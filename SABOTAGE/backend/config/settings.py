from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "hackathon-barranquilla-no-se-apaga-solo-demo"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "rest_framework",
    "game",
]

MIDDLEWARE = [
    "game.cors.SimpleCorsMiddleware",  # CORS mínimo para el frontend en :4200
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
}

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "UNAUTHENTICATED_USER": None,
}

# --- Parámetros del juego (ajustables) ---
LOBBY_SIZE = 6
VENTANA_AUDITORIA_MIN = 15
PENALIZACION_AUDITOR = 100
COSTO_RULETA = 50
INCREMENTO_PUJA = 50
# Factores de conversión ESTIMATIVOS (ajustar con datos reales de la factura / UPME)
COP_POR_KWH = 800
KG_CO2_POR_KWH = 0.126
KG_CO2_POR_ARBOL_ANIO = 22
