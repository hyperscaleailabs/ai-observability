"""Application settings loaded from environment / .env.local."""
import os
from dotenv import load_dotenv

load_dotenv(".env.local")


class Settings:
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    logs_root_dir: str = os.environ.get("LOGS_ROOT_DIR", "logs")
    max_runs_per_prompt: int = int(os.environ.get("MAX_RUNS_PER_PROMPT", "20"))
    default_model: str = os.environ.get("DEFAULT_MODEL", "gpt-4o-mini")
    port: int = int(os.environ.get("PORT", "8000"))


settings = Settings()
