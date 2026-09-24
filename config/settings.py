import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-dummy-key-for-dev-123')
DEBUG = env('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# Dynamically add Render external hostname if running on Render
RENDER_EXTERNAL_HOSTNAME = env('RENDER_EXTERNAL_HOSTNAME', default='')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'storages',
    'rest_framework',
    'accounts',
    'patients',
    'doctors',
    'staff',
    'cases',
    'reports',
    'ai_engine',
    'datasets',
    'administration',
    'audit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# STATIC & MEDIA STORAGE (Render + Firebase Storage)
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
os.makedirs(MEDIA_ROOT, exist_ok=True)

USE_FIREBASE_STORAGE = env.bool('USE_FIREBASE_STORAGE', default=False)
GS_BUCKET_NAME = env('GS_BUCKET_NAME', default='').strip()
GS_PROJECT_ID = env('GS_PROJECT_ID', default=None)
GS_CREDENTIALS_PATH = env('GS_CREDENTIALS_PATH', default='').strip()

# Verify whether Google Cloud / Firebase credentials file actually exists
has_creds = False
if GS_CREDENTIALS_PATH and os.path.exists(GS_CREDENTIALS_PATH):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GS_CREDENTIALS_PATH
    has_creds = True
elif os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') and os.path.exists(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')):
    has_creds = True

if USE_FIREBASE_STORAGE and GS_BUCKET_NAME and has_creds:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {
                "bucket_name": GS_BUCKET_NAME,
                "project_id": GS_PROJECT_ID,
            }
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/'
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'

# ---------------------------------------------------------------------------
# CORS & CSRF SETTINGS (Firebase Hosting & Cross-Origin support)
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:5000',
    'http://127.0.0.1:8000',
])
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.web\.app$",
    r"^https://.*\.firebaseapp\.com$",
    r"^https://.*\.onrender\.com$",
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    'https://healthcare-decision-support-system.onrender.com',
    'https://*.onrender.com',
    'https://*.web.app',
    'https://*.firebaseapp.com',
]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')

# ---------------------------------------------------------------------------
# AI SETTINGS — Google Gemini + ChromaDB
# ---------------------------------------------------------------------------
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
EMBEDDING_MODEL = env('EMBEDDING_MODEL', default='gemini-embedding-001')
CHROMA_DB_PATH = env('CHROMA_DB_PATH', default='./chroma_db')
LLM_MODEL = env('LLM_MODEL', default='gemini-2.5-flash')
