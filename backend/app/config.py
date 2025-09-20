from pathlib import Path
import os

try:
    # Load environment variables from backend/.env
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path, override=True)
except Exception:
    # dotenv is optional in runtime; if not installed, assume env vars are already present
    pass

# Database URL (Neon/PostgreSQL or fallback to SQLite for local dev)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Redis URL for Celery broker/result backend (can be customized via .env)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

