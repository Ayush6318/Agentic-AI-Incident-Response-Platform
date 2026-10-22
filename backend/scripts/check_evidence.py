import json

from app.providers import code_provider, log_provider, metrics_provider

S = "payment-service"


def show(title, data):
    print(f"\n=== {title}")
    print(json.dumps(data, indent=2, default=str)[:1800])


alerts = metrics_provider().alerts(S)
show("active alerts", alerts)

metric_data = {}
for m in ["error_rate_percent", "latency_p95_seconds", "db_pool_usage_percent", "db_pool_waiting"]:
    metric_data[m] = metrics_provider().query(S, m, 15)
    show(f"metric {m}", metric_data[m])

errors = log_provider().search(S, "ERROR", 15)
show("ERROR logs (grouped)", errors)
running = metrics_provider().running_version(S)
show("running version", running)
commits = code_provider().recent_commits(S, 168)
show("commits (7 days)", commits)

top = (errors.get("groups") or [{}])[0]
suspect = (top.get("versions") or [None])[0]
diff = code_provider().commit_diff(S, suspect) if suspect else {}
show(f"diff of {suspect}", diff)

in_history = isinstance(commits, list) and any(c["sha"] == suspect for c in commits)
checks = [
    ("error logs found", errors.get("total_lines", 0) > 0),
    ("top error mentions pool exhaustion", "pool exhausted" in top.get("message", "").lower()),
    ("running version is known", "versions" in running),
    ("errors occur on the running version", suspect in running.get("versions", [])),
    ("that version is in the commit history", in_history),
    ("error rate above 10%", metric_data["error_rate_percent"].get("max", 0) > 10),
    ("pool usage reached 100%", metric_data["db_pool_usage_percent"].get("max", 0) >= 100),
    ("an alert is pending or firing", isinstance(alerts, list) and len(alerts) > 0),
    ("diff shows the BATCH_SIZE change", any("BATCH_SIZE" in f.get("patch", "") for f in diff.get("files", []))),
]
print("\n=== CHECKS")
for name, ok in checks:
    print(("PASS  " if ok else "FAIL  ") + name)