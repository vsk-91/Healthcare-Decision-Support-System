# Healthcare Decision Support System

An AI-assisted **Clinical Decision Support System (CDSS)** built with Django, Google Gemini, ChromaDB, and scikit-learn.

The system combines supervised machine learning, Retrieval-Augmented Generation (RAG), and an LLM-based clinical explanation layer to assist physicians in reviewing patient cases.

> **Important:** This application is a clinical decision-support tool and is **not a replacement for a qualified healthcare professional**. AI-generated predictions and explanations are intended to support—not replace—clinical judgment. The attending physician is responsible for reviewing all available information and making the final clinical decision.

---

## Features

* Role-based access control:

  * Admin
  * Doctor
  * Staff
  * Patient
* Patient health-case submission
* Doctor case review and test requests
* Staff medical-test processing
* Medical report upload and verification
* AI-assisted clinical analysis
* Supervised ML prediction using scikit-learn
* Gemini-powered medical knowledge embeddings
* ChromaDB semantic search
* Gemini LLM clinical explanation
* Physician override and final clinical decision
* Audit logging
* Dataset management
* Automated test suite
* Bootstrap-based responsive interface

---

## Clinical Workflow

```text
Patient
   │
   ▼
Submit Health Application
   │
   ▼
Doctor Reviews Case
   │
   ▼
Medical Tests Requested
   │
   ▼
Staff Processes Tests
   │
   ▼
Medical Report Uploaded
   │
   ▼
Doctor Verifies Report
   │
   ▼
AI-Assisted Analysis
   │
   ├── ML Prediction
   │
   ├── Gemini Embeddings
   │
   ├── ChromaDB Retrieval
   │
   └── Gemini LLM Explanation
   │
   ▼
Doctor Reviews AI Output
   │
   ▼
Final Clinical Decision
   │
   ▼
Patient Views Result
```

---

## AI Architecture

The AI pipeline consists of three major components:

```text
Patient Clinical Data
        │
        ▼
ML Prediction
(Logistic Regression)
        │
        ▼
Gemini Embeddings
        │
        ▼
ChromaDB Semantic Search
        │
        ▼
Top Relevant Medical Knowledge
        │
        ▼
Gemini LLM
        │
        ▼
Structured Clinical Explanation
        │
        ▼
Physician Review
        │
        ▼
Final Clinical Decision
```

### 1. Machine Learning

The application uses a locally trained scikit-learn classifier.

Supported models include:

* Logistic Regression
* Random Forest
* Decision Tree

The training dataset is located at:

```text
ai_engine/ml_data/clinical_symptoms_dataset.csv
```

The trained model can be generated using the provided Django management command.

> Model performance depends on the dataset, preprocessing, feature representation, and evaluation methodology. Reported development metrics should not be interpreted as clinical validation.

---

### 2. Retrieval-Augmented Generation

Medical knowledge documents are embedded using Google's Gemini embedding model and stored in ChromaDB.

The RAG layer retrieves relevant medical knowledge before the LLM generates its explanation.

Knowledge-base topics include:

* Hypertension
* Type 2 Diabetes
* Respiratory Infections
* Anemia
* GERD
* Anxiety
* Musculoskeletal Pain
* Headache and Migraine
* Cardiac Risk
* Preventive Medicine

Knowledge files are stored in:

```text
knowledge_base/
```

---

### 3. Gemini LLM

Gemini generates a structured clinical explanation based on:

* Patient-provided clinical information
* ML prediction
* Confidence information
* Retrieved medical knowledge
* Relevant clinical context

The generated report contains:

1. **Primary Prediction**
2. **Confidence Interpretation**
3. **Supporting Findings**
4. **Relevant Medical Context**
5. **Uncertainties and Limitations**
6. **Recommended Next Steps**

The output is intended for physician review and does not constitute an autonomous diagnosis.

---

## Technology Stack

| Layer            | Technology                                 |
| ---------------- | ------------------------------------------ |
| Backend          | Django 5.2                                 |
| API              | Django REST Framework                      |
| Database         | SQLite / PostgreSQL                        |
| Frontend         | Bootstrap 5.3                              |
| Icons            | Font Awesome                               |
| Charts           | Chart.js                                   |
| LLM              | Google Gemini                              |
| Embeddings       | Gemini Embeddings                          |
| Vector Database  | ChromaDB                                   |
| Machine Learning | scikit-learn                               |
| Authentication   | Django session authentication              |
| Authorization    | Role-based access control                  |
| Security         | CSRF protection, environment-based secrets |

---

## Project Structure

```text
healthcare_dss/
│
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
│
├── config/
│   └── Django project configuration
│
├── knowledge_base/
│   └── Medical knowledge documents
│
├── accounts/
│   └── Authentication and user roles
│
├── ai_engine/
│   ├── ml_data/
│   ├── ml_models/
│   ├── services/
│   │   ├── rag_service.py
│   │   ├── llm_service.py
│   │   ├── multimodal_service.py
│   │   ├── ml_predictor.py
│   │   └── mock_data.py
│   └── management/
│       └── commands/
│           ├── ingest_medical_knowledge.py
│           └── train_ml_model.py
│
├── administration/
├── audit/
├── cases/
├── datasets/
├── doctors/
├── patients/
├── reports/
├── staff/
│
├── templates/
├── static/
└── media/
```

---

## Requirements

* Python 3.10+
* pip
* Git
* Google Gemini API key

---

## Installation

### 1. Clone the repository

```bash
git clone <https://github.com/vsk-91/Healthcare-Decision-Support-System>
cd healthcare_dss
```

### 2. Create a virtual environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Configuration

Create a local `.env` file from `.env.example`.

#### Windows

```bash
copy .env.example .env
```

#### Linux/macOS

```bash
cp .env.example .env
```

Configure the required variables:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
GEMINI_API_KEY=your-gemini-api-key
EMBEDDING_MODEL=gemini-embedding-001
LLM_MODEL=gemini-2.5-flash
CHROMA_DB_PATH=./chroma_db
```

Generate a Django secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> Never commit your `.env` file or API keys to GitHub.

---

## Database Setup

Apply Django migrations:

```bash
python manage.py migrate
```

---

## Initialize the Knowledge Base

Before using AI/RAG functionality, ingest the medical knowledge documents:

```bash
python manage.py ingest_medical_knowledge
```

To re-embed all documents:

```bash
python manage.py ingest_medical_knowledge --force
```

You can also provide a custom knowledge-base directory:

```bash
python manage.py ingest_medical_knowledge --kb-dir /path/to/docs
```

---

## Train the ML Model

To train or retrain the machine-learning classifier:

```bash
python manage.py train_ml_model
```

The command evaluates the configured models and stores the selected model and training information.

---

## Run the Development Server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

---

## Management Commands

### Ingest medical knowledge

```bash
python manage.py ingest_medical_knowledge
```

### Force re-ingestion

```bash
python manage.py ingest_medical_knowledge --force
```

### Use a custom knowledge directory

```bash
python manage.py ingest_medical_knowledge --kb-dir /path/to/docs
```

### Train ML model

```bash
python manage.py train_ml_model
```

---

## Testing

The project includes automated tests covering authentication, workflows, AI services, RAG retrieval, ML prediction, and error handling.

Run the complete test suite:

```bash
python manage.py test accounts.tests ai_engine.tests --verbosity=2
```

Run AI-engine tests:

```bash
python manage.py test ai_engine --verbosity=2
```

Run application workflow tests:

```bash
python manage.py test accounts.tests --verbosity=2
```

External Gemini API calls should be mocked during testing so the test suite does not depend on live API access.

---

## Error Handling

The application is designed to surface configuration and AI-service failures instead of silently producing fabricated results.

| Situation                             | Behaviour                              |
| ------------------------------------- | -------------------------------------- |
| Gemini API key missing                | Configuration error                    |
| ChromaDB collection unavailable/empty | Clear initialization error             |
| Gemini API failure                    | Runtime error with failure information |
| Invalid API key                       | Gemini authentication/API error        |
| ML model unavailable                  | Configured fallback behaviour          |
| Knowledge-base directory missing      | Management command error               |

---

## Security

The project includes:

* Django CSRF protection
* Session-based authentication
* Role-based authorization
* Environment-based API key configuration
* `.env` exclusion from version control
* Audit logging
* Restricted access to role-specific dashboards

### Before Production

At minimum:

```env
DEBUG=False
```

Additional production requirements include:

* Use PostgreSQL instead of SQLite
* Configure secure `ALLOWED_HOSTS`
* Use HTTPS
* Enable secure cookies
* Configure appropriate CORS/CSRF settings
* Rotate exposed API keys
* Configure secure file-upload validation
* Review access permissions
* Back up the database securely
* Protect uploaded medical reports
* Review audit-log retention
* Perform a security assessment
* Conduct appropriate privacy/compliance review before handling real patient data

---

## Clinical Safety Notice

This project is intended for **research, educational, and clinical decision-support purposes**.

The AI system may produce incorrect, incomplete, outdated, or misleading information. ML confidence scores should not be interpreted as probabilities of a patient's actual disease without appropriate validation.

The system does not independently establish a diagnosis or prescribe treatment.

A qualified healthcare professional must independently review patient information, medical reports, AI output, and relevant clinical evidence before making a clinical decision.
