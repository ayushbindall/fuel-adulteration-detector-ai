"""Thin wrapper around ml/predict.py so training, CLI and API share ONE validation + preprocessing path."""
import logging, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))
import predict as ml_predict  # noqa: E402

log = logging.getLogger("fuel.inference")
_ready = False


def load_model() -> bool:
    global _ready
    try:
        ml_predict.load()
        _ready = True
    except Exception:
        log.exception("Model failed to load")
        _ready = False
    return _ready


def is_ready() -> bool:
    return _ready


def model_meta() -> dict:
    return ml_predict.load()[1]


def run(fuel_type: str, temperature: float, dielectric: float) -> dict:
    """Raises ml_predict.InvalidReading for invalid input, RuntimeError if the model is unavailable."""
    if not _ready:
        raise RuntimeError("model not loaded")
    return ml_predict.predict_sample({"Fuel_Type": fuel_type, "Temperature": temperature, "Dielectric": dielectric})


InvalidReading = ml_predict.InvalidReading
