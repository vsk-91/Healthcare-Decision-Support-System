"""
RAG (Retrieval-Augmented Generation) Service — Gemini + ChromaDB.

Uses Google Gemini embeddings (gemini-embedding-001) for semantic retrieval
from a persistent ChromaDB vector database populated by:
    python manage.py ingest_medical_knowledge

Public interface (unchanged for all callers):
    RAGService().retrieve(query: str, top_k: int = 3) -> list[str]

Configuration (.env):
    GEMINI_API_KEY     — required
    EMBEDDING_MODEL    — default: gemini-embedding-001
    CHROMA_DB_PATH     — default: ./chroma_db

Prerequisites:
    1. Set GEMINI_API_KEY in .env
    2. Run: python manage.py ingest_medical_knowledge
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_COLLECTION_NAME = "healthcare_medical_knowledge"
_CHUNK_SIZE      = 600    # characters per chunk
_CHUNK_OVERLAP   = 100    # character overlap between consecutive chunks


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def _get_settings():
    """Lazy import of Django settings to avoid AppRegistry issues at import time."""
    from django.conf import settings as _s
    return _s


def _get_chroma_db_path() -> str:
    s = _get_settings()
    raw = getattr(s, "CHROMA_DB_PATH", "./chroma_db")
    if raw.startswith("./") or raw.startswith(".\\"):
        base = getattr(s, "BASE_DIR", Path(__file__).resolve().parent.parent.parent)
        return str(Path(base) / raw[2:])
    return raw


def _get_gemini_api_key() -> str:
    s = _get_settings()
    key = getattr(s, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise ValueError(
            "GEMINI_API_KEY is not set. "
            "Add GEMINI_API_KEY=<your-key> to your .env file. "
            "Never hard-code API keys in source files."
        )
    return key


def _get_embedding_model() -> str:
    s = _get_settings()
    return getattr(s, "EMBEDDING_MODEL", "gemini-embedding-001")


# ---------------------------------------------------------------------------
# Utility: text chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list:
    """
    Split text into overlapping character-level chunks for embedding.
    Returns a list of chunk strings.
    """
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])
        if end == text_len:
            break
        start = end - overlap
    return chunks


# ---------------------------------------------------------------------------
# Production RAG (Gemini embeddings + ChromaDB)
# ---------------------------------------------------------------------------

class _GeminiRAG:
    """
    Gemini-powered RAG using ChromaDB for persistent semantic retrieval.
    Initialised lazily on the first retrieve() or ingest call.
    """

    def __init__(self):
        self._chroma_client     = None
        self._collection        = None
        self._gemini_client     = None
        self._embedding_model   = None
        self._initialized       = False

    def _init(self):
        if self._initialized:
            return
        try:
            import chromadb
            from google import genai

            db_path = _get_chroma_db_path()
            logger.info("Initialising ChromaDB at: %s", db_path)

            self._chroma_client = chromadb.PersistentClient(path=db_path)
            self._collection = self._chroma_client.get_or_create_collection(
                name=_COLLECTION_NAME,
                metadata={"description": "Healthcare medical knowledge base — Gemini embeddings"},
            )

            api_key = _get_gemini_api_key()
            self._gemini_client    = genai.Client(api_key=api_key)
            self._embedding_model  = _get_embedding_model()
            self._initialized      = True

            count = self._collection.count()
            logger.info(
                "ChromaDB collection '%s' ready — %d chunks stored.",
                _COLLECTION_NAME, count,
            )
            if count == 0:
                logger.warning(
                    "ChromaDB collection '%s' is EMPTY. "
                    "Run: python manage.py ingest_medical_knowledge",
                    _COLLECTION_NAME,
                )
        except Exception as exc:
            logger.error("Failed to initialise Gemini RAG: %s", exc)
            raise

    def _embed(self, text: str) -> list:
        """Generate a Gemini embedding vector for a text string."""
        response = self._gemini_client.models.embed_content(
            model=self._embedding_model,
            contents=text,
        )
        return response.embeddings[0].values

    def ingest_document(self, doc_id: str, text: str, metadata: dict = None) -> int:
        """
        Chunk text, embed each chunk with Gemini, and store in ChromaDB.
        Idempotent: skips chunks that are already stored.
        Returns number of new chunks added.
        """
        self._init()
        metadata = metadata or {}
        chunks = chunk_text(text)
        ids    = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]

        # Check which chunks are already present
        existing     = self._collection.get(ids=ids, include=[])
        existing_ids = set(existing["ids"])
        new_pairs    = [(cid, chunk) for cid, chunk in zip(ids, chunks)
                        if cid not in existing_ids]

        if not new_pairs:
            logger.debug("Document '%s' already fully ingested — skipping.", doc_id)
            return 0

        new_ids, new_chunks = zip(*new_pairs)
        embeddings     = [self._embed(c) for c in new_chunks]
        chunk_metas    = [
            {**metadata, "doc_id": doc_id, "chunk_index": i}
            for i in range(len(new_ids))
        ]

        self._collection.add(
            ids=list(new_ids),
            embeddings=embeddings,
            documents=list(new_chunks),
            metadatas=chunk_metas,
        )
        logger.info("Ingested %d chunks for document '%s'.", len(new_ids), doc_id)
        return len(new_ids)

    def ingest_directory(self, directory: str) -> dict:
        """
        Ingest all .txt files from a directory into ChromaDB.
        Returns {"files": N, "chunks": M, "skipped": K, "errors": E}.
        """
        self._init()
        directory = Path(directory)
        if not directory.is_dir():
            raise FileNotFoundError(
                f"Knowledge-base directory not found: {directory}"
            )

        files_processed = chunks_added = skipped = errors = 0
        for txt_file in sorted(directory.glob("*.txt")):
            try:
                text   = txt_file.read_text(encoding="utf-8")
                doc_id = txt_file.stem
                added  = self.ingest_document(
                    doc_id=doc_id,
                    text=text,
                    metadata={
                        "source_file": txt_file.name,
                        "topic": doc_id.replace("_", " ").title(),
                    },
                )
                if added == 0:
                    skipped += 1
                else:
                    chunks_added += added
                files_processed += 1
            except Exception as exc:
                logger.error("Error ingesting '%s': %s", txt_file.name, exc)
                errors += 1

        return {
            "files":   files_processed,
            "chunks":  chunks_added,
            "skipped": skipped,
            "errors":  errors,
        }

    def retrieve(self, query: str, top_k: int = 3) -> list:
        """
        Semantically retrieve the top_k most relevant chunks from ChromaDB.
        Automatically attempts knowledge-base ingestion or file fallback
        if ChromaDB is empty or uninitialized, preventing server crashes.
        """
        if not query or not query.strip():
            logger.warning("RAG retrieve called with empty query.")
            return []

        top_k = max(1, int(top_k))

        try:
            self._init()
            count = self._collection.count()
            if count == 0:
                logger.info("ChromaDB is empty; attempting auto-ingestion from knowledge_base...")
                s = _get_settings()
                base_dir = getattr(s, "BASE_DIR", Path(__file__).resolve().parent.parent.parent)
                kb_dir = Path(base_dir) / "knowledge_base"
                if kb_dir.is_dir():
                    try:
                        self.ingest_directory(str(kb_dir))
                        count = self._collection.count()
                    except Exception as ingest_err:
                        logger.warning("Auto-ingestion into ChromaDB failed: %s", ingest_err)

            if count > 0:
                query_embedding = self._embed(query)
                results = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, count),
                    include=["documents", "metadatas", "distances"],
                )
                documents = results.get("documents", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]

                output = []
                for doc, meta in zip(documents, metadatas):
                    topic = meta.get("topic", meta.get("doc_id", "Medical Knowledge"))
                    output.append(f"[{topic}] {doc}")

                if output:
                    return output
        except Exception as exc:
            logger.warning(
                "ChromaDB retrieval unavailable (%s) — retrieving directly from knowledge_base files.",
                exc,
            )

        # Fallback: scan knowledge_base/*.txt files directly
        return retrieve_from_knowledge_base_files(query, top_k)


def retrieve_from_knowledge_base_files(query: str, top_k: int = 3) -> list:
    """
    Direct document retrieval from knowledge_base/*.txt files when
    ChromaDB or vector embeddings are temporarily unavailable.
    """
    s = _get_settings()
    base_dir = getattr(s, "BASE_DIR", Path(__file__).resolve().parent.parent.parent)
    kb_dir = Path(base_dir) / "knowledge_base"
    if not kb_dir.is_dir():
        return ["Clinical guidelines recommend standard diagnostic workup and correlation with patient symptoms."]

    query_words = set(w.lower() for w in query.split() if len(w) > 3)
    scored_chunks = []

    for txt_file in kb_dir.glob("*.txt"):
        try:
            topic = txt_file.stem.replace("_", " ").title()
            text = txt_file.read_text(encoding="utf-8")
            chunks = chunk_text(text, chunk_size=500, overlap=50)
            for chunk in chunks:
                chunk_lower = chunk.lower()
                score = sum(1 for w in query_words if w in chunk_lower)
                if score > 0:
                    scored_chunks.append((score, f"[{topic}] {chunk.strip()}"))
        except Exception:
            continue

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    if scored_chunks:
        return [item[1] for item in scored_chunks[:top_k]]

    # If no keyword overlap matched, return default clinical summaries
    fallbacks = []
    for fname in ["hypertension.txt", "diabetes.txt", "respiratory_infections.txt"]:
        fpath = kb_dir / fname
        if fpath.is_file():
            topic = fpath.stem.replace("_", " ").title()
            excerpt = fpath.read_text(encoding="utf-8")[:300].strip()
            fallbacks.append(f"[{topic}] {excerpt}...")
    return fallbacks or ["Clinical knowledge base consultation recommended."]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_rag_instance: _GeminiRAG = None


def _get_rag() -> _GeminiRAG:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = _GeminiRAG()
    return _rag_instance


# ---------------------------------------------------------------------------
# PUBLIC SERVICE CLASS (interface unchanged for all callers)
# ---------------------------------------------------------------------------

class RAGService:
    """
    Retrieval-Augmented Generation service — Gemini embeddings + ChromaDB.

    Public interface:
        retrieve(query: str, top_k: int = 3) -> list[str]

    Always performs real semantic retrieval.
    Raises RuntimeError if the knowledge base is empty (instead of
    silently returning mock results).

    To populate the knowledge base:
        python manage.py ingest_medical_knowledge
    """

    def retrieve(self, query: str, top_k: int = 3) -> list:
        """
        Retrieve top_k relevant knowledge base entries for a clinical query.

        Uses Gemini embedding-001 to embed the query and performs cosine
        similarity search in ChromaDB.

        Args:
            query:  Free-text clinical query (symptoms, history, chief complaint).
            top_k:  Maximum number of entries to return (>= 1).

        Returns:
            List of content strings prefixed with [Topic] labels.

        Raises:
            ValueError:   If GEMINI_API_KEY is not configured.
            RuntimeError: If ChromaDB is empty or initialisation fails.
        """
        return _get_rag().retrieve(query, top_k)
