
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
    LOKI_URL: str 
    PROMETHEUS_URL: str
    ENCRYPTION_KEY: str = ""
    GITHUB_WRITE_TOKEN: str = ""
    GITHUB_DEFAULT_BRANCH: str = "main"
    REMEDIATION_AUTO_MERGE: bool = False
    ALLOW_PLATFORM_SERVICES: bool = True
    MAX_SERVICES_PER_USER: int = 5
    
    

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
