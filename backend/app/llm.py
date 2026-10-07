from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.config import settings

def get_llm():
  return ChatGroq(
    model = settings.MODEL_NAME,temperature=0,groq_api_key =  settings.GROQ_API_KEY)