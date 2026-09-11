"""
Django management command: ingest_medical_knowledge

Usage:
    python manage.py ingest_medical_knowledge
    python manage.py ingest_medical_knowledge --kb-dir /path/to/knowledge_base
    python manage.py ingest_medical_knowledge --force   (re-embed all documents)

Description:
    Reads all .txt files from the knowledge_base/ directory, splits them into
    overlapping chunks, generates Gemini embeddings for each chunk, and stores
    them in the ChromaDB persistent vector database.

    Run this command ONCE before using the AI analysis pipeline.
    It is idempotent — re-running without --force skips already-stored chunks.
    Use --force to rebuild the entire vector database (e.g. after switching models).

    Requires GEMINI_API_KEY in .env.
"""

import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = (
        "Ingest medical knowledge documents into ChromaDB using Gemini embeddings. "
        "Requires GEMINI_API_KEY in .env."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--kb-dir",
            type=str,
            default=None,
            help=(
                "Path to the knowledge_base directory "
                "(default: <project_root>/knowledge_base/)"
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Delete and re-embed all documents even if already stored in ChromaDB.",
        )

    def handle(self, *args, **options):
        # ---------------------------------------------------------------
        # 1. Validate GEMINI_API_KEY
        # ---------------------------------------------------------------
        api_key = (
            getattr(settings, "GEMINI_API_KEY", "")
            or os.environ.get("GEMINI_API_KEY", "")
        )
        if not api_key or api_key == "your-gemini-api-key-here":
            raise CommandError(
                "GEMINI_API_KEY is not configured.\n"
                "Add it to your .env file:\n"
                "    GEMINI_API_KEY=<your-key>\n"
                "Get a key at: https://aistudio.google.com/app/apikey\n"
                "Never hard-code the API key in source files."
            )

        # ---------------------------------------------------------------
        # 2. Resolve knowledge_base directory
        # ---------------------------------------------------------------
        kb_dir = options.get("kb_dir")
        if kb_dir:
            kb_path = Path(kb_dir)
        else:
            kb_path = Path(settings.BASE_DIR) / "knowledge_base"

        if not kb_path.is_dir():
            raise CommandError(
                "Knowledge base directory not found: {}\n"
                "Create it and add .txt medical knowledge files.".format(kb_path)
            )

        txt_files = sorted(kb_path.glob("*.txt"))
        if not txt_files:
            raise CommandError(
                "No .txt files found in: {}\n"
                "Add medical knowledge .txt files to the directory.".format(kb_path)
            )

        # ---------------------------------------------------------------
        # 3. Display configuration
        # ---------------------------------------------------------------
        embedding_model = getattr(settings, "EMBEDDING_MODEL", "gemini-embedding-001")
        chroma_path     = getattr(settings, "CHROMA_DB_PATH", "./chroma_db")

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\nHealthcare DSS -- Medical Knowledge Ingestion (Gemini)\n"
            + "=" * 60
        ))
        self.stdout.write("Knowledge base   : {}".format(kb_path))
        self.stdout.write("Files found      : {}".format(len(txt_files)))
        self.stdout.write("Embedding model  : {}".format(embedding_model))
        self.stdout.write("ChromaDB path    : {}".format(chroma_path))
        self.stdout.write("")

        # ---------------------------------------------------------------
        # 4. Import RAG service and optionally wipe + reset
        # ---------------------------------------------------------------
        try:
            from ai_engine.services.rag_service import (
                _get_rag, _get_chroma_db_path, _COLLECTION_NAME, chunk_text
            )
            rag = _get_rag()
        except Exception as exc:
            raise CommandError("Failed to initialise RAG service: {}".format(exc))

        if options.get("force"):
            self.stdout.write(self.style.WARNING(
                "--force: deleting existing ChromaDB collection to re-embed all documents..."
            ))
            try:
                import chromadb
                db_path = _get_chroma_db_path()
                client  = chromadb.PersistentClient(path=db_path)
                try:
                    client.delete_collection(_COLLECTION_NAME)
                    self.stdout.write("Existing collection deleted.")
                except Exception:
                    self.stdout.write("No existing collection found — starting fresh.")

                # Reset singleton so next call re-initialises cleanly
                import ai_engine.services.rag_service as rs
                rs._rag_instance = None
                rag = rs._get_rag()
            except Exception as exc:
                raise CommandError("Failed to reset collection: {}".format(exc))

        # ---------------------------------------------------------------
        # 5. Ingest each file
        # ---------------------------------------------------------------
        total_files   = 0
        total_chunks  = 0
        total_skipped = 0
        errors        = []

        for txt_file in txt_files:
            self.stdout.write("  Processing: {}".format(txt_file.name), ending="")
            try:
                text       = txt_file.read_text(encoding="utf-8")
                doc_id     = txt_file.stem
                num_chunks = len(chunk_text(text))

                added = rag.ingest_document(
                    doc_id=doc_id,
                    text=text,
                    metadata={
                        "source_file": txt_file.name,
                        "topic": doc_id.replace("_", " ").title(),
                    },
                )
                total_files += 1

                if added == 0:
                    total_skipped += 1
                    self.stdout.write(self.style.WARNING(
                        "  [SKIPPED -- already stored ({} chunks)]".format(num_chunks)
                    ))
                else:
                    total_chunks += added
                    self.stdout.write(self.style.SUCCESS(
                        "  [OK -- {} new chunks embedded]".format(added)
                    ))

            except Exception as exc:
                errors.append((txt_file.name, str(exc)))
                self.stdout.write(self.style.ERROR("  [ERROR: {}]".format(exc)))

        # ---------------------------------------------------------------
        # 6. Summary
        # ---------------------------------------------------------------
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("INGESTION SUMMARY"))
        self.stdout.write("=" * 60)
        self.stdout.write("Documents processed  : {}".format(total_files))
        self.stdout.write("New chunks embedded  : {}".format(total_chunks))
        self.stdout.write("Docs skipped         : {} (already in ChromaDB)".format(total_skipped))
        self.stdout.write("Errors               : {}".format(len(errors)))

        try:
            rag._init()
            collection_count = rag._collection.count()
        except Exception:
            collection_count = "unknown"

        self.stdout.write("ChromaDB total       : healthcare_medical_knowledge ({} chunks)".format(
            collection_count
        ))
        self.stdout.write("")

        if errors:
            self.stdout.write(self.style.ERROR("Errors encountered:"))
            for fname, err in errors:
                self.stdout.write("  {} : {}".format(fname, err))
            self.stdout.write("")

        if total_chunks > 0 or total_skipped == total_files:
            self.stdout.write(self.style.SUCCESS(
                "Ingestion complete.\n"
                "The ChromaDB knowledge base is ready for AI analysis.\n"
                "Run 'python manage.py runserver' to start the application."
            ))
        else:
            raise CommandError(
                "No chunks were added. Check errors above.\n"
                "Tip: Use --force to re-embed all documents."
            )
