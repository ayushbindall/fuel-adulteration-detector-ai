"""Software tests (NOT physical validation). Run from project root:  python -m pytest tests -v
All readings below are clearly labelled source='manual_test' or 'simulation'."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from backend.main import app
    with TestClient(app) as c:
        yield c


def good(**kw):
    d = {"device_id": "test_device", "fuel_type": "Petrol", "temperature": 26.5, "dielectric": 2.1, "source": "manual_test"}
    d.update(kw)
    return d


def test_health_model_loaded(client):
    h = client.get("/health").json()
    assert h["model_loaded"] is True and h["status"] == "ok" and h["device_online"] is False


def test_low_dielectric_is_pure(client):
    r = client.post("/api/sensors", json=good())
    assert r.status_code == 201
    j = r.json()
    assert j["prediction"].startswith("Pure") and j["source"] == "manual_test"
    assert any("NOT a certified laboratory" in w for w in j["warnings"])


def test_high_dielectric_is_adulterated(client):
    j = client.post("/api/sensors", json=good(dielectric=9.0)).json()
    assert j["prediction"] == "Potentially Adulterated"


@pytest.mark.parametrize("bad", [
    {"dielectric": 500}, {"dielectric": 0.2}, {"temperature": -5}, {"temperature": 99},
    {"fuel_type": "Water"}, {"source": "magic"}, {"dielectric": "abc"}, {"device_id": "bad id!"},
    {"Adulterant": "Water"}, {"Adulteration_%": 10},
])
def test_invalid_rejected_and_not_stored(client, bad):
    assert client.post("/api/sensors", json=good(**bad)).status_code == 422
    assert client.get("/api/history").json()["total"] == 0


@pytest.mark.parametrize("missing", ["device_id", "fuel_type", "temperature", "dielectric", "source"])
def test_missing_field_rejected(client, missing):
    body = good(); body.pop(missing)
    assert client.post("/api/sensors", json=body).status_code == 422
    assert client.get("/api/history").json()["total"] == 0


def test_predict_endpoint_does_not_store(client):
    r = client.post("/api/predict", json=good(dielectric=9.0))
    assert r.status_code == 200 and r.json()["saved"] is False
    assert client.get("/api/history").json()["total"] == 0


def test_latest_and_history_filters(client):
    assert client.get("/api/sensors/latest").json()["reading"] is None
    client.post("/api/sensors", json=good())
    client.post("/api/sensors", json=good(dielectric=9.0, fuel_type="Diesel", source="simulation"))
    assert client.get("/api/sensors/latest").json()["reading"]["fuel_type"] == "Diesel"
    assert client.get("/api/history?source=manual_test").json()["total"] == 1
    assert client.get("/api/history?fuel_type=Diesel").json()["total"] == 1
    assert client.get("/api/history?prediction=Potentially").json()["total"] == 1


def test_only_hardware_marks_device_online(client):
    client.post("/api/sensors", json=good(source="simulation"))
    assert client.get("/health").json()["device_online"] is False
    client.post("/api/sensors", json=good(source="hardware"))
    assert client.get("/health").json()["device_online"] is True


def test_csv_export_and_model_info(client):
    client.post("/api/sensors", json=good())
    r = client.get("/api/history/export.csv")
    assert r.status_code == 200 and "probability_adulterated" in r.text.splitlines()[0]
    info = client.get("/api/model/info").json()
    assert info["metadata"]["feature_set"] == "hw_dielectric_temp" and "confusion_matrix" in info["heldout_test"]
