
"""FastAPI backend for AI Fuel Adulteration Detection."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend import database as db
from backend import inference
from backend.schemas import SensorReading, StoredReading

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fuel.api")

app = FastAPI(
    title="AI Powered Fuel Adulteration Detection",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_model_version():
    try:
        meta = inference.model_meta()
        return str(
            meta.get("model_version")
            or meta.get("version")
            or meta.get("name")
            or "fuel-model"
        )
    except Exception:
        return "unavailable"


@app.on_event("startup")
def startup():
    db.init_db()

    loaded = inference.load_model()

    if loaded:
        log.info("Model loaded: True")
        log.info("Model version: %s", get_model_version())
    else:
        log.error("Model loaded: False")


def _predict(reading: SensorReading) -> dict:
    if not inference.is_ready():
        raise HTTPException(
            status_code=503,
            detail="ML model is not loaded. Check ml/demo.py and model files."
        )

    try:
        result = inference.run(
            fuel_type=reading.fuel_type,
            temperature=reading.temperature,
            dielectric=reading.dielectric
        )

        return result

    except inference.InvalidReading as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    except Exception:
        log.exception("Prediction failed")
        raise HTTPException(
            status_code=500,
            detail="Prediction failed. Check backend terminal."
        )


@app.get("/")
def root():
    return {
        "message": "AI Fuel Adulteration Detection API",
        "status": "running"
    }


@app.get("/health")
def health():
    try:
        latest = db.latest(source="hardware")
        database_status = "ok"
    except Exception:
        log.exception("Database health check failed")
        latest = None
        database_status = "error"

    return {
        "status": "ok" if database_status == "ok" else "error",
        "model_loaded": inference.is_ready(),
        "model_version": get_model_version(),
        "database": database_status,
        "device_online": latest is not None,
        "last_hardware_reading_at": (
            latest.get("received_at") if latest else None
        ),
        "server_time": datetime.now(timezone.utc).isoformat()
    }


@app.post("/api/predict")
def predict(reading: SensorReading):
    result = _predict(reading)
    return result


@app.post(
    "/api/sensors",
    response_model=StoredReading,
    status_code=201
)
def ingest(reading: SensorReading):
    result = _predict(reading)

    rec = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "device_timestamp": (
            reading.timestamp.isoformat()
            if reading.timestamp else None
        ),
        "device_id": reading.device_id,
        "source": reading.source,
        "sequence": reading.sequence,
        "fuel_type": reading.fuel_type,
        "temperature": reading.temperature,
        "dielectric": reading.dielectric,

        # TCS34725
        "tcs_red": reading.tcs_red,
        "tcs_green": reading.tcs_green,
        "tcs_blue": reading.tcs_blue,
        "tcs_clear": reading.tcs_clear,

        # BMP280
        "bmp_pressure": reading.bmp_pressure,

        # ADS1115
        "ads_a0": reading.ads_a0,
        "ads_a1": reading.ads_a1,
        "ads_a2": reading.ads_a2,
        "ads_a3": reading.ads_a3,
        "ads_v0": reading.ads_v0,
        "ads_v1": reading.ads_v1,
        "ads_v2": reading.ads_v2,
        "ads_v3": reading.ads_v3,

        # HX711
        "hx711_raw": reading.hx711_raw,

        # ML prediction
        "prediction": result["prediction"],
        "probability_adulterated": result["probability_adulterated"],
        "uncertain": result["uncertain"],
        "model_version": result["model_version"],
        "warnings": result["warnings"],
    }

    try:
        rec["id"] = db.insert(rec)
    except Exception:
        log.exception("Database insert failed")
        raise HTTPException(
            status_code=500,
            detail="Could not save sensor reading to database."
        )

    return rec


@app.get("/api/latest")
def get_latest(source: Optional[str] = None):
    return db.latest(source=source)


@app.get("/api/history")
def get_history(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    source: Optional[str] = None,
    fuel_type: Optional[str] = None,
    prediction: Optional[str] = None,
    search: Optional[str] = None
):
    total, rows = db.history(
        limit=limit,
        offset=offset,
        source=source,
        fuel_type=fuel_type,
        prediction=prediction,
        search=search
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": rows
    }


@app.get("/api/model")
def model_info():
    if not inference.is_ready():
        return {
            "model_loaded": False,
            "message": "Model is not loaded"
        }

    try:
        meta = inference.model_meta()
        return {
            "model_loaded": True,
            "model_version": get_model_version(),
            "metadata": meta
        }
    except Exception:
        log.exception("Could not read model metadata")
        raise HTTPException(
            status_code=500,
            detail="Could not read model metadata"
        )
