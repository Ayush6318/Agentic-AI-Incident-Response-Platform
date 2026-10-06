from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings

def get_llm():
  return ChatGoogleGenerativeAI(
    model = settings.MODEL_NAME,temperature=0,google_api_key =  settings.GOOGLE_API_KEY)