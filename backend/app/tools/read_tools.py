import json
from pathlib import Path
from langchain_core.tools import tool

DATA = Path(__file__).resolve().parents[2] / "data"

@tool
def search_logs(service: str, level: str = "ERROR") -> str:
    """Search logs of a service filtered by level (INFO, ERROR)."""
    logs = json.loads((DATA / "logs.json").read_text())
    hits = [l for l in logs if l["service"] == service and l["level"] in (level, "INFO")]
    return json.dumps(hits)
  

@tool
def get_metrics(metric: str) -> str:
    """Get before/after-deploy values for a metric, e.g. db_connection_usage."""
    metrics = json.loads((DATA / "metrics.json").read_text())
    return json.dumps(metrics.get(metric, "metric not found"))
  

@tool
def get_recent_commits(repository: str) -> str:
    """List recent commits of a repository."""
    return (DATA / "commits.json").read_text()

  

