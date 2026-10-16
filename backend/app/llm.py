from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings

# ~4 requests/minute, shared by every agent (must be created once, at module level)
_limiter = InMemoryRateLimiter(requests_per_second=0.07, check_every_n_seconds=0.2, max_bucket_size=1)


def get_llm():
    return ChatGoogleGenerativeAI(
        model=settings.MODEL_NAME,
        temperature=0,
        api_key=settings.GOOGLE_API_KEY,
        rate_limiter=_limiter,
        max_retries=4,
    )
