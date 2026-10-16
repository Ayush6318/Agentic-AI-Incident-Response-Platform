import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.api.auth import current_user, require_role
from app.cache import rate_limit
from app.db import queries

router = APIRouter(prefix="/incidents", tags=["incidents"])

class IncidentIn(BaseModel):
    text: str = Field(min_length=5, max_length=2000)

def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

def get_owned_incident(incident_id: int, user: dict) -> dict:
    inc = queries.get_incident(incident_id)
    if not inc or (inc["user_id"] != user["id"] and user["role"] != "admin"):
        raise HTTPException(404, "Incident not found")      # same answer for "missing" and "not yours"
    return inc

@router.post("", status_code=201)
def start(body: IncidentIn, user: dict = Depends(current_user)):
    if not rate_limit(user["id"]):
        raise HTTPException(429, "Too many investigations, try again later")
    return {"id": queries.create_incident(user["id"], body.text)}

@router.get("")
def list_all(user: dict = Depends(current_user)):
    return queries.list_incidents(user["id"])

@router.get("/{incident_id}")
def read_one(incident_id: int, user: dict = Depends(current_user)):
    return get_owned_incident(incident_id, user)

@router.get("/{incident_id}/stream")
def stream(incident_id: int, request: Request, user: dict = Depends(current_user)):
    inc = get_owned_incident(incident_id, user)
    if inc["status"] != "running":
        raise HTTPException(409, f"Incident is {inc['status']}, not running")
    graph = request.app.state.graph
    cfg = {"configurable": {"thread_id": f"inc-{incident_id}"}}

    def gen():
        try:
            for update in graph.stream({"incident": inc["text"], "evidence": []},
                                       cfg, stream_mode="updates"):
                for node in update:
                    if node != "__interrupt__":
                        yield sse("agent_done", {"node": node})
            state = graph.get_state(cfg)
            awaiting = bool(state.next)                      # paused at the approval node
            values = state.values
            queries.update_incident(incident_id,
                                    "awaiting_approval" if awaiting else "done",
                                    values.get("root_cause", ""), values.get("plan", ""))
            if awaiting:
                yield sse("approval_required", {"plan": values.get("plan", "")})
            yield sse("end", {"status": "awaiting_approval" if awaiting else "done"})
        except Exception as e:
            queries.set_status(incident_id, "failed")
            yield sse("error", {"message": str(e)})

    return StreamingResponse(gen(), media_type="text/event-stream")

@router.post("/{incident_id}/decision")
def decide(incident_id: int, approve: bool, request: Request,
           user: dict = Depends(require_role("sre", "admin"))):
    inc = get_owned_incident(incident_id, user)
    if inc["status"] != "awaiting_approval":
        raise HTTPException(409, "Incident is not waiting for approval")
    cfg = {"configurable": {"thread_id": f"inc-{incident_id}"}}
    out = request.app.state.graph.invoke(Command(resume={"approve": approve}), cfg)
    queries.record_decision(incident_id, user["id"], approve)   # status + audit log, one transaction
    return {"result": out["result"]}

@router.get("/audit/logs")
def audit(user: dict = Depends(require_role("admin"))):
    return queries.list_audit_logs()