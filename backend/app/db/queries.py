from app.db.database import pool

#users
def create_user(email: str, password_hash: str, role: str = "viewer") -> int:
    with pool.connection() as conn:
        return conn.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s) RETURNING id",
            (email, password_hash, role),
        ).fetchone()["id"]

def get_user_by_email(email: str) -> dict | None:
    with pool.connection() as conn:
        return conn.execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()

def get_user(user_id: int) -> dict | None:
    with pool.connection() as conn:
        return conn.execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()

# incidents
def create_incident(user_id: int, text: str) -> int:
    with pool.connection() as conn:
        return conn.execute(
            "INSERT INTO incidents (user_id, text) VALUES (%s, %s) RETURNING id",
            (user_id, text),
        ).fetchone()["id"]

def get_incident(incident_id: int) -> dict | None:
    with pool.connection() as conn:
        return conn.execute("SELECT * FROM incidents WHERE id = %s", (incident_id,)).fetchone()

def list_incidents(user_id: int) -> list[dict]:
    with pool.connection() as conn:
        return conn.execute(
            "SELECT id, text, status, created FROM incidents WHERE user_id = %s ORDER BY id DESC",
            (user_id,),
        ).fetchall()

def update_incident(incident_id: int, status: str, root_cause: str = "", plan: str = "") -> None:
    with pool.connection() as conn:
        conn.execute(
            "UPDATE incidents SET status = %s, root_cause = %s, plan = %s WHERE id = %s",
            (status, root_cause, plan, incident_id),
        )

def set_status(incident_id: int, status: str) -> None:
    with pool.connection() as conn:
        conn.execute("UPDATE incidents SET status = %s WHERE id = %s", (status, incident_id))

# audit + decision (one transaction)
def record_decision(incident_id: int, user_id: int, approved: bool) -> None:
    """Update the incident AND write the audit log. Both succeed or neither does."""
    with pool.connection() as conn:
        conn.execute("UPDATE incidents SET status = %s WHERE id = %s",
                     ("done" if approved else "rejected", incident_id))
        conn.execute("INSERT INTO audit_logs (user_id, action, target) VALUES (%s, %s, %s)",
                     (user_id, "approve" if approved else "reject", f"incident-{incident_id}"))

def list_audit_logs(limit: int = 50) -> list[dict]:
    with pool.connection() as conn:
        return conn.execute(
            "SELECT a.id, u.email, a.action, a.target, a.time "
            "FROM audit_logs a JOIN users u ON u.id = a.user_id ORDER BY a.id DESC LIMIT %s",
            (limit,),
        ).fetchall()