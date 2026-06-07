import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    PLATFORM_NAME = os.environ.get("PLATFORM_NAME", "TRAZIA RFID")
    PLATFORM_TAGLINE = os.environ.get("PLATFORM_TAGLINE", "Inventario · Custodia · Trazabilidad Inteligente")
    APP_NAME = os.environ.get("APP_NAME", "TRAZIA RFID")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-inventario-rfid-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'inventario.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = str(BASE_DIR / "static" / "uploads")
    ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx"}

    GPT4ALL_ENABLED = os.environ.get("GPT4ALL_ENABLED", "true").lower() == "true"
    GPT4ALL_MODE = os.environ.get("GPT4ALL_MODE", "server")
    GPT4ALL_SERVER_URL = os.environ.get("GPT4ALL_SERVER_URL", "http://127.0.0.1:4891/v1")
    GPT4ALL_MODEL = os.environ.get("GPT4ALL_MODEL", "Phi-3 Mini Instruct")
    GPT4ALL_SDK_MODEL = os.environ.get("GPT4ALL_SDK_MODEL", "Phi-3-mini-4k-instruct.Q4_0.gguf")
    MAINTENANCE_ALERT_DAYS = int(os.environ.get("MAINTENANCE_ALERT_DAYS", 30))
    WARRANTY_ALERT_DAYS = int(os.environ.get("WARRANTY_ALERT_DAYS", 45))
    DATA_ENCRYPTION_KEY = os.environ.get("DATA_ENCRYPTION_KEY", SECRET_KEY)
    RESET_TOKEN_MAX_AGE = int(os.environ.get("RESET_TOKEN_MAX_AGE", 3600))
    MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "false").lower() == "true"
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME or "no-reply@inventario-rfid.local")
    MAIL_SUPPRESS_SEND = os.environ.get("MAIL_SUPPRESS_SEND", "false").lower() == "true"
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT", "trazia-rfid-email-salt")
    EMAIL_TOKEN_EXPIRATION_HOURS = int(os.environ.get("EMAIL_TOKEN_EXPIRATION_HOURS", 24))
    PASSWORD_RESET_EXPIRATION_HOURS = int(os.environ.get("PASSWORD_RESET_EXPIRATION_HOURS", 2))
    REQUIRE_EMAIL_VERIFICATION = os.environ.get("REQUIRE_EMAIL_VERIFICATION", "false").lower() == "true"
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5000")
    BRAND_LOGO_PATH = os.environ.get("BRAND_LOGO_PATH", "img/brand/logo-horizontal-light.svg")
    BRAND_MARK_PATH = os.environ.get("BRAND_MARK_PATH", "img/brand/logo-icon-light.svg")
    BRAND_EMAIL_LOGO_PATH = os.environ.get("BRAND_EMAIL_LOGO_PATH", "img/brand/logo-horizontal-dark.svg")
    BRAND_FAVICON_PATH = os.environ.get("BRAND_FAVICON_PATH", BRAND_MARK_PATH)
    DEVICE_API_TOKEN = os.environ.get("DEVICE_API_TOKEN", "trazia-device-secret-token")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
