"""
Generate synthetic clinical training data for the Healthcare DSS ML classifier.

Produces:  ai_engine/ml_data/clinical_symptoms_dataset.csv

The dataset is keyed exactly to the 8 conditions in mock_data.py MOCK_CONDITIONS:
  0  Hypertensive Heart Disease
  1  Type 2 Diabetes Mellitus
  2  Acute Upper Respiratory Infection
  3  Iron Deficiency Anemia
  4  Gastroesophageal Reflux Disease (GERD)
  5  Anxiety Disorder
  6  Musculoskeletal Back Pain
  7  Migraine

Features (binary symptom flags + simple numeric vitals):
  Symptoms (binary 0/1):
    headache, chest_pain, palpitation, dizziness,
    fatigue, weakness, breathlessness,
    fever, cough, sore_throat, nasal_congestion,
    nausea, vomiting, heartburn, regurgitation,
    anxiety_worry, insomnia, back_pain, muscle_stiffness,
    photophobia, throbbing_pain, polyuria, polydipsia, blurred_vision,
    pallor, pale_skin, weight_loss, excessive_thirst
  Numeric:
    age (20-75), systolic_bp (90-180), bmi (18-38)
  Label:
    condition (one of the 8 class names above)

Run this script once with:
  python ai_engine/ml_data/generate_dataset.py
"""

import random
import csv
from pathlib import Path

random.seed(42)

OUTFILE = Path(__file__).parent / "clinical_symptoms_dataset.csv"

# ----- condition definitions ------------------------------------------------
# Each condition has: class label, feature weights (prob of symptom=1),
# bp range, bmi range, age range, n samples

CONDITIONS = [
    {
        "label": "Hypertensive Heart Disease",
        "n": 150,
        "age": (40, 75),
        "bp":  (145, 180),
        "bmi": (26, 38),
        "symptoms": {
            "headache": 0.80, "chest_pain": 0.65, "palpitation": 0.70, "dizziness": 0.75,
            "fatigue": 0.50, "weakness": 0.30, "breathlessness": 0.40,
            "fever": 0.05, "cough": 0.05, "sore_throat": 0.03, "nasal_congestion": 0.03,
            "nausea": 0.20, "vomiting": 0.05, "heartburn": 0.10, "regurgitation": 0.05,
            "anxiety_worry": 0.25, "insomnia": 0.30, "back_pain": 0.15, "muscle_stiffness": 0.10,
            "photophobia": 0.10, "throbbing_pain": 0.30, "polyuria": 0.10, "polydipsia": 0.10,
            "blurred_vision": 0.25, "pallor": 0.10, "pale_skin": 0.08, "weight_loss": 0.10,
            "excessive_thirst": 0.10,
        },
    },
    {
        "label": "Type 2 Diabetes Mellitus",
        "n": 150,
        "age": (35, 70),
        "bp":  (120, 155),
        "bmi": (27, 40),
        "symptoms": {
            "headache": 0.20, "chest_pain": 0.15, "palpitation": 0.15, "dizziness": 0.20,
            "fatigue": 0.85, "weakness": 0.70, "breathlessness": 0.20,
            "fever": 0.05, "cough": 0.05, "sore_throat": 0.03, "nasal_congestion": 0.03,
            "nausea": 0.25, "vomiting": 0.10, "heartburn": 0.15, "regurgitation": 0.08,
            "anxiety_worry": 0.20, "insomnia": 0.25, "back_pain": 0.10, "muscle_stiffness": 0.10,
            "photophobia": 0.05, "throbbing_pain": 0.05, "polyuria": 0.90, "polydipsia": 0.88,
            "blurred_vision": 0.70, "pallor": 0.20, "pale_skin": 0.15, "weight_loss": 0.65,
            "excessive_thirst": 0.90,
        },
    },
    {
        "label": "Acute Upper Respiratory Infection",
        "n": 150,
        "age": (20, 65),
        "bp":  (100, 130),
        "bmi": (18, 30),
        "symptoms": {
            "headache": 0.60, "chest_pain": 0.10, "palpitation": 0.05, "dizziness": 0.20,
            "fatigue": 0.75, "weakness": 0.55, "breathlessness": 0.20,
            "fever": 0.90, "cough": 0.92, "sore_throat": 0.85, "nasal_congestion": 0.88,
            "nausea": 0.30, "vomiting": 0.15, "heartburn": 0.05, "regurgitation": 0.03,
            "anxiety_worry": 0.10, "insomnia": 0.35, "back_pain": 0.15, "muscle_stiffness": 0.30,
            "photophobia": 0.15, "throbbing_pain": 0.10, "polyuria": 0.03, "polydipsia": 0.05,
            "blurred_vision": 0.05, "pallor": 0.10, "pale_skin": 0.08, "weight_loss": 0.05,
            "excessive_thirst": 0.05,
        },
    },
    {
        "label": "Iron Deficiency Anemia",
        "n": 150,
        "age": (20, 60),
        "bp":  (90, 115),
        "bmi": (18, 26),
        "symptoms": {
            "headache": 0.40, "chest_pain": 0.15, "palpitation": 0.50, "dizziness": 0.65,
            "fatigue": 0.95, "weakness": 0.90, "breathlessness": 0.75,
            "fever": 0.05, "cough": 0.05, "sore_throat": 0.03, "nasal_congestion": 0.03,
            "nausea": 0.20, "vomiting": 0.05, "heartburn": 0.05, "regurgitation": 0.03,
            "anxiety_worry": 0.15, "insomnia": 0.20, "back_pain": 0.10, "muscle_stiffness": 0.10,
            "photophobia": 0.05, "throbbing_pain": 0.05, "polyuria": 0.03, "polydipsia": 0.05,
            "blurred_vision": 0.15, "pallor": 0.90, "pale_skin": 0.88, "weight_loss": 0.25,
            "excessive_thirst": 0.05,
        },
    },
    {
        "label": "Gastroesophageal Reflux Disease (GERD)",
        "n": 150,
        "age": (30, 65),
        "bp":  (110, 140),
        "bmi": (24, 36),
        "symptoms": {
            "headache": 0.20, "chest_pain": 0.55, "palpitation": 0.10, "dizziness": 0.10,
            "fatigue": 0.30, "weakness": 0.15, "breathlessness": 0.10,
            "fever": 0.03, "cough": 0.30, "sore_throat": 0.35, "nasal_congestion": 0.05,
            "nausea": 0.70, "vomiting": 0.30, "heartburn": 0.95, "regurgitation": 0.88,
            "anxiety_worry": 0.20, "insomnia": 0.40, "back_pain": 0.10, "muscle_stiffness": 0.05,
            "photophobia": 0.03, "throbbing_pain": 0.05, "polyuria": 0.03, "polydipsia": 0.05,
            "blurred_vision": 0.05, "pallor": 0.05, "pale_skin": 0.03, "weight_loss": 0.10,
            "excessive_thirst": 0.05,
        },
    },
    {
        "label": "Anxiety Disorder",
        "n": 150,
        "age": (20, 55),
        "bp":  (105, 135),
        "bmi": (19, 28),
        "symptoms": {
            "headache": 0.60, "chest_pain": 0.35, "palpitation": 0.80, "dizziness": 0.50,
            "fatigue": 0.70, "weakness": 0.40, "breathlessness": 0.35,
            "fever": 0.03, "cough": 0.05, "sore_throat": 0.03, "nasal_congestion": 0.03,
            "nausea": 0.45, "vomiting": 0.10, "heartburn": 0.15, "regurgitation": 0.05,
            "anxiety_worry": 0.95, "insomnia": 0.85, "back_pain": 0.25, "muscle_stiffness": 0.30,
            "photophobia": 0.10, "throbbing_pain": 0.15, "polyuria": 0.05, "polydipsia": 0.08,
            "blurred_vision": 0.10, "pallor": 0.10, "pale_skin": 0.08, "weight_loss": 0.15,
            "excessive_thirst": 0.08,
        },
    },
    {
        "label": "Musculoskeletal Back Pain",
        "n": 150,
        "age": (25, 65),
        "bp":  (110, 140),
        "bmi": (20, 34),
        "symptoms": {
            "headache": 0.20, "chest_pain": 0.05, "palpitation": 0.05, "dizziness": 0.10,
            "fatigue": 0.45, "weakness": 0.40, "breathlessness": 0.05,
            "fever": 0.05, "cough": 0.03, "sore_throat": 0.03, "nasal_congestion": 0.03,
            "nausea": 0.10, "vomiting": 0.03, "heartburn": 0.05, "regurgitation": 0.03,
            "anxiety_worry": 0.20, "insomnia": 0.35, "back_pain": 0.97, "muscle_stiffness": 0.90,
            "photophobia": 0.03, "throbbing_pain": 0.10, "polyuria": 0.03, "polydipsia": 0.03,
            "blurred_vision": 0.05, "pallor": 0.05, "pale_skin": 0.03, "weight_loss": 0.05,
            "excessive_thirst": 0.03,
        },
    },
    {
        "label": "Migraine",
        "n": 150,
        "age": (20, 50),
        "bp":  (100, 130),
        "bmi": (19, 28),
        "symptoms": {
            "headache": 0.98, "chest_pain": 0.05, "palpitation": 0.15, "dizziness": 0.55,
            "fatigue": 0.65, "weakness": 0.40, "breathlessness": 0.05,
            "fever": 0.05, "cough": 0.05, "sore_throat": 0.03, "nasal_congestion": 0.10,
            "nausea": 0.85, "vomiting": 0.65, "heartburn": 0.08, "regurgitation": 0.05,
            "anxiety_worry": 0.25, "insomnia": 0.35, "back_pain": 0.10, "muscle_stiffness": 0.10,
            "photophobia": 0.90, "throbbing_pain": 0.92, "polyuria": 0.03, "polydipsia": 0.03,
            "blurred_vision": 0.45, "pallor": 0.15, "pale_skin": 0.12, "weight_loss": 0.05,
            "excessive_thirst": 0.03,
        },
    },
]

SYMPTOM_COLS = [
    "headache", "chest_pain", "palpitation", "dizziness",
    "fatigue", "weakness", "breathlessness",
    "fever", "cough", "sore_throat", "nasal_congestion",
    "nausea", "vomiting", "heartburn", "regurgitation",
    "anxiety_worry", "insomnia", "back_pain", "muscle_stiffness",
    "photophobia", "throbbing_pain", "polyuria", "polydipsia",
    "blurred_vision", "pallor", "pale_skin", "weight_loss", "excessive_thirst",
]

NUMERIC_COLS = ["age", "systolic_bp", "bmi"]
ALL_COLS = SYMPTOM_COLS + NUMERIC_COLS + ["condition"]


def gen_row(cond_def):
    age = random.randint(*cond_def["age"])
    bp  = random.randint(*cond_def["bp"]) + random.randint(-5, 5)
    bmi = round(random.uniform(*cond_def["bmi"]) + random.uniform(-1, 1), 1)
    row = {}
    for sym in SYMPTOM_COLS:
        p = cond_def["symptoms"].get(sym, 0.05)
        # Add a little noise
        p = min(1.0, max(0.0, p + random.uniform(-0.05, 0.05)))
        row[sym] = 1 if random.random() < p else 0
    row["age"] = age
    row["systolic_bp"] = max(80, min(200, bp))
    row["bmi"] = max(15.0, min(45.0, bmi))
    row["condition"] = cond_def["label"]
    return row


rows = []
for cond in CONDITIONS:
    for _ in range(cond["n"]):
        rows.append(gen_row(cond))

# Shuffle
random.shuffle(rows)

with open(OUTFILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=ALL_COLS)
    writer.writeheader()
    writer.writerows(rows)

print(f"Dataset written: {OUTFILE}")
print(f"Total rows     : {len(rows)}")
print(f"Conditions     : {len(CONDITIONS)} classes")
print(f"Features       : {len(SYMPTOM_COLS)} binary symptoms + {len(NUMERIC_COLS)} numeric")
