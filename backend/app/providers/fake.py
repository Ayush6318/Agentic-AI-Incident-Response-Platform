import json
import os
from pathlib import Path

from app.providers.base import ProviderError

DATA = Path(__file__).resolve().parents[2] / "data"


def _dir() -> Path:
    scenario = os.getenv("SCENARIO")
    return DATA / "scenarios" / scenario if scenario else DATA


def _load(name: str):
    return json.loads((_dir() / name).read_text())


class FakeLogProvider:
    def search(self, service: str, level: str, minutes: int):
        return [l for l in _load("logs.json") if l["service"] == service and l["level"] in (level, "INFO")]

    def deploys(self, service: str, hours: int):
        return [{"time": l["ts"], "version": l["msg"].split()[-1]}
                for l in _load("logs.json") if "Deployed commit" in l["msg"]]


class FakeMetricsProvider:
    metric_names = ["db_connection_usage", "redis_memory_usage", "service_memory_usage",
                    "query_latency_ms", "error_rate"]

    def query(self, service: str, metric: str, minutes: int):
        metrics = _load("metrics.json")
        if metric not in metrics:
            raise ProviderError(f"Unknown metric '{metric}'. Available: {', '.join(metrics)}")
        return {"metric": metric, **metrics[metric]}

    def alerts(self, service: str):
        return {"note": "No active alerts (fake data)"}
      
    def running_version(self, service: str):
      
      deploys = [l for l in _load("logs.json") if "Deployed commit" in l["msg"]]
      if not deploys:
            return {"note": "No version information in fake data"}
      return {"versions": [deploys[-1]["msg"].split()[-1]]}


class FakeCodeProvider:
    def recent_commits(self, service: str, hours: int):
        return _load("commits.json")

    def commit_diff(self, service: str, sha: str):
        for c in _load("commits.json"):
            if c["sha"].startswith(sha):
                return {**c, "note": "diff not available in fake data"}
        raise ProviderError(f"Commit {sha} not found")