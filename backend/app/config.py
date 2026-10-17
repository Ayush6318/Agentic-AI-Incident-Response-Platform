
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

class Settings(BaseSettings):
    GROQ_API_KEY: str
    GOOGLE_API_KEY: str
    MODEL_NAME: str = "gemini-2.5-flash"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/incidents"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str
    CORS_ORIGINS: str = "http://localhost:5173"
    CODE_PROVIDER: str = "fake"
    LOGS_PROVIDER: str = "fake"
    METRICS_PROVIDER: str = "fake"
    GITHUB_TOKEN: str
    GITHUB_REPO: str
    LOKI_URL: str = "http://localhost:3100"
    PROMETHEUS_URL: str = "http://localhost:9090"
    

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
