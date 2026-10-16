from app.tests.conftest import make_user

def test_duplicate_register(client):
    body = {"email": "a@example.com", "password": "password123"}
    assert client.post("/auth/register", json=body).status_code == 201
    assert client.post("/auth/register", json=body).status_code == 400

def test_sql_injection_login_fails(client):
    r = client.post("/auth/login", data={"username": "' OR 1=1 --", "password": "x"})
    assert r.status_code == 401

def test_full_flow_with_approval(client):
    h = make_user(client, "sre@example.com", role="sre")
    inc_id = client.post("/incidents", json={"text": "payment-service 500"}, headers=h).json()["id"]
    r = client.get(f"/incidents/{inc_id}/stream", headers=h)
    assert "approval_required" in r.text
    assert client.get(f"/incidents/{inc_id}", headers=h).json()["status"] == "awaiting_approval"
    r = client.post(f"/incidents/{inc_id}/decision?approve=true", headers=h)
    assert r.status_code == 200
    assert client.get(f"/incidents/{inc_id}", headers=h).json()["status"] == "done"

def test_viewer_cannot_approve(client):
    sre = make_user(client, "sre@example.com", role="sre")
    viewer = make_user(client, "v@example.com")
    inc_id = client.post("/incidents", json={"text": "payment-service 500"}, headers=sre).json()["id"]
    client.get(f"/incidents/{inc_id}/stream", headers=sre)
    assert client.post(f"/incidents/{inc_id}/decision?approve=true", headers=viewer).status_code == 403

def test_cannot_see_other_users_incident(client):
    a = make_user(client, "a@example.com")
    b = make_user(client, "b@example.com")
    inc_id = client.post("/incidents", json={"text": "redis memory high"}, headers=a).json()["id"]
    assert client.get(f"/incidents/{inc_id}", headers=b).status_code == 404

def test_cannot_approve_twice(client):
    h = make_user(client, "sre@example.com", role="sre")
    inc_id = client.post("/incidents", json={"text": "payment-service 500"}, headers=h).json()["id"]
    client.get(f"/incidents/{inc_id}/stream", headers=h)
    client.post(f"/incidents/{inc_id}/decision?approve=true", headers=h)
    assert client.post(f"/incidents/{inc_id}/decision?approve=true", headers=h).status_code == 409
    

def test_invalid_token_rejected(client):
    r = client.get("/incidents", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401

def test_no_token_rejected(client):
    assert client.get("/incidents").status_code == 401