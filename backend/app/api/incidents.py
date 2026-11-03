import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.api.auth import current_user, require_role
from app.cache import rate_limit
from app.config import settings
from app.crypto import CryptoError
from app.db import queries
from app.services import PLATFORM_NAME, UnknownService, resolve_service
from app.tools.write_tools import REAL_STATUSES

router = APIRouter(prefix="/incidents", tags=["incidents"])


class IncidentIn(BaseModel):
    text: str = Field(min_length=5, max_length=2000)
    service: str | None = Field(default=None, max_length=60)


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def get_owned_incident(incident_id: int, user: dict) -> dict:
    inc = queries.get_incident(incident_id)
    if not inc or (inc["user_id"] != user["id"] and user["role"] != "admin"):
        raise HTTPException(404, "Incident not found")
    return inc


def pick_service(user_id: int, requested: str | None) -> str:
    if requested and requested.strip():
        return requested.strip().lower()
    mine = queries.list_services(user_id)
    if len(mine) == 1:
        return mine[0]["name"]
    if len(mine) > 1:
        raise HTTPException(400, "You have several services connected: say which one the incident is about")
    if settings.ALLOW_PLATFORM_SERVICES:
        return PLATFORM_NAME
    raise HTTPException(400, "Connect a GitHub repository first (POST /services)")


@router.post("", status_code=201)
def start(body: IncidentIn, user: dict = Depends(current_user)):
    if not rate_limit(user["id"]):
        raise HTTPException(429, "Too many investigations, try again later")
    name = pick_service(user["id"], body.service)
    try:
        resolve_service(user["id"], name)
    except UnknownService as e:
        raise HTTPException(400, str(e))
    except CryptoError:
        raise HTTPException(500, "Stored credentials for this service cannot be read. Reconnect the service.")
    return {"id": queries.create_incident(user["id"], body.text, name)}


@router.get("")
def list_all(user: dict = Depends(current_user)):
    return queries.list_incidents(user["id"])


@router.get("/{incident_id}")
def read_one(incident_id: int, user: dict = Depends(current_user)):
    return get_owned_incident(incident_id, user)


@router.get("/{incident_id}/remediations")
def remediations(incident_id: int, user: dict = Depends(current_user)):
    get_owned_incident(incident_id, user)
    return queries.list_remediations(incident_id)


@router.get("/{incident_id}/stream")
def stream(incident_id: int, request: Request, user: dict = Depends(current_user)):
    inc = get_owned_incident(incident_id, user)
    if inc["status"] != "running":
        raise HTTPException(409, f"Incident is {inc['status']}, not running")
    graph = request.app.state.graph
    owner = inc["user_id"]                        # tools are scoped to the OWNER of the incident
    state_in = {"incident": inc["text"], "evidence": [], "user_id": owner, "incident_id": incident_id,
                "service": inc.get("service_name") or PLATFORM_NAME}
    cfg = {"configurable": {"thread_id": f"inc-{incident_id}", "user_id": owner}}

    def gen():
        try:
            for update in graph.stream(state_in, cfg, stream_mode="updates"):
                for node in update:
                    if node != "__interrupt__":
                        yield sse("agent_done", {"node": node})
            state = graph.get_state(cfg)
            awaiting = bool(state.next)
            values = state.values
            queries.update_incident(incident_id, "awaiting_approval" if awaiting else "done",
                                    values.get("root_cause", ""), values.get("plan", ""))
            if awaiting:
                yield sse("approval_required", {"plan": values.get("plan", "")})
            yield sse("end", {"status": "awaiting_approval" if awaiting else "done"})
        except Exception as e:
            queries.set_status(incident_id, "failed")
            yield sse("error", {"message": str(e)})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/{incident_id}/decision")
def decide(incident_id: int, approve: bool, request: Request, user: dict = Depends(current_user)):
    inc = queries.get_incident(incident_id)
    if not inc:
        raise HTTPException(404, "Incident not found")
    if not (inc["user_id"] == user["id"] or user["role"] in ("sre", "admin")):
        raise HTTPException(403, "Not allowed")        # owner of the repo, or an sre/admin
    if inc["status"] != "awaiting_approval":
        raise HTTPException(409, "Incident is not waiting for approval")
    cfg = {"configurable": {"thread_id": f"inc-{incident_id}", "user_id": inc["user_id"]}}
    out = request.app.state.graph.invoke(Command(resume={"approve": approve}), cfg)

    rem = out.get("remediation") or {}
    queries.record_decision(incident_id, user["id"], approve)
    if rem.get("status") in REAL_STATUSES:
        queries.create_remediation(incident_id, user["id"], "rollback", rem.get("target_sha", ""), rem["status"],
                                   rem.get("pr_url", ""), rem.get("detail") or rem.get("message", ""))
        target = rem["pr_url"].split("github.com/")[-1] if rem.get("pr_url") else f"incident-{incident_id}"
        queries.add_audit(user["id"], f"rollback_{rem['status']}", target)
    return {"result": out.get("result", ""), "remediation": rem}


@router.get("/audit/logs")
def audit(user: dict = Depends(require_role("admin"))):
    return queries.list_audit_logs()