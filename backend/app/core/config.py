"""
Configuration settings for the Cloud Security Platform backend.
"""
import os

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "cloud-security-platform-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Database Configuration
# Reverting to SQLite for demo purposes since Postgres is not running
DATABASE_URL = "sqlite:///./security_platform.db"

# PostgreSQL connection (Commenting out for now)
# POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
# POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
# POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
# POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
# POSTGRES_DB = os.getenv("POSTGRES_DB", "security_platform")
# DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# CORS Configuration
CORS_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "null",  # For file:// protocol
]

# API Configuration
API_PREFIX = "/api"

# ML Models Path
ML_MODELS_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "models")
