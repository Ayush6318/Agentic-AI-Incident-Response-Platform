import re

from fastapi import APIRouter, Depends, HTTPException
from psycopg import errors
from pydantic import BaseModel, Field

from app.api.auth import current_user
from app.config import settings
from app.crypto import CryptoError, encrypt
from app.db import queries
from app.providers.base import ProviderError
from app.providers.github import GitHubCodeProvider
from app.services import PLATFORM_NAME, from_row

router = APIRouter(prefix="/services", tags=["services"])

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,59}$")
LABEL_RE = re.compile(r"^[A-Za-z0-9_.:/-]{1,100}$")


class ServiceIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    github_repo: str = Field(min_length=3, max_length=200)
    github_token: str = Field(min_length=20, max_length=400)
    allow_remediation: bool = False
    auto_merge: bool = False
    loki_labels: dict[str, str] | None = None
    prom_job: str | None = Field(default=None, max_length=100)


def _public(row: dict) -> dict:
    out = {k: row[k] for k in ("id", "name", "github_repo", "default_branch", "loki_labels", "prom_job", "created")}
    out["remediation_enabled"] = bool(row["can_write"])
    out["auto_merge"] = bool(row["auto_merge"]) and bool(row["can_write"])
    return out


@router.post("", status_code=201)
def connect(body: ServiceIn, user: dict = Depends(current_user)):
    name = body.name.strip().lower()
    if not NAME_RE.fullmatch(name):
        raise HTTPException(422, "name: lowercase letters, digits, '-' or '_', 2 to 60 characters")
    if name == PLATFORM_NAME and settings.ALLOW_PLATFORM_SERVICES:
        raise HTTPException(409, f"'{name}' is reserved for the platform demo service")
    labels = body.loki_labels or {"service": name}
    prom_job = body.prom_job or name
    if not all(LABEL_RE.fullmatch(k) and LABEL_RE.fullmatch(v) for k, v in labels.items()) or not LABEL_RE.fullmatch(prom_job):
        raise HTTPException(422, "loki_labels and prom_job may only contain letters, digits and _ . : / -")
    if queries.count_services(user["id"]) >= settings.MAX_SERVICES_PER_USER:
        raise HTTPException(409, f"At most {settings.MAX_SERVICES_PER_USER} services per user")
    try:
        info = GitHubCodeProvider().verify_access(body.github_repo.strip(), body.github_token.strip())
        token_enc = encrypt(body.github_token.strip())
    except ProviderError as e:
        raise HTTPException(400, f"GitHub check failed: {e}")
    except CryptoError as e:
        raise HTTPException(500, str(e))
    try:
        row = queries.create_service(user["id"], name, body.github_repo.strip(), token_enc, body.allow_remediation,
                                     body.auto_merge and body.allow_remediation, info["default_branch"], labels, prom_job)
    except errors.UniqueViolation:
        raise HTTPException(409, "You already have a service with that name")
    return _public(row)


@router.get("")
def list_mine(user: dict = Depends(current_user)):
    return [_public(r) for r in queries.list_services(user["id"])]


@router.post("/{service_id}/verify")
def verify(service_id: int, user: dict = Depends(current_user)):
    row = queries.get_service_row_by_id(user["id"], service_id)
    if not row:
        raise HTTPException(404, "Service not found")
    try:
        cfg = from_row(row)
        info = GitHubCodeProvider().verify_access(cfg.repo, cfg.token)
    except (ProviderError, CryptoError) as e:
        raise HTTPException(400, f"GitHub check failed: {e}")
    return {"ok": True, "default_branch": info["default_branch"]}


@router.delete("/{service_id}", status_code=204)
def disconnect(service_id: int, user: dict = Depends(current_user)):
    if not queries.delete_service(user["id"], service_id):
        raise HTTPException(404, "Service not found")