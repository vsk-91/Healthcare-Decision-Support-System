#!/usr/bin/env bash
# Build script for Render deployment
set -o errexit

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running database migrations..."
python manage.py migrate

# If GEMINI_API_KEY is configured in Render environment, ingest knowledge base into ChromaDB
if [ -n "$GEMINI_API_KEY" ] && [ "$GEMINI_API_KEY" != "your-gemini-api-key" ]; then
    echo "==> Ingesting medical knowledge into ChromaDB..."
    python manage.py ingest_medical_knowledge || echo "Warning: Knowledge ingestion encountered an issue. Skipping."
else
    echo "==> GEMINI_API_KEY not set yet. Remember to set it in Render Dashboard and run ingest_medical_knowledge."
fi

echo "==> Build completed successfully!"
