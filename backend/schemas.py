
"""Request validation for fuel sensor readings."""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

FuelType = Literal["Petrol", "Diesel", "Kerosene"]
Source = Literal["hardware", "simulation", "manual_test"]


class SensorReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$")
    fuel_type: FuelType
    temperature: float = Field(ge=0, le=60, allow_inf_nan=False)
    dielectric: float = Field(ge=1, le=100, allow_inf_nan=False)
    source: Source
    sequence: Optional[int] = Field(default=None, ge=0)
    timestamp: Optional[datetime] = None

    # TCS34725
    tcs_red: Optional[int] = Field(default=None, ge=0, le=65535)
    tcs_green: Optional[int] = Field(default=None, ge=0, le=65535)
    tcs_blue: Optional[int] = Field(default=None, ge=0, le=65535)
    tcs_clear: Optional[int] = Field(default=None, ge=0, le=65535)

    # BMP280
    bmp_pressure: Optional[float] = Field(default=None, ge=0, le=2000)

    # ADS1115 raw ADC values and voltage
    ads_a0: Optional[int] = None
    ads_a1: Optional[int] = None
    ads_a2: Optional[int] = None
    ads_a3: Optional[int] = None
    ads_v0: Optional[float] = None
    ads_v1: Optional[float] = None
    ads_v2: Optional[float] = None
    ads_v3: Optional[float] = None

    # HX711
    hx711_raw: Optional[float] = None


class PredictionOut(BaseModel):
    prediction: str
    probability_adulterated: float
    uncertain: bool
    model_version: str
    warnings: list[str]


class StoredReading(BaseModel):
    id: int
    received_at: str
    device_timestamp: Optional[str]
    device_id: str
    source: str
    sequence: Optional[int]
    fuel_type: str
    temperature: float
    dielectric: float
    prediction: str
    probability_adulterated: float
    uncertain: bool
    model_version: str
    warnings: list[str]

    tcs_red: Optional[int] = None
    tcs_green: Optional[int] = None
    tcs_blue: Optional[int] = None
    tcs_clear: Optional[int] = None
    bmp_pressure: Optional[float] = None
    ads_a0: Optional[int] = None
    ads_a1: Optional[int] = None
    ads_a2: Optional[int] = None
    ads_a3: Optional[int] = None
    ads_v0: Optional[float] = None
    ads_v1: Optional[float] = None
    ads_v2: Optional[float] = None
    ads_v3: Optional[float] = None
    hx711_raw: Optional[float] = None
