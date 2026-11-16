"""Train, compare and save the fuel adulteration classifier.   Run:  python ml/train_model.py

Protocol (no test-set peeking):
 1. One stratified 80/20 split (stratified by Fuel x Adulterant x %).
 2. Model selection per feature set uses ONLY the training part (5-fold x 2 repeats CV, selected by F1 then ROC-AUC).
 3. The chosen model is probability-calibrated (CV on training data) and scored ONCE on the held-out test set.
 4. Stress test: leave-one-adulterant-out (train without an adulterant, test on it).
 5. The shipped model is the one that was evaluated (trained on the training split) so reported metrics match it.
"""
import json, platform, sys
from datetime import datetime, timezone
import joblib, numpy as np, pandas as pd, sklearn
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.inspection import permutation_importance
from sklearn.metrics import (accuracy_score, brier_score_loss, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, cross_validate, cross_val_predict

from common import *

SCORING = {"accuracy": "accuracy", "precision": "precision", "recall": "recall", "f1": "f1", "roc_auc": "roc_auc"}


def test_metrics(model, X, y):
    p = model.predict_proba(X)[:, 1]
    pred = (p >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "accuracy": accuracy_score(y, pred), "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred), "f1": f1_score(y, pred), "roc_auc": roc_auc_score(y, p),
        "specificity": tn / (tn + fp), "brier": brier_score_loss(y, p),
        "confusion_matrix": {"labels": ["Pure", "Adulterated"], "matrix": [[int(tn), int(fp)], [int(fn), int(tp)]]},
        "n_test": int(len(y)),
    }


def loao(best_name, fset, df):
    """Leave-one-adulterant-out: recall on the unseen adulterant + specificity on held-out pure rows."""
    cols, num = columns_for(fset), FEATURE_SETS[fset]
    rng = np.random.RandomState(SEED)
    pure_idx = df.index[df.y == 0].to_numpy()
    held_pure = rng.choice(pure_idx, int(0.2 * len(pure_idx)), replace=False)
    out = {}
    for adult in sorted(a for a in df.Adulterant.unique() if a != "None"):
        te_ad = df.index[df.Adulterant == adult]
        te = df.loc[np.union1d(te_ad, held_pure)]
        tr = df.drop(index=te.index)
        tr = tr[tr.Adulterant != adult]
        m = clone(candidate_models(num)[best_name]).fit(tr[cols], tr.y)
        r_ad = m.predict(df.loc[te_ad, cols]).mean()
        spec = 1 - m.predict(df.loc[held_pure, cols]).mean()
        out[adult] = {"recall_unseen_adulterant": round(float(r_ad), 4), "specificity_pure": round(float(spec), 4)}
    return out


def main():
    df = load_data()
    train, test = split(df)
    print(f"rows={len(df)} train={len(train)} test={len(test)} | test class balance={test.y.mean():.3f}")
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=2, random_state=SEED)

    cv_table, chosen, test_table, loao_table = [], {}, {}, {}
    fitted = {}
    for fset in FEATURE_SETS:
        cols, num = columns_for(fset), FEATURE_SETS[fset]
        rows = []
        for name, pipe in candidate_models(num).items():
            r = cross_validate(pipe, train[cols], train.y, cv=cv, scoring=SCORING, n_jobs=1)
            row = {"feature_set": fset, "model": name,
                   **{k: round(float(r[f"test_{k}"].mean()), 4) for k in SCORING},
                   **{f"{k}_std": round(float(r[f"test_{k}"].std()), 4) for k in ("f1", "roc_auc")}}
            rows.append(row)
        cv_table += rows
        best = sorted(rows, key=lambda r: (r["f1"], r["roc_auc"]), reverse=True)[0]["model"]
        chosen[fset] = best
        # Calibrated final model, trained on the training split only
        cal = CalibratedClassifierCV(candidate_models(num)[best], method="isotonic" if len(train) > 1000 else "sigmoid",
                                     cv=StratifiedKFold(5, shuffle=True, random_state=SEED))
        cal.fit(train[cols], train.y)
        fitted[fset] = cal
        test_table[fset] = {"model": best, **test_metrics(cal, test[cols], test.y)}
        loao_table[fset] = loao(best, fset, df)
        print(f"[{fset:20s}] best CV model = {best:24s} test F1={test_table[fset]['f1']:.3f} "
              f"AUC={test_table[fset]['roc_auc']:.3f} acc={test_table[fset]['accuracy']:.3f}")

    # ----- deployed model details -----
    dep = DEPLOYED_SET
    cols = columns_for(dep)
    model = fitted[dep]
    # per-adulterant / % recall from out-of-fold predictions on ALL data (descriptive; not used for selection)
    oof = cross_val_predict(candidate_models(FEATURE_SETS[dep])[chosen[dep]], df[cols], df.y,
                            cv=StratifiedKFold(5, shuffle=True, random_state=SEED))
    d = df.assign(hit=(oof == 1))[df.y == 1]
    recall_grid = d.pivot_table(index="Adulterant", columns="Adulteration_%", values="hit", aggfunc="mean").round(3)
    pure_spec = float(1 - oof[df.y == 0].mean())

    imp = permutation_importance(model, test[cols], test.y, scoring="roc_auc", n_repeats=20, random_state=SEED)
    importance = {c: {"mean_auc_drop": round(float(m), 4), "std": round(float(s), 4)}
                  for c, m, s in zip(cols, imp.importances_mean, imp.importances_std)}

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(fitted["full_reference"], REFERENCE_MODEL_PATH)

    num = FEATURE_SETS[dep]
    meta = {
        "model_version": "fuel-clf-" + datetime.now(timezone.utc).strftime("%Y%m%d"),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "binary: Pure vs Adulterated (potential)",
        "algorithm": chosen[dep], "calibration": "isotonic (5-fold CV on training split)",
        "feature_set": dep, "input_columns": cols, "numeric_features": num,
        "categorical_features": {"Fuel_Type": FUEL_TYPES},
        "units": {c: UNITS[c] for c in num},
        "training_ranges": {c: [round(float(df[c].min()), 4), round(float(df[c].max()), 4)] for c in num},
        "valid_input_ranges": {"Temperature": [0.0, 60.0], "Dielectric": [1.0, 100.0]},
        "decision_threshold": 0.5, "uncertain_band": [0.35, 0.65],
        "forbidden_inputs": FORBIDDEN_INPUTS,
        "dataset": {"file": "micro.xlsx", "rows": int(len(df)), "train_rows": int(len(train)), "test_rows": int(len(test)),
                    "class_counts": {"Pure": int((df.y == 0).sum()), "Adulterated": int((df.y == 1).sum())},
                    "provenance": "Almost certainly SIMULATED (uniform random temperature, uncorrelated features, "
                                  "implausible petrol flash point). Metrics describe this dataset only."},
        "random_seed": SEED,
        "environment": {"python": sys.version.split()[0], "sklearn": sklearn.__version__,
                        "pandas": pd.__version__, "numpy": np.__version__, "platform": platform.system()},
        "limitations": [
            "Trained on a simulated dataset; NOT evidence of real-world detection accuracy.",
            "Dielectric input must be calibrated to relative permittivity; raw capacitance will give wrong answers.",
            "Reliably flags only polar contaminants (water, ethanol, methanol). Hydrocarbon adulterants "
            "(diesel/kerosene/solvent/waste oil) are mostly missed at low percentages.",
            "A prediction is NOT a certified laboratory result.",
        ],
    }
    META_PATH.write_text(json.dumps(meta, indent=2))

    evaluation = {
        "cv_table_train_only": cv_table, "chosen_model_per_feature_set": chosen,
        "heldout_test": test_table, "leave_one_adulterant_out": loao_table,
        "deployed": {"feature_set": dep, "feature_importance_permutation_auc": importance,
                     "oof_recall_by_adulterant_and_percent": json.loads(recall_grid.to_json()),
                     "oof_specificity_pure": round(pure_spec, 4)},
    }
    EVAL_PATH.write_text(json.dumps(evaluation, indent=2))

    print("\n=== 5-fold x2 CV on TRAIN split (mean) ===")
    print(pd.DataFrame(cv_table)[["feature_set", "model", "accuracy", "precision", "recall", "f1", "roc_auc", "f1_std"]].to_string(index=False))
    print("\n=== DEPLOYED:", dep, "-> model", chosen[dep], "===")
    print("held-out test:", {k: round(v, 3) for k, v in test_table[dep].items() if isinstance(v, float)})
    print("confusion matrix [[TN FP],[FN TP]]:", test_table[dep]["confusion_matrix"]["matrix"])
    print("OOF recall by adulterant x %:\n", recall_grid.to_string(), f"\nOOF pure specificity: {pure_spec:.3f}")
    print("Leave-one-adulterant-out (deployed set):", loao_table[dep])
    print("Permutation importance:", importance)
    print(f"\nSaved: {MODEL_PATH.name}, {META_PATH.name}, {EVAL_PATH.name}, {REFERENCE_MODEL_PATH.name}")


if __name__ == "__main__":
    main()
