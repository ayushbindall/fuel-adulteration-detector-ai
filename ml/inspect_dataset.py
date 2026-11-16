"""Phase 1: reproducible dataset inspection for micro.xlsx.
Run from project root:  python ml/inspect_dataset.py
NOTE: keep_default_na=False is REQUIRED. The Adulterant value "None" (pure fuel)
is otherwise silently converted to NaN by pandas.
"""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score

SEED = 42
PATH = Path(__file__).resolve().parents[1] / "dataset" / "micro.xlsx"
FEATS = ["Density", "Viscosity", "Refractive_Index", "Dielectric",
         "Optical_Sensor", "Color", "Temperature", "Flash_Point"]

df = pd.read_excel(PATH, keep_default_na=False)
y = (df["Label"] == "Adulterated").astype(int)

print("== Shape / dtypes / missing / duplicates ==")
print(df.shape); print(df.dtypes.to_string())
print("missing:", int(df.isna().sum().sum()),
      "| full-row dups:", int(df.duplicated().sum()),
      "| dups on features:", int(df.duplicated(subset=FEATS).sum()))

print("\n== Class balance ==")
print(df["Label"].value_counts().to_string())
print(pd.crosstab(df["Fuel_Type"], df["Label"]).to_string())

print("\n== Design balance: rows per Fuel x Adulterant x % (adulterated only) ==")
print(df[y == 1].groupby(["Fuel_Type", "Adulterant", "Adulteration_%"]).size().value_counts().to_string())

print("\n== Provenance checks (evidence of simulation) ==")
ks = stats.kstest(df["Temperature"], "uniform", args=(20, 15))
print(f"Temperature ~ Uniform(20,35)? KS p = {ks.pvalue:.3f}  (high p => uniform, i.e. random, not a real thermal log)")
pure = df[df["Label"] == "Pure"]
for f, g in pure.groupby("Fuel_Type"):
    print(f"{f:9s} pure: corr(Temp,Density)={g.Temperature.corr(g.Density):+.3f}  "
          f"corr(Temp,Viscosity)={g.Temperature.corr(g.Viscosity):+.3f}  "
          f"mean|corr| among other features={g[FEATS].drop(columns='Temperature').corr().abs().values[np.triu_indices(7,1)].mean():.3f}")
print("Mean pure Flash_Point by fuel:", pure.groupby("Fuel_Type")["Flash_Point"].mean().round(1).to_dict(),
      "(real petrol flash point is far below 0 C)")

print("\n== Leakage demonstration (5-fold CV accuracy, Random Forest) ==")
X = pd.get_dummies(df[FEATS + ["Fuel_Type"]], columns=["Fuel_Type"], dtype=int)
rf = RandomForestClassifier(300, random_state=SEED, n_jobs=-1)
cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
print("measurements + Fuel_Type          :", cross_val_score(rf, X, y, cv=cv).mean().round(3))
print("+ Adulteration_% (LEAKS target)   :", cross_val_score(rf, X.assign(pct=df["Adulteration_%"]), y, cv=cv).mean().round(3))

print("\n== Group means by Adulterant (shows which features respond) ==")
print(df.groupby("Adulterant")[FEATS].mean().round(3).to_string())
