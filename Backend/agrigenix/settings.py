from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parent.parent
PICTURES_DIR = Path.home() / "OneDrive" / "Pictures"
DOWNLOADS_DIR = Path.home() / "Downloads"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "agrigenix-dev-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "agrigenix.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.global_ui",
            ],
        },
    },
]
WSGI_APPLICATION = "agrigenix.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "agrigenix-cache",
        "TIMEOUT": 300,
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
APP_LOGO_PATH = "core/images/agrigenix-logo.svg"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "core.FarmerUser"
LOGIN_URL = "login"
OTP_EXPIRY_MINUTES = 5
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "console")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY", "579b464db66ec23bdd00000193c634ee35f8431554e2724a42352501")
DATA_GOV_API_BASE_URL = os.getenv("DATA_GOV_API_BASE_URL", "https://api.data.gov.in")
UMANG_API_BASE_URL = os.getenv("UMANG_API_BASE_URL", "https://api.umangapp.in")
GODOWN_API_URL = os.getenv("GODOWN_API_URL", "/resource/f5bbd629-8836-41ab-a106-268102d087e8")
ENAM_MARKET_API_URL = os.getenv("ENAM_MARKET_API_URL", "/umang/apisetu/dept/enamapi/ws1/getMandiInfoForMI")
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "agrigenix")
MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "1500"))
GODOWN_MASTER_XLSX = os.getenv("GODOWN_MASTER_XLSX", str(DOWNLOADS_DIR / "tableConvert.com_33ub1d.xlsx"))
GODOWN_ADDRESSES_PDF = os.getenv("GODOWN_ADDRESSES_PDF", str(DOWNLOADS_DIR / "Addresses_Rural_Godowns.pdf"))
CROP_RATES_XLSX = os.getenv("CROP_RATES_XLSX", str(PICTURES_DIR / "crop_rates_kg_corrected.xlsx"))
MARKET_PRICES_CSV = os.getenv("MARKET_PRICES_CSV", str(DOWNLOADS_DIR / "9ef84268-d588-465a-a308-a864a43d0070.csv"))
LIVE_DATA_CACHE_TIMEOUT = int(os.getenv("LIVE_DATA_CACHE_TIMEOUT", "300"))
