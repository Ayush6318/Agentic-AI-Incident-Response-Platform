from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import current_user
from app.rag import runbooks

router = APIRouter(prefix="/runbooks", tags=["runbooks"])


class RunbookIn(BaseModel):
    name: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9 _.-]+$")
    text: str = Field(min_length=20, max_length=20_000)


@router.post("", status_code=201)
def upload(body: RunbookIn, user: dict = Depends(current_user)):
    return {"name": body.name, "chunks": runbooks.ingest_text(user["id"], body.name, body.text)}


@router.get("")
def mine(user: dict = Depends(current_user)):
    return runbooks.list_names(user["id"])


@router.delete("/{name}", status_code=204)
def remove(name: str, user: dict = Depends(current_user)):
    if not runbooks.delete(user["id"], name):
        raise HTTPException(404, "Runbook not found")