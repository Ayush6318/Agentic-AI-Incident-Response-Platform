import operator
from typing import Annotated, TypedDict


class IncidentState(TypedDict, total=False):
    incident: str
    evidence: Annotated[list[str], operator.add]
    root_cause: str
    plan: str
    approved: bool
    result: str
    user_id: int
    service: str
    incident_id: int
    remediation: dict