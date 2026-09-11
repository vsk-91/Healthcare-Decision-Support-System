"""
ML Predictor Service for Healthcare DSS.

Trains Logistic Regression, Decision Tree, and Random Forest classifiers
on the clinical symptoms dataset, compares their metrics, and persists the
best-performing model as a .pkl file for use in the analysis pipeline.

Public interface:
  MLPredictor().predict(case) -> dict
      Returns: { prediction, confidence, ml_algorithm, supporting_findings }

  MLPredictor().is_trained() -> bool

Usage (called by management command):
  from ai_engine.services.ml_predictor import MLPredictor
  predictor = MLPredictor()
  report = predictor.train()
  print(report)

Integration point:
  multimodal_service.py calls predict(case) instead of _select_condition(case)
  when a trained model is available.  If no trained model exists, it falls back
  to the existing keyword-based _select_condition() automatically.

Design:
  - No external APIs required.
  - Dataset: ai_engine/ml_data/clinical_symptoms_dataset.csv (1200 rows, 8 classes)
  - Model file: ai_engine/ml_models/best_model.pkl (joblib format)
  - All three classifiers are always trained and evaluated for comparison.
  - Best model selected by weighted F1-score on stratified 20% test split.
  - Findings are generated from the trained classifier to remain informative.
"""

import logging
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

warnings.filterwarnings("ignore", category=UserWarning)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_AI_ENGINE_DIR = Path(__file__).resolve().parent.parent   # ai_engine/
_DATASET_PATH  = _AI_ENGINE_DIR / "ml_data" / "clinical_symptoms_dataset.csv"
_MODEL_DIR     = _AI_ENGINE_DIR / "ml_models"
_MODEL_PATH    = _MODEL_DIR / "best_model.pkl"
_REPORT_PATH   = _MODEL_DIR / "training_report.json"

# ---------------------------------------------------------------------------
# Feature columns — must match dataset column order
# ---------------------------------------------------------------------------
SYMPTOM_FEATURES = [
    "headache", "chest_pain", "palpitation", "dizziness",
    "fatigue", "weakness", "breathlessness",
    "fever", "cough", "sore_throat", "nasal_congestion",
    "nausea", "vomiting", "heartburn", "regurgitation",
    "anxiety_worry", "insomnia", "back_pain", "muscle_stiffness",
    "photophobia", "throbbing_pain", "polyuria", "polydipsia",
    "blurred_vision", "pallor", "pale_skin", "weight_loss", "excessive_thirst",
]
NUMERIC_FEATURES = ["age", "systolic_bp", "bmi"]
ALL_FEATURES     = SYMPTOM_FEATURES + NUMERIC_FEATURES
TARGET_COL       = "condition"

# ---------------------------------------------------------------------------
# Symptom-to-feature mapping for case → feature vector conversion
# Maps common clinical text patterns → dataset feature columns
# ---------------------------------------------------------------------------
SYMPTOM_KEYWORDS = {
    "headache":       ["headache", "head pain", "head ache"],
    "chest_pain":     ["chest pain", "chest tightness", "chest pressure"],
    "palpitation":    ["palpitation", "heart racing", "heart beat", "palpitations"],
    "dizziness":      ["dizzy", "dizziness", "vertigo", "lightheaded"],
    "fatigue":        ["fatigue", "tired", "exhausted", "tiredness", "lethargic"],
    "weakness":       ["weakness", "weak", "lack of energy"],
    "breathlessness": ["breathless", "shortness of breath", "dyspnea", "sob", "difficulty breathing"],
    "fever":          ["fever", "high temperature", "pyrexia", "febrile", "temperature"],
    "cough":          ["cough", "coughing"],
    "sore_throat":    ["sore throat", "throat pain", "pharyngitis", "tonsilitis"],
    "nasal_congestion": ["nasal", "runny nose", "congestion", "stuffy nose", "rhinitis", "sneezing"],
    "nausea":         ["nausea", "nauseous", "feeling sick"],
    "vomiting":       ["vomiting", "vomit", "throwing up"],
    "heartburn":      ["heartburn", "burning", "acid"],
    "regurgitation":  ["regurgitation", "reflux", "waterbrash"],
    "anxiety_worry":  ["anxiety", "anxious", "worry", "worried", "panic", "nervous", "stress", "stressed"],
    "insomnia":       ["insomnia", "sleep", "sleepless", "can't sleep"],
    "back_pain":      ["back pain", "backache", "lumbar", "spine", "sciatica"],
    "muscle_stiffness": ["stiffness", "stiff", "muscle pain", "myalgia", "aching muscles"],
    "photophobia":    ["photophobia", "light sensitivity", "sensitive to light"],
    "throbbing_pain": ["throbbing", "pulsating", "pounding"],
    "polyuria":       ["polyuria", "frequent urination", "urinating frequently", "passing urine"],
    "polydipsia":     ["polydipsia", "excessive thirst", "drinking lots"],
    "blurred_vision": ["blurred vision", "blurry vision", "visual disturbance", "vision problems"],
    "pallor":         ["pallor", "pale"],
    "pale_skin":      ["pale skin", "pallid", "ashen"],
    "weight_loss":    ["weight loss", "losing weight", "lost weight"],
    "excessive_thirst": ["excessive thirst", "thirst", "polydipsia", "very thirsty"],
}

# Default vital values (used when not extractable from case text)
_DEFAULT_AGE = 40
_DEFAULT_SBP = 125
_DEFAULT_BMI = 25.0


def case_to_features(case) -> np.ndarray:
    """
    Convert a PatientCase object to a feature vector for ML prediction.

    Binary symptom features are set by keyword-matching against:
      case.symptoms + case.chief_complaint + case.medical_history

    Numeric features (age, bp, bmi) default to population averages when
    not available in the case record.

    Returns: np.ndarray of shape (1, n_features)
    """
    text = " ".join(filter(None, [
        case.symptoms or "",
        case.chief_complaint or "",
        case.medical_history or "",
    ])).lower()

    row = {}
    for feat, keywords in SYMPTOM_KEYWORDS.items():
        row[feat] = int(any(kw in text for kw in keywords))

    # Numeric vitals — attempt to read from case attributes, else use defaults
    row["age"]          = int(getattr(case, "age", None) or _DEFAULT_AGE)
    row["systolic_bp"]  = int(getattr(case, "systolic_bp", None) or _DEFAULT_SBP)
    row["bmi"]          = float(getattr(case, "bmi", None) or _DEFAULT_BMI)

    # Return as 2D array (1 row) in exact feature column order
    return np.array([[row[f] for f in ALL_FEATURES]], dtype=float)


def _load_data():
    """Load and validate the training dataset."""
    if not _DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {_DATASET_PATH}\n"
            "Run: python ai_engine/ml_data/generate_dataset.py"
        )
    df = pd.read_csv(_DATASET_PATH)
    missing = [c for c in ALL_FEATURES + [TARGET_COL] if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing columns: {missing}")
    return df


def _build_pipelines():
    """Return the three classifier pipelines to compare."""
    return {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                max_iter=2000,
                C=1.0,
                solver="lbfgs",
                random_state=42,
            )),
        ]),
        "Decision Tree": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", DecisionTreeClassifier(
                max_depth=12,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
            )),
        ]),
        "Random Forest": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(
                n_estimators=200,
                max_depth=None,
                min_samples_split=4,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            )),
        ]),
    }


# ---------------------------------------------------------------------------
# PUBLIC SERVICE CLASS
# ---------------------------------------------------------------------------

class MLPredictor:
    """
    Supervised ML classifier for clinical condition prediction.

    Lifecycle:
      1. Admin runs: python manage.py train_ml_model
         → trains 3 classifiers, picks best by F1, saves .pkl
      2. On first predict() call, loads model from .pkl
      3. multimodal_service.py calls predict(case) before RAG+LLM steps

    predict() returns the same dict shape as _select_condition() so the
    rest of the pipeline (RAG → LLM → Doctor Review) is completely unchanged.
    """

    def __init__(self):
        self._pipeline   = None   # fitted sklearn Pipeline
        self._classes    = None   # class names (label strings)
        self._algorithm  = None   # name of selected algorithm
        self._loaded     = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_trained(self) -> bool:
        """Return True if a trained model file exists."""
        return _MODEL_PATH.exists()

    def predict(self, case) -> dict:
        """
        Predict the clinical condition for a PatientCase.

        Returns a dict compatible with _select_condition():
          {
            'prediction'        : str,    # condition name
            'confidence'        : float,  # probability 0.0-1.0
            'ml_algorithm'      : str,    # algorithm name used
            'keywords'          : list,   # empty (pipeline compat)
            'findings'          : list,   # ML-derived clinical findings
          }

        Raises:
          RuntimeError: if model is not trained yet.
        """
        self._ensure_loaded()
        features = case_to_features(case)
        probas   = self._pipeline.predict_proba(features)[0]
        pred_idx = int(np.argmax(probas))
        pred_label   = self._classes[pred_idx]
        confidence   = float(probas[pred_idx])
        findings     = self._build_findings(pred_label, features[0], probas)
        return {
            "prediction":   pred_label,
            "confidence":   round(confidence, 4),
            "ml_algorithm": self._algorithm,
            "keywords":     [],
            "findings":     findings,
        }

    def train(self) -> dict:
        """
        Train all three classifiers, compare metrics, select the best,
        and save it to disk. Returns a comprehensive training report dict.

        Selection criterion: highest weighted F1 on the 20% stratified test split.
        If F1 is tied to within 0.001, cross-validation mean F1 is used as tiebreaker.
        """
        logger.info("Starting ML model training...")
        _MODEL_DIR.mkdir(parents=True, exist_ok=True)

        df = _load_data()
        X = df[ALL_FEATURES].values.astype(float)
        y = df[TARGET_COL].values

        le = LabelEncoder()
        y_enc = le.fit_transform(y)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y_enc, test_size=0.20, random_state=42, stratify=y_enc
        )

        pipelines = _build_pipelines()
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

        results   = {}
        all_reports = {}

        for name, pipe in pipelines.items():
            logger.info("Training %s ...", name)
            pipe.fit(X_train, y_train)
            y_pred = pipe.predict(X_test)

            acc  = accuracy_score(y_test, y_pred)
            prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
            rec  = recall_score(y_test, y_pred, average="weighted", zero_division=0)
            f1   = f1_score(y_test, y_pred, average="weighted", zero_division=0)

            # 5-fold cross-validation on the full training set
            cv_f1 = cross_val_score(pipe, X_train, y_train, cv=cv,
                                    scoring="f1_weighted", n_jobs=-1)

            per_class = classification_report(
                y_test, y_pred,
                target_names=le.classes_,
                output_dict=True,
                zero_division=0,
            )
            cm = confusion_matrix(y_test, y_pred).tolist()

            results[name] = {
                "accuracy":     round(acc, 4),
                "precision":    round(prec, 4),
                "recall":       round(rec, 4),
                "f1_weighted":  round(f1, 4),
                "cv_f1_mean":   round(float(cv_f1.mean()), 4),
                "cv_f1_std":    round(float(cv_f1.std()), 4),
                "per_class":    {k: {m: round(v, 4) for m, v in v2.items()}
                                 for k, v2 in per_class.items()
                                 if isinstance(v2, dict)},
                "confusion_matrix": cm,
                "pipeline":     pipe,
            }
            logger.info(
                "%s → acc=%.4f  prec=%.4f  rec=%.4f  f1=%.4f  cv_f1=%.4f±%.4f",
                name, acc, prec, rec, f1, cv_f1.mean(), cv_f1.std()
            )

        # --- Select best model ---
        def sort_key(item):
            r = item[1]
            return (r["f1_weighted"], r["cv_f1_mean"])

        best_name, best_result = max(results.items(), key=sort_key)
        best_pipe = best_result.pop("pipeline")
        for r in results.values():
            r.pop("pipeline", None)

        # Persist
        joblib.dump(
            {
                "pipeline":  best_pipe,
                "classes":   list(le.classes_),
                "algorithm": best_name,
                "features":  ALL_FEATURES,
                "metrics":   {k: v for k, v in best_result.items()
                              if k not in ("per_class", "confusion_matrix")},
            },
            _MODEL_PATH,
        )

        # Reload into this instance immediately
        self._pipeline  = best_pipe
        self._classes   = list(le.classes_)
        self._algorithm = best_name
        self._loaded    = True

        report = {
            "selected_algorithm": best_name,
            "dataset_rows":       len(df),
            "train_rows":         len(X_train),
            "test_rows":          len(X_test),
            "n_features":         len(ALL_FEATURES),
            "n_classes":          len(le.classes_),
            "classes":            list(le.classes_),
            "model_path":         str(_MODEL_PATH),
            "all_models":         results,
            "best_metrics":       best_result,
        }

        # Save JSON report
        with open(_REPORT_PATH, "w", encoding="utf-8") as f:
            import copy
            serializable = copy.deepcopy(report)
            json.dump(serializable, f, indent=2, default=str)

        logger.info("Best model: %s  (F1=%.4f)", best_name, best_result["f1_weighted"])
        return report

    def get_training_report(self) -> dict:
        """Load and return the last saved training report, or empty dict."""
        if _REPORT_PATH.exists():
            with open(_REPORT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self):
        """Load the persisted model if not already loaded."""
        if self._loaded:
            return
        if not _MODEL_PATH.exists():
            raise RuntimeError(
                "ML model has not been trained yet.\n"
                "Run: python manage.py train_ml_model"
            )
        data = joblib.load(_MODEL_PATH)
        self._pipeline  = data["pipeline"]
        self._classes   = data["classes"]
        self._algorithm = data["algorithm"]
        self._loaded    = True
        logger.info("ML model loaded: %s (features=%d, classes=%d)",
                    self._algorithm, len(data.get("features", [])), len(self._classes))

    def _build_findings(self, prediction: str, feature_vec: np.ndarray, probas: np.ndarray) -> list:
        """Generate human-readable clinical findings from the ML prediction."""
        confidence = float(np.max(probas))
        n_symptoms = int(np.sum(feature_vec[:len(SYMPTOM_FEATURES)]))

        findings = [
            f"ML classifier ({self._algorithm}) predicted: {prediction}",
            f"Prediction confidence: {confidence*100:.1f}% based on {n_symptoms} active symptom signals",
        ]

        # Identify top-2 runner-up conditions for transparency
        sorted_idx = np.argsort(probas)[::-1]
        for i in range(1, min(3, len(sorted_idx))):
            idx = sorted_idx[i]
            runner_prob = float(probas[idx])
            if runner_prob > 0.05:
                findings.append(
                    f"Differential considered: {self._classes[idx]} "
                    f"(probability {runner_prob*100:.1f}%)"
                )

        findings.append(
            "Physician review is required — ML prediction is decision support only."
        )
        return findings


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_predictor_instance: MLPredictor = None


def get_predictor() -> MLPredictor:
    """Return the module-level singleton MLPredictor (lazy-loaded)."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = MLPredictor()
    return _predictor_instance
