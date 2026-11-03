import json
import os
import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")


class ApiError(Exception):
    def __init__(self, status: int, detail):
        self.status, self.detail = status, detail
        super().__init__(f"{status}: {detail}")


def _check(r: requests.Response) -> requests.Response:
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        raise ApiError(r.status_code, detail if isinstance(detail, str) else str(detail))
    return r


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register(email: str, password: str) -> dict:
    return _check(requests.post(f"{API_URL}/auth/register",
                                json={"email": email, "password": password}, timeout=10)).json()


def login(email: str, password: str) -> str:
    r = _check(requests.post(f"{API_URL}/auth/login",
                             data={"username": email, "password": password}, timeout=10))
    return r.json()["access_token"]


def me(token: str) -> dict:
    return _check(requests.get(f"{API_URL}/auth/me", headers=_auth(token), timeout=10)).json()


def create_incident(token: str, text: str, service: str | None = None) -> dict:
    body = {"text": text, **({"service": service} if service else {})}
    return _check(requests.post(f"{API_URL}/incidents", json=body, headers=_auth(token), timeout=10)).json()


def add_service(token, name, repo, gh_token, allow_remediation, auto_merge,
                log_label=None, prom_job=None) -> dict:
    body = {"name": name, "github_repo": repo, "github_token": gh_token,
            "allow_remediation": allow_remediation, "auto_merge": auto_merge}
    if log_label:
        body["loki_labels"] = {"service": log_label}
    if prom_job:
        body["prom_job"] = prom_job
    return _check(requests.post(f"{API_URL}/services", json=body, headers=_auth(token), timeout=30)).json()

def list_services(token) -> list[dict]:
    return _check(requests.get(f"{API_URL}/services", headers=_auth(token), timeout=10)).json()


def delete_service(token, service_id) -> dict:
    _check(requests.delete(f"{API_URL}/services/{service_id}", headers=_auth(token), timeout=10))
    return {"ok": True}


def list_remediations(token, incident_id) -> list[dict]:
    return _check(requests.get(f"{API_URL}/incidents/{incident_id}/remediations",
                               headers=_auth(token), timeout=10)).json()


def list_incidents(token: str) -> list[dict]:
    return _check(requests.get(f"{API_URL}/incidents", headers=_auth(token), timeout=10)).json()


def get_incident(token: str, incident_id: int) -> dict:
    return _check(requests.get(f"{API_URL}/incidents/{incident_id}",
                               headers=_auth(token), timeout=10)).json()


def decide(token: str, incident_id: int, approve: bool) -> dict:
    return _check(requests.post(f"{API_URL}/incidents/{incident_id}/decision",
                                params={"approve": str(approve).lower()},
                                headers=_auth(token), timeout=120)).json()


def stream_incident(token: str, incident_id: int):
    """Yield (event_name, data_dict) for each Server-Sent Event from the investigation."""
    with requests.get(f"{API_URL}/incidents/{incident_id}/stream", headers=_auth(token),
                      stream=True, timeout=(5, 600)) as r:
        _check(r)
        r.encoding = "utf-8"
        event = None
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                yield event, json.loads(line[5:].strip())