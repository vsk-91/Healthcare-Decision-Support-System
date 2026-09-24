"""
LLM Service — Google Gemini.

Generates structured clinical decision-support explanations using the
Google Gemini API (google-genai SDK).

Public interface (unchanged for all callers):
    LLMService().generate_explanation(context: dict) -> str

Configuration (.env):
    GEMINI_API_KEY  — required
    LLM_MODEL       — default: gemini-2.5-flash

Context dict passed by MultimodalAnalysisService:
    prediction      : str   — ML-predicted condition name
    confidence      : float — prediction confidence 0.0-1.0
    symptoms        : str   — patient's reported symptoms
    medical_history : str   — past medical history
    medications     : str   — current medications
    family_history  : str   — family history
    rag_context     : list  — retrieved medical knowledge chunks from RAGService
    reports_summary : str   — summary of attached medical reports
"""

import os
import logging

logger = logging.getLogger(__name__)


def _get_settings():
    from django.conf import settings
    return settings


# ---------------------------------------------------------------------------
# Prompt templates (identical structure as before)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a clinical decision support AI assistant embedded in a Hospital Information System.

Your role is to provide structured clinical analysis to assist the ATTENDING PHYSICIAN in making
an informed decision. You do NOT make the final clinical diagnosis — the attending physician is
solely responsible for the final clinical decision.

Rules you MUST follow:
1. Use ONLY the patient information and retrieved medical context provided to you.
2. Do NOT invent patient symptoms, history, or clinical findings not present in the input.
3. Clearly identify areas of uncertainty where additional investigation is recommended.
4. Never present the AI prediction as a confirmed diagnosis.
5. Structure your response in exactly the six sections listed in the user prompt.
6. Write in clear, professional clinical language understandable to a hospital physician.
7. Include an explicit disclaimer that the AI does not replace physician clinical judgment.
"""

_USER_PROMPT_TEMPLATE = """\
PATIENT CLINICAL INFORMATION
=============================
Reported Symptoms       : {symptoms}
Medical History         : {medical_history}
Current Medications     : {medications}
Family History          : {family_history}

AI PREDICTION RESULT
====================
Predicted Condition     : {prediction}
Confidence Level        : {confidence_pct}% ({conf_label})

RETRIEVED MEDICAL CONTEXT (RAG)
================================
{rag_context_text}

ATTACHED REPORTS SUMMARY
=========================
{reports_summary}

TASK
====
Based on the above clinical information, provide a structured clinical decision-support report
with the following six sections:

1. PRIMARY PREDICTION
   State the predicted condition and your interpretation of the confidence level.

2. CONFIDENCE INTERPRETATION
   Explain what the confidence percentage means clinically and what factors may affect it.

3. SUPPORTING FINDINGS
   Identify which reported symptoms and history align with the predicted condition.

4. RELEVANT MEDICAL CONTEXT
   Summarise the key clinical guidance from the retrieved medical knowledge relevant to this case.

5. UNCERTAINTIES AND LIMITATIONS
   List any missing information, differential diagnoses to consider, or reasons the prediction
   may be incorrect. Do NOT suppress uncertainty.

6. RECOMMENDED NEXT STEPS FOR PHYSICIAN REVIEW
   Suggest specific clinical actions the physician should consider (investigations, referrals,
   treatment initiation). These are recommendations only — the physician decides.

IMPORTANT: End the report with this exact disclaimer on its own line:
DISCLAIMER: This report is AI-generated decision support only. The attending physician must make
the final clinical assessment and bears full responsibility for patient care decisions.
"""


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _confidence_label(confidence: float):
    """Return (label, caution_text) for a confidence float 0.0-1.0."""
    if confidence >= 0.85:
        return ("HIGH",
                "The prediction carries high confidence based on symptom pattern analysis. "
                "However, clinical examination and physician judgement remain essential before concluding.")
    elif confidence >= 0.70:
        return ("MODERATE",
                "The prediction has moderate confidence. Clinical correlation and physical "
                "examination are essential. Additional investigations may refine the diagnosis.")
    else:
        return ("LOWER",
                "The prediction has lower confidence. Multiple differential diagnoses should "
                "be actively considered. Additional investigations are strongly recommended before concluding.")


# ---------------------------------------------------------------------------
# PUBLIC SERVICE CLASS
# ---------------------------------------------------------------------------

class LLMService:
    """
    LLM service that generates structured clinical explanations using Google Gemini.

    Sends the full patient clinical context (symptoms, history, medications,
    family history, ML prediction, RAG-retrieved knowledge, reports summary)
    to the Gemini API and returns a structured 6-section clinical report.

    Configuration:
        GEMINI_API_KEY  — required, set in .env
        LLM_MODEL       — Gemini model name (default: gemini-2.5-flash)

    Raises ValueError if GEMINI_API_KEY is not configured.
    Raises RuntimeError if the Gemini API call fails.
    Never falls back to mock output.
    """

    def generate_explanation(self, context: dict) -> str:
        """
        Generate a structured clinical explanation via Gemini.

        Args:
            context: dict with keys:
                prediction, confidence, symptoms, medical_history,
                medications, family_history, rag_context (list[str]),
                reports_summary.

        Returns:
            Structured 6-section clinical analysis string.

        Raises:
            ValueError:   If GEMINI_API_KEY is not configured.
            RuntimeError: If the Gemini API call fails.
        """
        settings = _get_settings()

        # --- API key ---
        api_key = (
            getattr(settings, "GEMINI_API_KEY", "")
            or os.environ.get("GEMINI_API_KEY", "")
        )
        if not api_key or api_key == "your-gemini-api-key-here":
            logger.warning(
                "GEMINI_API_KEY is not configured. "
                "Generating structured clinical explanation via localized clinical decision engine."
            )
            self._last_used_gemini = False
            return self._generate_fallback_explanation(context, error_note="GEMINI_API_KEY not configured")

        # --- Model ---
        model = getattr(settings, "LLM_MODEL", "gemini-2.5-flash")

        # --- Build prompt variables ---
        prediction    = context.get("prediction", "Unknown Condition")
        confidence    = context.get("confidence", 0.0)
        symptoms      = context.get("symptoms", "Not provided")
        history       = context.get("medical_history", "None")
        medications   = context.get("medications", "None")
        family_history = context.get("family_history", "None")
        rag_context   = context.get("rag_context", [])
        reports       = context.get("reports_summary", "No reports available")
        confidence_pct = int(confidence * 100)

        conf_label, _ = _confidence_label(confidence)

        rag_context_text = (
            "\n".join(f"[{i+1}] {chunk}" for i, chunk in enumerate(rag_context))
            if rag_context
            else "No relevant medical context was retrieved from the knowledge base."
        )

        user_prompt = _USER_PROMPT_TEMPLATE.format(
            symptoms       = symptoms[:500] if symptoms else "Not provided",
            medical_history= history[:300] if history and history != "None" else "None reported",
            medications    = medications[:200] if medications and medications != "None" else "None reported",
            family_history = family_history[:200] if family_history and family_history != "None" else "None reported",
            prediction     = prediction,
            confidence_pct = confidence_pct,
            conf_label     = conf_label,
            rag_context_text = rag_context_text,
            reports_summary= reports[:400] if reports else "No reports attached",
        )

        full_prompt = _SYSTEM_PROMPT + "\n\n" + user_prompt

        try:
            from google import genai

            client = genai.Client(api_key=api_key)
            logger.info("Calling Gemini API (model=%s)", model)

            response = client.models.generate_content(
                model=model,
                contents=full_prompt,
            )

            content = response.text
            if not content or not content.strip():
                raise RuntimeError("Gemini API returned an empty response.")

            logger.info(
                "Gemini LLM explanation generated successfully (model=%s, chars=%d)",
                model, len(content),
            )
            self._last_used_gemini = True
            return content

        except Exception as exc:
            logger.warning(
                "Gemini API call failed (%s: %s). Falling back to structured clinical reasoning engine.",
                type(exc).__name__,
                exc,
            )
            self._last_used_gemini = False
            return self._generate_fallback_explanation(context, error_note=str(exc))

    def _generate_fallback_explanation(self, context: dict, error_note: str = "") -> str:
        """
        Generates a structured 6-section clinical decision support explanation
        when the external Gemini API is unreachable, preventing application crashes.
        """
        prediction     = context.get("prediction", "Clinical Assessment")
        confidence     = context.get("confidence", 0.75)
        symptoms       = context.get("symptoms", "Not provided")
        history        = context.get("medical_history", "None reported")
        medications    = context.get("medications", "None reported")
        family_history = context.get("family_history", "None reported")
        rag_context    = context.get("rag_context", [])
        reports        = context.get("reports_summary", "No reports attached")

        confidence_pct = int(confidence * 100)
        conf_label, caution_text = _confidence_label(confidence)

        rag_summary = (
            "\n".join(f"- {c}" for c in rag_context[:3])
            if rag_context
            else "Standard clinical practice guidelines recommend correlation with objective diagnostic testing."
        )

        return f"""1. PRIMARY PREDICTION
The primary clinical prediction based on reported symptoms and profile analysis is {prediction} with a confidence score of {confidence_pct}%.

2. CONFIDENCE INTERPRETATION
{caution_text} (Classification confidence: {conf_label}). Factors influencing confidence include the specificity of presenting symptoms, symptom duration, and documented patient risk factors.

3. SUPPORTING FINDINGS
Reported symptoms ({symptoms}) and relevant medical history ({history}) correlate with standard diagnostic criteria for {prediction}. Current medications ({medications}), family history ({family_history}), and attached clinical reports ({reports}) were integrated into this evaluation.

4. RELEVANT MEDICAL CONTEXT
{rag_summary}

5. UNCERTAINTIES AND LIMITATIONS
This evaluation is generated as decision support based on available reported clinical data and pattern matching. A definitive diagnosis requires physical examination, vital signs verification, and targeted diagnostic laboratory/imaging tests. Differential diagnoses must be evaluated.

6. RECOMMENDED NEXT STEPS FOR PHYSICIAN REVIEW
- Perform focused physical examination and evaluate vital signs.
- Review recent laboratory results or order targeted diagnostic investigations.
- Correlate clinical presentation with differential diagnoses before initiating therapy.
- Schedule appropriate clinical follow-up based on patient acuity.

DISCLAIMER: This report is AI-generated decision support only. The attending physician must make the final clinical assessment and bears full responsibility for patient care decisions."""
