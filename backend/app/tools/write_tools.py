import datetime
import re

from app.providers import code_provider, metrics_provider
from app.providers.base import ProviderError
from app.services import ServiceConfig

REAL_STATUSES = {"pr_opened", "merged", "failed", "blocked"}
SHA_RE = re.compile(r"[0-9a-fA-F]{4,40}")

# ---- kept for your guardrail unit tests (simulated)
AUDIT_LOG: list[dict] = []
ALLOWED_WRITE_ACTIONS = {"rollback", "restart"}
FORBIDDEN = {"delete_database", "drop_table"}


def execute_action(action: str, target: str, user_role: str, approved: bool) -> str:
    if action in FORBIDDEN:
        raise PermissionError(f"{action} is never allowed")
    if action not in ALLOWED_WRITE_ACTIONS:
        raise PermissionError(f"Unknown action {action}")
    if user_role not in ("sre", "admin"):
        raise PermissionError("User not authorized for write actions")
    if not approved:
        raise PermissionError("Human approval required")
    AUDIT_LOG.append({"time": datetime.datetime.utcnow().isoformat(), "action": action, "target": target,
                      "role": user_role})
    return f"Executed {action} on {target} (simulated)"


# ---- real remediation
def _result(status: str, message: str, **extra) -> dict:
    return {"status": status, "message": message, **extra}


def _same(a: str, b: str) -> bool:
    a, b = a.lower(), (b or "").lower()
    return bool(b) and (a.startswith(b) or b.startswith(a))


def _running_versions(cfg: ServiceConfig) -> list[str]:
    try:
        data = metrics_provider().running_version(cfg)
        return list(data.get("versions", [])) if isinstance(data, dict) else []
    except Exception:
        return []


def execute_rollback(cfg: ServiceConfig, sha: str, incident_id: int, summary: str = "") -> dict:
    """Called only after human approval. Status: pr_opened | merged | failed | blocked."""
    if not SHA_RE.fullmatch(sha or ""):
        return _result("blocked", "The plan did not contain a valid commit id, so nothing was changed.")
    if not (cfg.can_write and cfg.write_token):
        return _result("blocked", f"Remediation is not enabled for '{cfg.name}' (read-only access). "
                                  f"Revert commit {sha[:7]} manually, or reconnect the service with rollback allowed.")
    running = _running_versions(cfg)
    if running and not any(_same(sha, v) for v in running):
        return _result("blocked", f"Commit {sha[:7]} is not the version running now ({', '.join(running)}); "
                                  "it may already have been rolled back. Nothing was changed.")
    try:
        res = code_provider().create_revert_pr(cfg, sha, incident_id, summary, merge=cfg.auto_merge)
    except ProviderError as e:
        return _result("failed", f"Rollback could not be performed: {e}")

    if res["status"] == "simulated":
        return _result("blocked", "Simulated rollback (fake provider): nothing was changed.", **res)
    if res["status"] == "merged":
        msg = (f"Revert pull request #{res['pr_number']} was merged into {cfg.default_branch}: {res['pr_url']}. "
               "If your pipeline does not deploy on merge, redeploy now.")
    else:
        msg = (f"Opened revert pull request #{res['pr_number']} for commit {res['reverted_commit']}: {res['pr_url']}. "
               "Review and merge it to roll back." + (f" {res['detail']}" if res.get("detail") else ""))
    return _result(res["status"], msg, **{k: v for k, v in res.items() if k != "status"})