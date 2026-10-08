from pydantic_settings  import BaseSettings

class Settings(BaseSettings):
  GROQ_API_KEY : str
  GOOGLE_API_KEY: str
  MODEL_NAME : str = "gemini-2.5-flash"
  class Config:
    
    env_file = ".env"
    extra = "ignore"
    
settings = Settings()