"""Demo for presentations.  Run from the ml folder:  python demo.py
Runs several test readings through the SAME validation + model used by the API.
These are hand-picked test values, NOT physical measurements."""
from predict import predict_sample, InvalidReading

CASES = [
    ("Pure petrol",           "Petrol",   26.5, 2.15),
    ("Petrol + water-like",   "Petrol",   26.5, 9.0),
    ("Pure diesel",           "Diesel",   26.5, 2.74),
    ("Diesel + alcohol-like", "Diesel",   26.5, 12.0),
    ("Pure kerosene",         "Kerosene", 26.5, 2.45),
    ("Kerosene + water-like", "Kerosene", 26.5, 20.0),
    ("Uncertain (near boundary)", "Diesel", 26.5, 2.40),
    ("Beyond training range", "Diesel",   26.5, 50.0),
    ("Invalid (dielectric 500)", "Diesel", 26.5, 500.0),
    ("Invalid (unknown fuel)", "Water",   26.5, 2.0),
]

print(f"{'Case':28s}{'Fuel':10s}{'Temp':>6s}{'Diel.':>8s}   {'Result':33s}{'P(adult.)':>10s}  Notes")
print("-" * 100)
for name, fuel, t, d in CASES:
    try:
        r = predict_sample({"Fuel_Type": fuel, "Temperature": t, "Dielectric": d})
        notes = []
        if r["uncertain"]:
            notes.append("UNCERTAIN")
        if any("outside the training range" in w for w in r["warnings"]):
            notes.append("outside training range")
        print(f"{name:28s}{fuel:10s}{t:6.1f}{d:8.2f}   {r['prediction']:33s}{r['probability_adulterated']*100:9.1f}%  {', '.join(notes)}")
    except InvalidReading as e:
        print(f"{name:28s}{fuel:10s}{t:6.1f}{d:8.2f}   {'REJECTED':33s}{'-':>10s}  {e}")
print("\nNote: model estimate only - NOT a certified laboratory result.")