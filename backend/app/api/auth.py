import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from psycopg import errors
from pydantic import BaseModel, Field
from app.db import queries
from app.security import hash_password, verify_password, create_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")

class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)

@router.post("/register", status_code=201)
def register(body: Credentials):
    try:
        user_id = queries.create_user(body.email.lower(), hash_password(body.password))
    except errors.UniqueViolation:                       # the database enforces uniqueness
        raise HTTPException(400, "Email already registered")
    return {"id": user_id}

@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = queries.get_user_by_email(form.username.lower())
    if not user or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(401, "Bad credentials")
    return {"access_token": create_token(user["id"]), "token_type": "bearer"}

def current_user(token: str = Depends(oauth2)) -> dict:
    try:
        user = queries.get_user(decode_token(token))
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(401, "Invalid token")
    if not user:
        raise HTTPException(401, "User no longer exists")
    return user

def require_role(*roles: str):
    def checker(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(403, "Not allowed")
        return user
    return checker