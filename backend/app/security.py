from datetime import datetime, timedelta, timezone
import bcrypt, jwt
from app.config import settings

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> int:
    """Returns the user id, or raises jwt.InvalidTokenError."""
    return int(jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])["sub"])