from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Настройки для запуска учебного проекта на своем компьютере.
SECRET_KEY = "django-insecure-local-books-project-only"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "[::1]"]

INSTALLED_APPS = [
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "books",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "library.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "library.wsgi.application"
MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Книги хранятся в файлах, база данных для них не нужна.
BOOKS_DIR = BASE_DIR / "data" / "books"
MAX_JSON_SIZE = 1024 * 1024
MAX_BOOKS_PER_FILE = 1000
