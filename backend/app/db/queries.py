from app.db.database import pool
from psycopg.types.json import Jsonb

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

def create_incident(user_id: int, text: str, service_name: str = "") -> int:
    with pool.connection() as conn:
        return conn.execute(
            "INSERT INTO incidents (user_id, text, service_name) VALUES (%s, %s, %s) RETURNING id",
            (user_id, text, service_name)).fetchone()["id"]


SERVICE_PUBLIC = "id, name, github_repo, can_write, auto_merge, default_branch, loki_labels, prom_job, created"


def count_services(user_id: int) -> int:
    with pool.connection() as conn:
        return conn.execute("SELECT count(*) AS n FROM services WHERE user_id = %s", (user_id,)).fetchone()["n"]


def create_service(user_id, name, repo, token_enc, can_write, auto_merge, default_branch, loki_labels, prom_job) -> dict:
    with pool.connection() as conn:
        return conn.execute(
            f"INSERT INTO services (user_id, name, github_repo, github_token_enc, can_write, auto_merge, "
            f"default_branch, loki_labels, prom_job) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING {SERVICE_PUBLIC}",
            (user_id, name, repo, token_enc, can_write, auto_merge, default_branch, Jsonb(loki_labels), prom_job),
        ).fetchone()


def list_services(user_id: int) -> list[dict]:                    # never returns the token
    with pool.connection() as conn:
        return conn.execute(f"SELECT {SERVICE_PUBLIC} FROM services WHERE user_id = %s ORDER BY id",
                            (user_id,)).fetchall()


def get_service_row(user_id: int, name: str) -> dict | None:      # includes the ENCRYPTED token (server side only)
    with pool.connection() as conn:
        return conn.execute("SELECT * FROM services WHERE user_id = %s AND name = %s", (user_id, name)).fetchone()


def get_service_row_by_id(user_id: int, service_id: int) -> dict | None:
    with pool.connection() as conn:
        return conn.execute("SELECT * FROM services WHERE user_id = %s AND id = %s", (user_id, service_id)).fetchone()


def delete_service(user_id: int, service_id: int) -> bool:
    with pool.connection() as conn:
        return conn.execute("DELETE FROM services WHERE user_id = %s AND id = %s RETURNING id",
                            (user_id, service_id)).fetchone() is not None


def create_remediation(incident_id, approver_id, action, target_sha, status, pr_url, detail) -> int:
    with pool.connection() as conn:
        return conn.execute(
            "INSERT INTO remediations (incident_id, user_id, action, target_sha, status, pr_url, detail) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (incident_id, approver_id, action, target_sha[:40], status, pr_url, detail[:1000])).fetchone()["id"]


def list_remediations(incident_id: int) -> list[dict]:
    with pool.connection() as conn:
        return conn.execute("SELECT id, action, target_sha, status, pr_url, detail, created FROM remediations "
                            "WHERE incident_id = %s ORDER BY id", (incident_id,)).fetchall()


def add_audit(user_id: int, action: str, target: str) -> None:
    with pool.connection() as conn:
        conn.execute("INSERT INTO audit_logs (user_id, action, target) VALUES (%s, %s, %s)",
                     (user_id, action[:50], target[:100]))

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