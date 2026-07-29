import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")


@dataclass(frozen=True)
class Settings:
    database_path: str = os.getenv("DATABASE_PATH", "./data/deepstudy.db")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "").rstrip("/")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")

    def ensure_directories(self) -> None:
        Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
