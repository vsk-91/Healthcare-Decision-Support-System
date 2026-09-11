"""
Tests for the AI engine services.

Coverage:
  - chunk_text utility
  - _confidence_label helper
  - RAGService: GEMINI_API_KEY validation
  - RAGService: full retrieval path with mocked Gemini + ChromaDB
  - RAGService: empty ChromaDB collection raises RuntimeError
  - LLMService: GEMINI_API_KEY validation
  - LLMService: full generation path with mocked Gemini API
  - LLMService: API failure raises RuntimeError
  - MultimodalAnalysisService: full pipeline with mocked Gemini + ChromaDB
  - MLPredictor: feature extraction (case_to_features)
  - MLPredictor: training and prediction (real sklearn, temp directories)
  - MLPredictor: fallback to keyword selection when model not trained

IMPORTANT:
  No tests make live Gemini API calls.
  All external API paths are mocked (Gemini client, ChromaDB PersistentClient).
"""

from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings

from ai_engine.services.rag_service import RAGService, chunk_text
from ai_engine.services.llm_service import LLMService, _confidence_label


# ===========================================================================
# chunk_text utility
# ===========================================================================

class ChunkTextTests(TestCase):

    def test_short_text_returns_single_chunk(self):
        text = "Short clinical note."
        chunks = chunk_text(text, chunk_size=600, overlap=100)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_long_text_splits_into_multiple_chunks(self):
        text = "A" * 1500
        chunks = chunk_text(text, chunk_size=600, overlap=100)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 600)

    def test_overlap_present(self):
        text = "A" * 1200
        chunks = chunk_text(text, chunk_size=600, overlap=100)
        if len(chunks) >= 2:
            self.assertEqual(chunks[0][-100:], chunks[1][:100])

    def test_empty_text_returns_empty_list(self):
        chunks = chunk_text("", chunk_size=600)
        self.assertEqual(chunks, [])


# ===========================================================================
# _confidence_label helper
# ===========================================================================

class ConfidenceLabelTests(TestCase):

    def test_high_confidence(self):
        label, text = _confidence_label(0.90)
        self.assertEqual(label, "HIGH")
        self.assertIn("high", text.lower())

    def test_moderate_confidence(self):
        label, text = _confidence_label(0.75)
        self.assertEqual(label, "MODERATE")

    def test_lower_confidence(self):
        label, text = _confidence_label(0.50)
        self.assertEqual(label, "LOWER")

    def test_boundary_high(self):
        label, _ = _confidence_label(0.85)
        self.assertEqual(label, "HIGH")

    def test_boundary_moderate(self):
        label, _ = _confidence_label(0.70)
        self.assertEqual(label, "MODERATE")


# ===========================================================================
# RAGService — Gemini + ChromaDB (all external calls mocked)
# ===========================================================================

def _make_mock_gemini_client(embedding=None):
    """Return a MagicMock Gemini client that returns a fake embedding."""
    fake_embed = embedding or [0.01] * 768
    mock_embed_val = MagicMock()
    mock_embed_val.values = fake_embed
    mock_embed_resp = MagicMock()
    mock_embed_resp.embeddings = [mock_embed_val]

    mock_client = MagicMock()
    mock_client.models.embed_content.return_value = mock_embed_resp
    return mock_client


def _make_mock_chroma_collection(count=5):
    """Return a mocked ChromaDB collection with sample query results."""
    mock_coll = MagicMock()
    mock_coll.count.return_value = count
    mock_coll.query.return_value = {
        "documents": [["Hypertension is a major risk factor for stroke.",
                        "Diabetes affects glucose metabolism."]],
        "metadatas": [[
            {"topic": "Hypertension Management", "doc_id": "hypertension"},
            {"topic": "Diabetes Mellitus", "doc_id": "diabetes"},
        ]],
        "distances": [[0.10, 0.18]],
    }
    mock_coll.get.return_value = {"ids": []}
    return mock_coll


class RAGServiceGeminiTests(TestCase):

    def setUp(self):
        """Reset the RAG singleton before each test."""
        import ai_engine.services.rag_service as rs
        rs._rag_instance = None

    def tearDown(self):
        import ai_engine.services.rag_service as rs
        rs._rag_instance = None

    @override_settings(GEMINI_API_KEY='')
    def test_missing_api_key_raises_value_error(self):
        """Empty GEMINI_API_KEY must raise ValueError before any API call."""
        svc = RAGService()
        with patch.dict('os.environ', {'GEMINI_API_KEY': ''}, clear=False):
            with self.assertRaises(ValueError) as ctx:
                svc.retrieve("test query")
        self.assertIn("GEMINI_API_KEY", str(ctx.exception))

    @override_settings(GEMINI_API_KEY='fake-gemini-key-test')
    def test_retrieve_returns_list_of_strings(self):
        """retrieve() must return a non-empty list of strings."""
        mock_coll  = _make_mock_chroma_collection(count=5)
        mock_chroma = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_coll
        mock_genai = _make_mock_gemini_client()

        with patch("chromadb.PersistentClient", return_value=mock_chroma), \
             patch("google.genai.Client", return_value=mock_genai):
            svc = RAGService()
            result = svc.retrieve("headache migraine", top_k=2)

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        for item in result:
            self.assertIsInstance(item, str)

    @override_settings(GEMINI_API_KEY='fake-gemini-key-test')
    def test_retrieve_includes_topic_labels(self):
        """Result strings must be prefixed with [Topic] labels from metadata."""
        mock_coll  = _make_mock_chroma_collection(count=5)
        mock_chroma = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_coll
        mock_genai = _make_mock_gemini_client()

        with patch("chromadb.PersistentClient", return_value=mock_chroma), \
             patch("google.genai.Client", return_value=mock_genai):
            svc = RAGService()
            result = svc.retrieve("blood pressure hypertension", top_k=2)

        combined = " ".join(result)
        self.assertIn("Hypertension", combined)

    @override_settings(GEMINI_API_KEY='fake-gemini-key-test')
    def test_empty_collection_raises_runtime_error(self):
        """
        An empty ChromaDB collection must raise RuntimeError with instructions
        to run ingest_medical_knowledge — not silently return mock results.
        """
        import ai_engine.services.rag_service as rs

        mock_coll  = _make_mock_chroma_collection(count=0)
        mock_chroma = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_coll
        mock_genai = _make_mock_gemini_client()

        with patch("chromadb.PersistentClient", return_value=mock_chroma), \
             patch("google.genai.Client", return_value=mock_genai):
            # Force singleton to re-initialize inside the patch scope
            rs._rag_instance = None
            svc = RAGService()
            with self.assertRaises(RuntimeError) as ctx:
                svc.retrieve("chest pain", top_k=3)
        self.assertIn("ingest_medical_knowledge", str(ctx.exception))

    @override_settings(GEMINI_API_KEY='fake-gemini-key-test')
    def test_top_k_respected(self):
        """retrieve() must not return more than top_k results."""
        import ai_engine.services.rag_service as rs

        # Return only 1 document when queried
        mock_coll = MagicMock()
        mock_coll.count.return_value = 5
        mock_coll.query.return_value = {
            "documents": [["Hypertension is a major risk factor."]],
            "metadatas": [[{"topic": "Hypertension Management", "doc_id": "hypertension"}]],
            "distances": [[0.10]],
        }
        mock_chroma = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_coll
        mock_genai = _make_mock_gemini_client()

        with patch("chromadb.PersistentClient", return_value=mock_chroma), \
             patch("google.genai.Client", return_value=mock_genai):
            rs._rag_instance = None
            svc = RAGService()
            result = svc.retrieve("cough fever", top_k=1)

        rs._rag_instance = None
        self.assertLessEqual(len(result), 1)


    @override_settings(GEMINI_API_KEY='fake-gemini-key-test')
    def test_empty_query_returns_empty_list(self):
        """Empty query must return an empty list, not raise an error."""
        mock_coll  = _make_mock_chroma_collection(count=5)
        mock_chroma = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_coll
        mock_genai = _make_mock_gemini_client()

        with patch("chromadb.PersistentClient", return_value=mock_chroma), \
             patch("google.genai.Client", return_value=mock_genai):
            svc = RAGService()
            result = svc.retrieve("")

        self.assertEqual(result, [])


# ===========================================================================
# LLMService — Gemini (all external calls mocked)
# ===========================================================================

def _make_mock_gemini_text_response(text: str):
    """Return a MagicMock Gemini generate_content response."""
    mock_resp = MagicMock()
    mock_resp.text = text
    return mock_resp


_SAMPLE_CLINICAL_RESPONSE = """\
1. PRIMARY PREDICTION
   Predicted Condition: Hypertensive Heart Disease (98% confidence - HIGH)

2. CONFIDENCE INTERPRETATION
   The HIGH confidence reflects a very strong symptom-feature match.

3. SUPPORTING FINDINGS
   Elevated BP, headache, and family history align with hypertension.

4. RELEVANT MEDICAL CONTEXT
   ACE inhibitors are first-line treatment per DASH guidelines.

5. UNCERTAINTIES AND LIMITATIONS
   Physical examination and ECG required to exclude cardiac complications.

6. RECOMMENDED NEXT STEPS FOR PHYSICIAN REVIEW
   1. Confirm BP with serial measurements.
   2. Order ECG and renal function panel.
   3. Consider ACE inhibitor initiation after physical exam.

DISCLAIMER: This report is AI-generated decision support only. The attending physician must make
the final clinical assessment and bears full responsibility for patient care decisions.
"""


class LLMServiceGeminiTests(TestCase):

    @override_settings(GEMINI_API_KEY='', LLM_MODEL='gemini-2.5-flash')
    def test_missing_api_key_raises_value_error(self):
        """Empty GEMINI_API_KEY must raise ValueError before any API call."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': ''}, clear=False):
            svc = LLMService()
            ctx = {
                "prediction": "Test", "confidence": 0.5,
                "symptoms": "Test", "medical_history": "None",
                "medications": "None", "family_history": "None",
                "rag_context": [], "reports_summary": "None",
            }
            with self.assertRaises(ValueError) as exc_ctx:
                svc.generate_explanation(ctx)
        self.assertIn("GEMINI_API_KEY", str(exc_ctx.exception))

    @override_settings(GEMINI_API_KEY='fake-gemini-key', LLM_MODEL='gemini-2.5-flash')
    def test_generate_explanation_returns_string(self):
        """generate_explanation() must return a non-empty string."""
        mock_genai = MagicMock()
        mock_genai.models.generate_content.return_value = \
            _make_mock_gemini_text_response(_SAMPLE_CLINICAL_RESPONSE)

        with patch("google.genai.Client", return_value=mock_genai):
            svc = LLMService()
            ctx = {
                "prediction": "Hypertensive Heart Disease",
                "confidence": 0.98,
                "symptoms": "Persistent headache, BP 160/100",
                "medical_history": "Obesity",
                "medications": "None",
                "family_history": "Father had hypertension",
                "rag_context": ["[Hypertension] ACE inhibitors are first-line."],
                "reports_summary": "BP log attached",
            }
            result = svc.generate_explanation(ctx)

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 100)

    @override_settings(GEMINI_API_KEY='fake-gemini-key', LLM_MODEL='gemini-2.5-flash')
    def test_output_contains_disclaimer(self):
        """Clinical disclaimer must always be present in Gemini response."""
        mock_genai = MagicMock()
        mock_genai.models.generate_content.return_value = \
            _make_mock_gemini_text_response(_SAMPLE_CLINICAL_RESPONSE)

        with patch("google.genai.Client", return_value=mock_genai):
            svc = LLMService()
            ctx = {
                "prediction": "Test", "confidence": 0.5,
                "symptoms": "Test", "medical_history": "None",
                "medications": "None", "family_history": "None",
                "rag_context": [], "reports_summary": "None",
            }
            result = svc.generate_explanation(ctx)

        self.assertIn("DISCLAIMER", result)

    @override_settings(GEMINI_API_KEY='fake-gemini-key', LLM_MODEL='gemini-2.5-flash')
    def test_rag_context_is_passed_to_gemini_prompt(self):
        """RAG context must be included in the prompt sent to Gemini."""
        mock_genai = MagicMock()
        mock_genai.models.generate_content.return_value = \
            _make_mock_gemini_text_response(_SAMPLE_CLINICAL_RESPONSE)

        with patch("google.genai.Client", return_value=mock_genai):
            svc = LLMService()
            ctx = {
                "prediction": "Hypertension",
                "confidence": 0.88,
                "symptoms": "BP 160/100, headache",
                "medical_history": "None",
                "medications": "None",
                "family_history": "None",
                "rag_context": ["[Hypertension] ACE inhibitors are first-line treatment."],
                "reports_summary": "None",
            }
            svc.generate_explanation(ctx)

        # Verify generate_content was called and prompt includes RAG text
        self.assertTrue(mock_genai.models.generate_content.called)
        call_args = mock_genai.models.generate_content.call_args
        prompt = call_args[1].get("contents") or call_args[0][1]
        self.assertIn("ACE inhibitors", prompt)
        self.assertIn("Hypertension", prompt)

    @override_settings(GEMINI_API_KEY='fake-gemini-key', LLM_MODEL='gemini-2.5-flash')
    def test_gemini_uses_configured_model(self):
        """generate_content must be called with the configured LLM_MODEL."""
        mock_genai = MagicMock()
        mock_genai.models.generate_content.return_value = \
            _make_mock_gemini_text_response(_SAMPLE_CLINICAL_RESPONSE)

        with patch("google.genai.Client", return_value=mock_genai):
            svc = LLMService()
            ctx = {
                "prediction": "Test", "confidence": 0.5,
                "symptoms": "Test", "medical_history": "None",
                "medications": "None", "family_history": "None",
                "rag_context": [], "reports_summary": "None",
            }
            svc.generate_explanation(ctx)

        call_kwargs = mock_genai.models.generate_content.call_args[1]
        self.assertEqual(call_kwargs.get("model"), "gemini-2.5-flash")

    @override_settings(GEMINI_API_KEY='fake-gemini-key', LLM_MODEL='gemini-2.5-flash')
    def test_api_failure_raises_runtime_error(self):
        """Gemini API failure must be wrapped in RuntimeError."""
        mock_genai = MagicMock()
        mock_genai.models.generate_content.side_effect = Exception("Connection refused")

        with patch("google.genai.Client", return_value=mock_genai):
            svc = LLMService()
            ctx = {
                "prediction": "Test", "confidence": 0.5,
                "symptoms": "Test", "medical_history": "None",
                "medications": "None", "family_history": "None",
                "rag_context": [], "reports_summary": "None",
            }
            with self.assertRaises(RuntimeError) as ctx_mgr:
                svc.generate_explanation(ctx)
        self.assertIn("Gemini API call failed", str(ctx_mgr.exception))


# ===========================================================================
# MultimodalAnalysisService — Gemini pipeline (all external calls mocked)
# ===========================================================================

class MultimodalGeminiPipelineTests(TestCase):

    def setUp(self):
        import ai_engine.services.rag_service as rs
        rs._rag_instance = None

    def tearDown(self):
        import ai_engine.services.rag_service as rs
        rs._rag_instance = None

    def _make_fake_case(self):
        case = MagicMock()
        case.pk               = 999
        case.symptoms         = "Headache, nausea, sensitivity to light"
        case.chief_complaint  = "Severe headache"
        case.medical_history  = "No significant history"
        case.current_medications = "Paracetamol"
        case.family_history   = "Mother has migraines"
        mock_reports = MagicMock()
        mock_reports.exists.return_value = False
        case.medical_reports  = mock_reports
        return case

    def _mock_context(self):
        """Context manager: mocks both Gemini (embed + generate) and ChromaDB."""
        mock_coll = _make_mock_chroma_collection(count=3)
        mock_chroma = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_coll

        mock_genai = _make_mock_gemini_client()
        mock_genai.models.generate_content.return_value = \
            _make_mock_gemini_text_response(_SAMPLE_CLINICAL_RESPONSE)

        return (
            patch("chromadb.PersistentClient", return_value=mock_chroma),
            patch("google.genai.Client", return_value=mock_genai),
        )

    @override_settings(GEMINI_API_KEY='fake-gemini-key', LLM_MODEL='gemini-2.5-flash')
    def test_analyze_returns_required_keys(self):
        p1, p2 = self._mock_context()
        with p1, p2:
            from ai_engine.services.multimodal_service import MultimodalAnalysisService
            result = MultimodalAnalysisService().analyze(self._make_fake_case())
        for key in ["prediction", "confidence", "supporting_findings",
                    "rag_context", "llm_explanation", "mode"]:
            self.assertIn(key, result)

    @override_settings(GEMINI_API_KEY='fake-gemini-key', LLM_MODEL='gemini-2.5-flash')
    def test_analyze_mode_is_gemini(self):
        """mode field must be 'gemini', never 'mock'."""
        p1, p2 = self._mock_context()
        with p1, p2:
            from ai_engine.services.multimodal_service import MultimodalAnalysisService
            result = MultimodalAnalysisService().analyze(self._make_fake_case())
        self.assertEqual(result["mode"], "gemini")

    @override_settings(GEMINI_API_KEY='fake-gemini-key', LLM_MODEL='gemini-2.5-flash')
    def test_analyze_confidence_in_range(self):
        p1, p2 = self._mock_context()
        with p1, p2:
            from ai_engine.services.multimodal_service import MultimodalAnalysisService
            result = MultimodalAnalysisService().analyze(self._make_fake_case())
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)

    @override_settings(GEMINI_API_KEY='fake-gemini-key', LLM_MODEL='gemini-2.5-flash')
    def test_analyze_rag_context_not_empty(self):
        """RAG context must be retrieved and passed from ChromaDB to result."""
        p1, p2 = self._mock_context()
        with p1, p2:
            from ai_engine.services.multimodal_service import MultimodalAnalysisService
            result = MultimodalAnalysisService().analyze(self._make_fake_case())
        self.assertIsInstance(result["rag_context"], list)
        self.assertGreater(len(result["rag_context"]), 0)

    @override_settings(GEMINI_API_KEY='fake-gemini-key', LLM_MODEL='gemini-2.5-flash')
    def test_analyze_llm_explanation_has_disclaimer(self):
        """LLM explanation must contain clinical disclaimer."""
        p1, p2 = self._mock_context()
        with p1, p2:
            from ai_engine.services.multimodal_service import MultimodalAnalysisService
            result = MultimodalAnalysisService().analyze(self._make_fake_case())
        self.assertIn("DISCLAIMER", result["llm_explanation"])

    @override_settings(GEMINI_API_KEY='fake-gemini-key', LLM_MODEL='gemini-2.5-flash')
    def test_analyze_prediction_is_string(self):
        p1, p2 = self._mock_context()
        with p1, p2:
            from ai_engine.services.multimodal_service import MultimodalAnalysisService
            result = MultimodalAnalysisService().analyze(self._make_fake_case())
        self.assertIsInstance(result["prediction"], str)
        self.assertGreater(len(result["prediction"]), 0)


# ===========================================================================
# MLPredictor — unit tests (real sklearn, no Gemini API calls)
# ===========================================================================

class MLPredictorFeatureTests(TestCase):
    """Tests for case_to_features() feature extraction."""

    def _make_case(self, symptoms="", chief_complaint="", medical_history=""):
        case = MagicMock()
        case.symptoms        = symptoms
        case.chief_complaint = chief_complaint
        case.medical_history = medical_history
        case.age         = None
        case.systolic_bp = None
        case.bmi         = None
        return case

    def test_returns_correct_shape(self):
        from ai_engine.services.ml_predictor import case_to_features, ALL_FEATURES
        case = self._make_case(symptoms="headache fatigue")
        arr = case_to_features(case)
        self.assertEqual(arr.shape, (1, len(ALL_FEATURES)))

    def test_headache_flag_set(self):
        from ai_engine.services.ml_predictor import case_to_features, SYMPTOM_FEATURES
        case = self._make_case(symptoms="severe headache and nausea")
        arr = case_to_features(case)
        idx = SYMPTOM_FEATURES.index("headache")
        self.assertEqual(arr[0, idx], 1)

    def test_fever_and_cough_flags_set(self):
        from ai_engine.services.ml_predictor import case_to_features, SYMPTOM_FEATURES
        case = self._make_case(symptoms="high fever and cough")
        arr = case_to_features(case)
        self.assertEqual(arr[0, SYMPTOM_FEATURES.index("fever")], 1)
        self.assertEqual(arr[0, SYMPTOM_FEATURES.index("cough")], 1)

    def test_empty_case_returns_zero_symptoms(self):
        from ai_engine.services.ml_predictor import case_to_features, SYMPTOM_FEATURES
        case = self._make_case(symptoms="")
        arr = case_to_features(case)
        self.assertEqual(int(arr[0, :len(SYMPTOM_FEATURES)].sum()), 0)

    def test_back_pain_flag_from_chief_complaint(self):
        from ai_engine.services.ml_predictor import case_to_features, SYMPTOM_FEATURES
        case = self._make_case(chief_complaint="severe lumbar back pain")
        arr = case_to_features(case)
        self.assertEqual(arr[0, SYMPTOM_FEATURES.index("back_pain")], 1)

    def test_numeric_defaults_applied(self):
        from ai_engine.services.ml_predictor import (
            case_to_features, SYMPTOM_FEATURES,
            _DEFAULT_AGE, _DEFAULT_SBP, _DEFAULT_BMI,
        )
        case = self._make_case()
        arr = case_to_features(case)
        n = len(SYMPTOM_FEATURES)
        self.assertEqual(arr[0, n],   _DEFAULT_AGE)
        self.assertEqual(arr[0, n+1], _DEFAULT_SBP)
        self.assertAlmostEqual(arr[0, n+2], _DEFAULT_BMI, places=1)

    def test_polyuria_polydipsia_flags(self):
        from ai_engine.services.ml_predictor import case_to_features, SYMPTOM_FEATURES
        case = self._make_case(symptoms="frequent urination excessive thirst weight loss")
        arr = case_to_features(case)
        self.assertEqual(arr[0, SYMPTOM_FEATURES.index("polyuria")], 1)
        self.assertEqual(arr[0, SYMPTOM_FEATURES.index("polydipsia")], 1)

    def test_photophobia_flag(self):
        from ai_engine.services.ml_predictor import case_to_features, SYMPTOM_FEATURES
        case = self._make_case(symptoms="sensitive to light throbbing headache nausea")
        arr = case_to_features(case)
        self.assertEqual(arr[0, SYMPTOM_FEATURES.index("photophobia")], 1)


class MLPredictorTrainingTests(TestCase):
    """ML training tests — real sklearn on real dataset, isolated temp dirs."""

    def _make_case(self, symptoms="headache nausea"):
        case = MagicMock()
        case.symptoms        = symptoms
        case.chief_complaint = ""
        case.medical_history = ""
        case.age = case.systolic_bp = case.bmi = None
        return case

    def _tmp_predictor(self):
        import tempfile
        from pathlib import Path
        import ai_engine.services.ml_predictor as ml_mod
        tmpdir = tempfile.mkdtemp()
        ml_mod._orig_model_dir  = ml_mod._MODEL_DIR
        ml_mod._orig_model_path = ml_mod._MODEL_PATH
        ml_mod._orig_report     = ml_mod._REPORT_PATH
        ml_mod._MODEL_DIR   = Path(tmpdir)
        ml_mod._MODEL_PATH  = Path(tmpdir) / "best_model.pkl"
        ml_mod._REPORT_PATH = Path(tmpdir) / "training_report.json"
        from ai_engine.services.ml_predictor import MLPredictor
        return MLPredictor(), tmpdir

    def _restore(self):
        import ai_engine.services.ml_predictor as ml_mod
        ml_mod._MODEL_DIR   = ml_mod._orig_model_dir
        ml_mod._MODEL_PATH  = ml_mod._orig_model_path
        ml_mod._REPORT_PATH = ml_mod._orig_report

    def test_train_returns_required_report_keys(self):
        import shutil
        p, tmpdir = self._tmp_predictor()
        try:
            report = p.train()
            for key in ["selected_algorithm", "dataset_rows", "train_rows",
                        "test_rows", "n_features", "n_classes", "classes",
                        "all_models", "best_metrics"]:
                self.assertIn(key, report, msg=f"Missing key: {key}")
        finally:
            self._restore()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_train_selects_one_of_three_algorithms(self):
        import shutil
        p, tmpdir = self._tmp_predictor()
        try:
            report = p.train()
            self.assertIn(report["selected_algorithm"],
                          ["Logistic Regression", "Decision Tree", "Random Forest"])
        finally:
            self._restore()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_all_three_models_evaluated_with_metrics(self):
        import shutil
        p, tmpdir = self._tmp_predictor()
        try:
            report = p.train()
            for algo in ["Logistic Regression", "Decision Tree", "Random Forest"]:
                self.assertIn(algo, report["all_models"])
                m = report["all_models"][algo]
                for metric in ["accuracy", "precision", "recall", "f1_weighted", "cv_f1_mean"]:
                    self.assertIn(metric, m)
                    self.assertGreaterEqual(m[metric], 0.0)
                    self.assertLessEqual(m[metric], 1.0)
        finally:
            self._restore()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_best_model_metrics_reasonable(self):
        import shutil
        p, tmpdir = self._tmp_predictor()
        try:
            report = p.train()
            acc = report["best_metrics"]["accuracy"]
            self.assertGreater(acc, 0.60, msg=f"Best model accuracy too low: {acc:.4f}")
        finally:
            self._restore()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_predict_returns_required_keys(self):
        import shutil
        p, tmpdir = self._tmp_predictor()
        try:
            p.train()
            result = p.predict(self._make_case("headache throbbing nausea photophobia"))
            for key in ["prediction", "confidence", "ml_algorithm", "findings"]:
                self.assertIn(key, result)
            self.assertIsInstance(result["prediction"], str)
            self.assertGreater(len(result["prediction"]), 0)
            self.assertGreaterEqual(result["confidence"], 0.0)
            self.assertLessEqual(result["confidence"], 1.0)
            self.assertIsInstance(result["findings"], list)
        finally:
            self._restore()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_predict_without_training_raises_runtime_error(self):
        import tempfile, shutil
        import ai_engine.services.ml_predictor as ml_mod
        from pathlib import Path
        tmpdir = tempfile.mkdtemp()
        orig = ml_mod._MODEL_PATH
        try:
            ml_mod._MODEL_PATH = Path(tmpdir) / "nonexistent.pkl"
            from ai_engine.services.ml_predictor import MLPredictor
            p = MLPredictor()
            with self.assertRaises(RuntimeError):
                p.predict(self._make_case("test"))
        finally:
            ml_mod._MODEL_PATH = orig
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_is_trained_false_when_no_model_file(self):
        import tempfile, shutil
        import ai_engine.services.ml_predictor as ml_mod
        from pathlib import Path
        tmpdir = tempfile.mkdtemp()
        orig = ml_mod._MODEL_PATH
        try:
            ml_mod._MODEL_PATH = Path(tmpdir) / "nonexistent.pkl"
            from ai_engine.services.ml_predictor import MLPredictor
            p = MLPredictor()
            self.assertFalse(p.is_trained())
        finally:
            ml_mod._MODEL_PATH = orig
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_is_trained_true_after_training(self):
        import shutil
        p, tmpdir = self._tmp_predictor()
        try:
            self.assertFalse(p.is_trained())
            p.train()
            self.assertTrue(p.is_trained())
        finally:
            self._restore()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_training_report_json_saved(self):
        import shutil, json
        import ai_engine.services.ml_predictor as ml_mod
        p, tmpdir = self._tmp_predictor()
        try:
            p.train()
            self.assertTrue(ml_mod._REPORT_PATH.exists())
            with open(ml_mod._REPORT_PATH) as f:
                data = json.load(f)
            self.assertIn("selected_algorithm", data)
        finally:
            self._restore()
            shutil.rmtree(tmpdir, ignore_errors=True)


# ===========================================================================
# MLPredictor — keyword fallback when model not trained
# ===========================================================================

class MLPredictorFallbackTests(TestCase):
    """Tests that multimodal_service uses keyword fallback when no model trained."""

    def _make_fake_case(self):
        case = MagicMock()
        case.pk              = 999
        case.symptoms        = "Headache, nausea, sensitivity to light"
        case.chief_complaint = "Severe headache"
        case.medical_history = "No significant history"
        case.current_medications = "Paracetamol"
        case.family_history  = "Mother has migraines"
        mock_reports = MagicMock()
        mock_reports.exists.return_value = False
        case.medical_reports = mock_reports
        return case

    @override_settings(GEMINI_API_KEY='fake-gemini-key', LLM_MODEL='gemini-2.5-flash')
    def test_pipeline_runs_without_trained_model(self):
        """
        When no ML model is trained, the pipeline must still complete
        using the keyword-based fallback (and Gemini for RAG + LLM).
        """
        import tempfile, shutil
        import ai_engine.services.ml_predictor as ml_mod
        import ai_engine.services.rag_service as rs
        from pathlib import Path

        tmpdir   = tempfile.mkdtemp()
        orig_path = ml_mod._MODEL_PATH
        orig_inst = ml_mod._predictor_instance
        rs._rag_instance = None

        mock_coll = _make_mock_chroma_collection(count=3)
        mock_chroma = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_coll
        mock_genai = _make_mock_gemini_client()
        mock_genai.models.generate_content.return_value = \
            _make_mock_gemini_text_response(_SAMPLE_CLINICAL_RESPONSE)

        try:
            ml_mod._MODEL_PATH = Path(tmpdir) / "nonexistent.pkl"
            ml_mod._predictor_instance = None

            with patch("chromadb.PersistentClient", return_value=mock_chroma), \
                 patch("google.genai.Client", return_value=mock_genai):
                from ai_engine.services.multimodal_service import MultimodalAnalysisService
                svc = MultimodalAnalysisService()
                result = svc.analyze(self._make_fake_case())

            self.assertIn("prediction", result)
            self.assertGreater(len(result["prediction"]), 0)
            self.assertIn("rag_context", result)
            self.assertIn("llm_explanation", result)
            self.assertEqual(result["mode"], "gemini")
        finally:
            ml_mod._MODEL_PATH = orig_path
            ml_mod._predictor_instance = orig_inst
            rs._rag_instance = None
            shutil.rmtree(tmpdir, ignore_errors=True)
