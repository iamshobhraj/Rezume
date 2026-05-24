"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings.

    Reads from a .env file located in the project root (one level above backend/).
    """

    google_api_key: str = ""
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    database_url: str = "sqlite:///./data/airesume.db"
    github_token: str = ""


    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
