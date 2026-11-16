"""Shared constants and helpers used by train / evaluate / predict (and later the backend).
Keeping feature names, units and categories in ONE place guarantees the same schema everywhere."""
from pathlib import Path
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 42
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "dataset" / "micro.xlsx"
MODEL_DIR = ROOT / "ml" / "models"
MODEL_PATH = MODEL_DIR / "fuel_model.joblib"
REFERENCE_MODEL_PATH = MODEL_DIR / "fuel_model_full_reference.joblib"
META_PATH = MODEL_DIR / "metadata.json"
EVAL_PATH = MODEL_DIR / "evaluation.json"

FUEL_TYPES = ["Diesel", "Kerosene", "Petrol"]
CATEGORICAL = ["Fuel_Type"]
TARGET_POSITIVE = "Adulterated"

# Units (as used by the dataset and by the future firmware/backend JSON):
UNITS = {"Temperature": "degC", "Dielectric": "relative permittivity (dimensionless)",
         "Optical_Sensor": "dataset-defined units (instrument unknown)", "Color": "dataset-defined units",
         "Density": "kg/m3", "Viscosity": "cP (assumed)", "Refractive_Index": "dimensionless",
         "Flash_Point": "degC"}

# NEVER inputs: they reveal the label or are unknown at inference time.
FORBIDDEN_INPUTS = ["Adulterant", "Adulteration_%", "Label"]

FEATURE_SETS = {
    # Offline upper bound: needs lab instruments (and an unsafe flash-point test). NOT deployable.
    "full_reference": ["Density", "Viscosity", "Refractive_Index", "Dielectric",
                       "Optical_Sensor", "Color", "Temperature", "Flash_Point"],
    # Hardware-compatible after calibration to relative permittivity (temperature probe + capacitance cell).
    "hw_dielectric_temp": ["Temperature", "Dielectric"],
    "hw_dielectric_only": ["Dielectric"],
    # Needs the optical sensor retrained on YOUR OWN data (dataset optical units are undefined).
    "hw_plus_optical": ["Temperature", "Dielectric", "Optical_Sensor"],
}
DEPLOYED_SET = "hw_dielectric_temp"


def load_data() -> pd.DataFrame:
    # keep_default_na=False: the string "None" (pure fuel) must NOT become NaN.
    df = pd.read_excel(DATA_PATH, keep_default_na=False)
    df["y"] = (df["Label"] == TARGET_POSITIVE).astype(int)
    df["cell"] = df["Fuel_Type"] + "|" + df["Adulterant"] + "|" + df["Adulteration_%"].astype(str)
    return df


def split(df: pd.DataFrame):
    """Single deterministic 80/20 split, stratified by Fuel x Adulterant x % cell."""
    return train_test_split(df, test_size=0.20, random_state=SEED, stratify=df["cell"])


def make_preprocessor(numeric_cols):
    return ColumnTransformer([
        ("fuel", OneHotEncoder(categories=[FUEL_TYPES], handle_unknown="error"), CATEGORICAL),
        ("num", StandardScaler(), list(numeric_cols)),
    ])


def candidate_models(numeric_cols):
    prep = lambda: make_preprocessor(numeric_cols)
    return {
        "logistic_regression": Pipeline([("prep", prep()), ("clf", LogisticRegression(
            max_iter=3000, class_weight="balanced", random_state=SEED))]),
        "random_forest": Pipeline([("prep", prep()), ("clf", RandomForestClassifier(
            n_estimators=300, min_samples_leaf=3, class_weight="balanced", random_state=SEED, n_jobs=-1))]),
        "extra_trees": Pipeline([("prep", prep()), ("clf", ExtraTreesClassifier(
            n_estimators=300, min_samples_leaf=3, class_weight="balanced", random_state=SEED, n_jobs=-1))]),
        "hist_gradient_boosting": Pipeline([("prep", prep()), ("clf", HistGradientBoostingClassifier(
            max_depth=4, learning_rate=0.06, max_iter=200, class_weight="balanced", random_state=SEED))]),
    }


def columns_for(feature_set: str):
    return CATEGORICAL + FEATURE_SETS[feature_set]
