from pydantic_settings  import BaseSettings

class Settings(BaseSettings):
  GROQ_API_KEY : str
  GOOGLE_API_KEY: str
  MODEL_NAME : str = "gemini-2.5-flash"
  DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/incidents"
  REDIS_URL: str = "redis://localhost:6379/0"
  SECRET_KEY: str = "AyushisBoss"
  CORS_ORIGINS: str = "http://localhost:5173"
  class Config:
    
    env_file = ".env"
    extra = "ignore"
    
settings = Settings()