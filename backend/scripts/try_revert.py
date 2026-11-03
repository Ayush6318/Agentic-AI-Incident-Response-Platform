import sys

from app.db.database import pool
from app.services import resolve_service
from app.tools.write_tools import execute_rollback

user_id, service, sha = int(sys.argv[1]), sys.argv[2], sys.argv[3]
pool.open(wait=True, timeout=10)
try:
    cfg = resolve_service(user_id, service)
    print("service:", cfg.name, cfg.repo, "| can_write:", cfg.can_write, "| auto_merge:", cfg.auto_merge)
    print(execute_rollback(cfg, sha, 16, "Manual test of the revert step (no model involved)"))
finally:
    pool.close()