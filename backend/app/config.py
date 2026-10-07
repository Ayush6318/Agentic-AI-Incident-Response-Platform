from pydantic_settings  import BaseSettings

class Settings(BaseSettings):
  GROQ_API_KEY : str
  MODEL_NAME : str = "qwen/qwen3.8-27b"
  class Config:
    
    env_file = ".env"
    extra = "ignore"
    
settings = Settings()