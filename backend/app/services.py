from __future__ import annotations
from dataclasses import dataclass, field
from app.config import settings

PLATFORM_NAME = "payment-service"


class UnknownService(Exception):
    pass


@dataclass(frozen=True)
class ServiceConfig:
    name: str
    repo: str = ""
    token: str = ""              
    write_token: str = ""
    can_write: bool = False
    auto_merge: bool = False
    default_branch: str = "main"
    loki_labels: dict = field(default_factory=dict)
    prom_job: str = ""
    id: int | None = None
    owner_id: int | None = None


def platform_service() -> ServiceConfig:
    return ServiceConfig(
        name=PLATFORM_NAME, repo=settings.GITHUB_REPO, token=settings.GITHUB_TOKEN,
        write_token=settings.GITHUB_WRITE_TOKEN, can_write=bool(settings.GITHUB_WRITE_TOKEN),
        auto_merge=settings.REMEDIATION_AUTO_MERGE and bool(settings.GITHUB_WRITE_TOKEN),
        default_branch=settings.GITHUB_DEFAULT_BRANCH,
        loki_labels={"service": PLATFORM_NAME}, prom_job=PLATFORM_NAME)


def from_row(row: dict) -> ServiceConfig:
    from app.crypto import decrypt
    token = decrypt(row["github_token_enc"])
    can_write = bool(row["can_write"])
    return ServiceConfig(
        name=row["name"], repo=row["github_repo"], token=token, write_token=token if can_write else "",
        can_write=can_write, auto_merge=bool(row["auto_merge"]) and can_write,
        default_branch=row["default_branch"], loki_labels=row["loki_labels"] or {},
        prom_job=row["prom_job"] or "", id=row["id"], owner_id=row["user_id"])


def resolve_service(user_id: int | None, name: str | None) -> ServiceConfig:
    key = (name or PLATFORM_NAME).strip().lower()
    known = []
    if user_id is not None:
        from app.db import queries
        row = queries.get_service_row(user_id, key)
        if row:
            return from_row(row)
        known = [s["name"] for s in queries.list_services(user_id)]
    if settings.ALLOW_PLATFORM_SERVICES and key == PLATFORM_NAME:
        return platform_service()
    if settings.ALLOW_PLATFORM_SERVICES:
        known.append(PLATFORM_NAME)
    raise UnknownService(f"Unknown service '{name}'. Known services: {', '.join(known) or 'none'}")


def as_config(service) -> ServiceConfig:
    """Providers accept a ServiceConfig or a plain name (platform service only)."""
    return service if isinstance(service, ServiceConfig) else resolve_service(None, service)