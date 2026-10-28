import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'base_de_donnees.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "cours")
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 Mo maximum par requête

    # Sécurité des cookies de session.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    # Extensions autorisées pour les supports pédagogiques.
    ALLOWED_EXTENSIONS = {
        "pdf",
        "mp4",
        "webm",
        "ogg",
        "doc",
        "docx",
        "ppt",
        "pptx",
        "xls",
        "xlsx",
    }
