import os
os.environ["DATABASE_URL"] = "postgresql://app:app@localhost:5432/incidents_test"
os.environ.setdefault("GOOGLE_API_KEY", "test")          # set before app.config is imported

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import pool

class FakeState:
    def __init__(self, values, nxt): self.values, self.next = values, nxt

class FakeGraph:
    def __init__(self): self.resumed = False
    def stream(self, inp, cfg, stream_mode=None):
        yield {"logs": {}}
        yield {"planner": {}}
    def get_state(self, cfg):
        return FakeState({"root_cause": "pool exhausted", "plan": "ACTION: rollback abc123"},
                         () if self.resumed else ("approval",))
    def invoke(self, cmd, cfg):
        self.resumed = True
        return {"result": "Executed rollback on abc123 (simulated)"}



@pytest.fixture(autouse=True)
def clean_test_db():
    with pool.connection() as conn:
        conn.execute(
            "TRUNCATE users, incidents, audit_logs RESTART IDENTITY CASCADE"
        )

@pytest.fixture(scope="session")
def client():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "app.api.incidents.rate_limit",
        lambda *a, **k: True
    )

    with TestClient(app) as c:
        app.state.graph = FakeGraph()

        yield c

    monkeypatch.undo()

def make_user(client, email, role="viewer"):
    client.post("/auth/register", json={"email": email, "password": "password123"})
    if role != "viewer":
        with pool.connection() as conn:
            conn.execute("UPDATE users SET role = %s WHERE email = %s", (role, email))
    r = client.post("/auth/login", data={"username": email, "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}