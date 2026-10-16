import redis
from app.config import settings

r = redis.from_url(settings.REDIS_URL, decode_responses=True)

def rate_limit(user_id: int, limit: int = 10, window: int = 3600) -> bool:
    key = f"rl:{user_id}"
    n = r.incr(key)
    if n == 1:
        r.expire(key, window)
    return n <= limit