from cryptography.fernet import Fernet, InvalidToken
from app.config import settings


class CryptoError(Exception):
    pass


def _fernet() -> Fernet:
    if not settings.ENCRYPTION_KEY:
        raise CryptoError("ENCRYPTION_KEY is not set")
    try:
        return Fernet(settings.ENCRYPTION_KEY.encode())
    except ValueError:
        raise CryptoError("ENCRYPTION_KEY is not a valid Fernet key")


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        raise CryptoError("Stored token cannot be decrypted (was ENCRYPTION_KEY changed?)")