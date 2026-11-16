"""Re-evaluate the SAVED model on the same held-out split.
Run:  python evaluate_model.py   (from inside the ml folder)"""
import json
import joblib
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from common import *

meta = json.loads(META_PATH.read_text())
saved_eval = json.loads(EVAL_PATH.read_text())
model = joblib.load(MODEL_PATH)

df = load_data()
_, test = split(df)
cols = meta["input_columns"]
assert not set(cols) & set(FORBIDDEN_INPUTS), "Forbidden/leaky column used as input!"
p = model.predict_proba(test[cols])[:, 1]
pred = (p >= meta["decision_threshold"]).astype(int)

print(f"Model: {meta['algorithm']} | features: {cols} | version {meta['model_version']}")
print(f"Held-out test rows: {len(test)}\n")
print(classification_report(test.y, pred, target_names=["Pure", "Adulterated"], digits=3))
print("Confusion matrix [[TN FP],[FN TP]]:\n", confusion_matrix(test.y, pred))
auc = roc_auc_score(test.y, p)
print(f"ROC-AUC: {auc:.3f}")

lo, hi = meta["uncertain_band"]
unc = (p >= lo) & (p <= hi)
print(f"\nSamples in uncertain band [{lo},{hi}]: {unc.sum()} ({unc.mean():.1%}); accuracy outside band: "
      f"{(pred[~unc] == test.y.values[~unc]).mean():.3f}")

print("\nHeld-out recall by adulterant (adulterated rows only):")
t = test.assign(hit=(pred == 1))[test.y == 1]
print(t.groupby("Adulterant").hit.agg(["mean", "count"]).round(3).to_string())

rec = saved_eval["heldout_test"][meta["feature_set"]]
assert abs(rec["roc_auc"] - auc) < 1e-9, "Mismatch with training-time metrics!"
print("\nOK: metrics match training run (reproducible).")
print("REMINDER: simulated dataset -> these numbers are NOT real-world detection accuracy.")