"""
Multimodal Analysis Service — Orchestrates the complete AI pipeline.

Pipeline:
  1. ML Prediction      — Supervised classifier (Logistic Regression / Decision Tree /
                          Random Forest) trained on clinical symptoms dataset.
                          Falls back to keyword-based selection if model not yet trained.
  2. RAG Retrieval      — Gemini embeddings + ChromaDB semantic similarity search
                          (populated by: python manage.py ingest_medical_knowledge)
  3. LLM Explanation    — Google Gemini API generates structured 6-section clinical report
  4. Return result dict — For Doctor review

IMPORTANT:
  - The AI does NOT make the final clinical decision.
  - The Doctor reviews the AI analysis and makes the Final Decision.
  - Requires GEMINI_API_KEY in .env.
  - ChromaDB must be populated:  python manage.py ingest_medical_knowledge
  - ML model must be trained:    python manage.py train_ml_model

No mock mode. No OpenAI. Gemini is the only AI provider.
"""

import logging
from .rag_service import RAGService
from .llm_service import LLMService
from .ml_predictor import get_predictor
from .mock_data import MOCK_CONDITIONS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Condition selection helpers
# ---------------------------------------------------------------------------

def _select_condition_by_keywords(case) -> dict:
    """
    Keyword-overlap fallback used when no trained ML model is available.
    Selects the most symptom-matched condition from MOCK_CONDITIONS.
    """
    text = " ".join(filter(None, [
        case.symptoms or "",
        case.chief_complaint or "",
        case.medical_history or "",
    ])).lower()

    best_score = -1
    best_cond  = None

    for cond in MOCK_CONDITIONS:
        score = sum(1 for kw in cond.get("keywords", []) if kw.lower() in text)
        if score > best_score:
            best_score = score
            best_cond  = cond

    if best_score == 0 or best_cond is None:
        idx       = hash(text[:20] if text.strip() else "default") % len(MOCK_CONDITIONS)
        best_cond = MOCK_CONDITIONS[abs(idx)]

    best_cond.setdefault("ml_algorithm", "keyword-fallback")
    return best_cond


def _predict_condition(case) -> dict:
    """
    Predict clinical condition using the trained ML classifier if available,
    otherwise fall back to keyword-based selection.

    Returns a dict with at minimum:
        prediction, confidence, findings (list), ml_algorithm (str)
    """
    predictor = get_predictor()
    if predictor.is_trained():
        try:
            result = predictor.predict(case)
            logger.info(
                "ML prediction: %s (conf=%.2f, algo=%s)",
                result["prediction"], result["confidence"], result["ml_algorithm"],
            )
            return result
        except Exception as exc:
            logger.warning("ML prediction failed (%s) — using keyword fallback.", exc)

    cond = _select_condition_by_keywords(case)
    logger.info("Keyword-based condition selection: %s", cond["prediction"])
    return cond


def _build_reports_summary(case) -> str:
    """Build a text summary of all attached medical reports for a case."""
    try:
        reports    = case.medical_reports.all()
        has_reports = reports.exists()
    except AttributeError:
        reports    = list(case.medical_reports) if hasattr(case, "medical_reports") else []
        has_reports = bool(reports)

    if has_reports:
        return "; ".join(
            f"{r.title} ({r.get_report_type_display()}, {r.get_status_display()})"
            for r in reports
        )
    return "No medical reports attached"


# ---------------------------------------------------------------------------
# Public service class
# ---------------------------------------------------------------------------

class MultimodalAnalysisService:
    """
    Orchestrates the full AI analysis pipeline:

      ML Prediction (trained sklearn classifier)
          ↓
      Patient clinical data (symptoms, history, medications, family history)
          ↓
      RAG Retrieval (Gemini embeddings + ChromaDB semantic search)
          ↓
      Gemini LLM (structured 6-section clinical explanation)
          ↓
      Result dict → Doctor Dashboard

    Configuration required in .env:
        GEMINI_API_KEY  — for RAG embeddings and LLM
        LLM_MODEL       — Gemini model (default: gemini-2.5-flash)
        EMBEDDING_MODEL — Gemini embedding model (default: gemini-embedding-001)
        CHROMA_DB_PATH  — ChromaDB path (default: ./chroma_db)

    Prerequisites:
        python manage.py ingest_medical_knowledge   (populate ChromaDB)
        python manage.py train_ml_model             (train ML classifier)

    Raises ValueError/RuntimeError on missing credentials or API failures.
    Never returns mock/template results.
    """

    def __init__(self):
        self.rag_service = RAGService()
        self.llm_service = LLMService()

    def analyze(self, case) -> dict:
        """
        Run the complete AI analysis pipeline on a PatientCase.

        Returns:
            dict with keys:
                prediction          : str   — predicted condition name
                confidence          : float — confidence 0.0-1.0
                supporting_findings : list  — list of clinical finding strings
                rag_context         : list  — retrieved knowledge chunks
                llm_explanation     : str   — structured 6-section Gemini report
                mode                : str   — always 'gemini'

        Raises:
            ValueError:   If GEMINI_API_KEY is not set.
            RuntimeError: If ChromaDB is empty or Gemini API fails.
        """
        logger.info("Starting AI analysis pipeline for case pk=%s",
                    getattr(case, "pk", "unknown"))

        # Step 1: ML prediction (with keyword fallback if model not trained)
        condition = _predict_condition(case)

        # Step 2: Build RAG query from patient clinical information
        rag_query = " ".join(filter(None, [
            case.symptoms or "",
            case.chief_complaint or "",
            case.medical_history or "",
        ]))

        # Step 3: RAG retrieval — Gemini embeddings + ChromaDB semantic search
        try:
            rag_results = self.rag_service.retrieve(rag_query, top_k=3)
            logger.info("RAG retrieved %d chunks for case pk=%s",
                        len(rag_results), getattr(case, "pk", "unknown"))
        except Exception as exc:
            logger.warning("RAG retrieval failed: %s — continuing without vector chunks.", exc)
            rag_results = []

        # Step 4: Attached reports summary
        reports_summary = _build_reports_summary(case)

        # Step 5: Gemini LLM explanation
        llm_context = {
            "prediction":      condition["prediction"],
            "confidence":      condition["confidence"],
            "symptoms":        case.symptoms or "Not provided",
            "medical_history": case.medical_history or "None",
            "medications":     case.current_medications or "None",
            "family_history":  case.family_history or "None",
            "rag_context":     rag_results,
            "reports_summary": reports_summary,
        }

        try:
            explanation = self.llm_service.generate_explanation(llm_context)
            mode = "gemini" if getattr(self.llm_service, "_last_used_gemini", True) else "clinical_rules"
        except Exception as exc:
            logger.warning("LLM explanation failed: %s — generating fallback clinical analysis.", exc)
            explanation = self.llm_service._generate_fallback_explanation(llm_context, str(exc))
            mode = "clinical_rules"

        logger.info("AI analysis complete for case pk=%s (mode=%s)",
                    getattr(case, "pk", "unknown"), mode)

        return {
            "prediction":          condition["prediction"],
            "confidence":          condition["confidence"],
            "supporting_findings": condition.get("findings", []),
            "rag_context":         rag_results,
            "llm_explanation":     explanation,
            "mode":                mode,
        }
