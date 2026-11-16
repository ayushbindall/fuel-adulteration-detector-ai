"""Inference helper + CLI. The backend (inference.py) will import predict_sample() from here
so training, CLI and API all share exactly the same validation and preprocessing.

CLI:  python ml/predict.py --fuel-type Petrol --temperature 26.5 --dielectric 2.1
"""
import argparse, json, math
import joblib, pandas as pd
from common import META_PATH, MODEL_PATH, FORBIDDEN_INPUTS

_model, _meta = None, None


class InvalidReading(ValueError):
    """Raised for missing / malformed / out-of-range measurements. Never substituted silently."""


def load():
    global _model, _meta
    if _model is None:
        _meta = json.loads(META_PATH.read_text())
        _model = joblib.load(MODEL_PATH)
    return _model, _meta


def validate(reading: dict, meta: dict) -> dict:
    errs = []
    bad = [k for k in reading if k in FORBIDDEN_INPUTS]
    if bad:
        errs.append(f"Not allowed as input (leaks label): {bad}")
    fuels = meta["categorical_features"]["Fuel_Type"]
    if reading.get("Fuel_Type") not in fuels:
        errs.append(f"Fuel_Type must be one of {fuels}, got {reading.get('Fuel_Type')!r}")
    clean = {"Fuel_Type": reading.get("Fuel_Type")}
    for f in meta["numeric_features"]:
        v = reading.get(f)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            errs.append(f"{f} missing or not a finite number")
            continue
        lo, hi = meta["valid_input_ranges"][f]
        if not lo <= v <= hi:
            errs.append(f"{f}={v} outside physically valid range [{lo}, {hi}]")
        clean[f] = float(v)
    if errs:
        raise InvalidReading("; ".join(errs))
    return clean


def predict_sample(reading: dict) -> dict:
    model, meta = load()
    clean = validate(reading, meta)
    p = float(model.predict_proba(pd.DataFrame([clean])[meta["input_columns"]])[0, 1])
    lo, hi = meta["uncertain_band"]
    warnings = ["Model estimate only - NOT a certified laboratory result."]
    for f, (a, b) in meta["training_ranges"].items():
        if not a <= clean[f] <= b:
            warnings.append(f"{f}={clean[f]} is outside the training range [{a}, {b}]; prediction unreliable.")
    uncertain = lo <= p <= hi
    if uncertain:
        warnings.append("Probability is near the decision boundary; result is uncertain.")
    label = "Potentially Adulterated" if p >= meta["decision_threshold"] else "Pure (no adulteration detected)"
    warnings.append("This model mainly detects polar contaminants (water/alcohols); a 'Pure' result does not rule out "
                    "hydrocarbon adulteration such as diesel/kerosene/solvent/waste oil.") if label.startswith("Pure") else None
    return {"prediction": label, "probability_adulterated": round(p, 4), "uncertain": uncertain,
            "inputs": clean, "model_version": meta["model_version"], "warnings": [w for w in warnings if w]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuel-type", required=True)
    ap.add_argument("--temperature", type=float, required=True)
    ap.add_argument("--dielectric", type=float, required=True)
    a = ap.parse_args()
    try:
        print(json.dumps(predict_sample({"Fuel_Type": a.fuel_type, "Temperature": a.temperature,
                                         "Dielectric": a.dielectric}), indent=2))
    except InvalidReading as e:
        print("INVALID READING:", e)
        raise SystemExit(2)
