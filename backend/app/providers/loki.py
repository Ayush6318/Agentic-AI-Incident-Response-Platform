import json
import re
import time
from datetime import datetime, timezone

import httpx

from app.providers.base import ProviderError
from app.services import get_service

NS = 1_000_000_000


def _iso(ns: int) -> str:
    return datetime.fromtimestamp(ns / NS, timezone.utc).isoformat(timespec="seconds")


def _parse(line: str) -> dict:
    try:
        d = json.loads(line)
    except ValueError:
        return {"msg": line}
    return d if isinstance(d, dict) else {"msg": str(d)}


class LokiLogProvider:
    def __init__(self, base_url: str, client: httpx.Client | None = None):
        self.base_url = base_url
        self.client = client or httpx.Client(base_url=base_url, timeout=10.0)

    def _selector(self, service: str, extra: list[str] | None = None) -> str:
        labels = get_service(service)["loki_labels"]          # trusted values only, never from the model
        parts = [f'{k}="{v}"' for k, v in labels.items()] + (extra or [])
        return "{" + ", ".join(parts) + "}"

    def _query(self, logql: str, minutes: int, limit: int = 1000) -> list[tuple[int, str]]:
        end = time.time_ns()
        try:
            r = self.client.get("/loki/api/v1/query_range", params={
                "query": logql, "start": end - minutes * 60 * NS, "end": end,
                "limit": limit, "direction": "backward"})
        except httpx.HTTPError as e:
            raise ProviderError(f"Loki unreachable at {self.base_url}: {e}")
        if r.status_code == 400:
            raise ProviderError(f"Loki rejected the query: {r.text[:200]}")
        if r.status_code >= 400:
            raise ProviderError(f"Loki error {r.status_code}")
        lines = [(int(ts), line) for stream in r.json()["data"]["result"] for ts, line in stream["values"]]
        lines.sort()
        return lines

    def search(self, service: str, level: str, minutes: int):
        extra = {"ERROR": ['level="ERROR"'], "WARNING": ['level=~"WARNING|ERROR"'], "INFO": []}.get(level)
        if extra is None:
            raise ProviderError("level must be ERROR, WARNING or INFO")
        lines = self._query(self._selector(service, extra), minutes)
        if not lines:
            return {"window_minutes": minutes, "total_lines": 0,
                    "note": "No matching log lines. The service may be healthy, or its logs are not being collected."}

        groups: dict = {}
        for ts, line in lines:
            e = _parse(line)
            msg = str(e.get("msg", ""))
            key = (e.get("level"), re.sub(r"\d+(\.\d+)?", "N", msg))     # same message, different numbers
            g = groups.setdefault(key, {"level": e.get("level"), "message": msg[:300], "count": 0,
                                        "first": ts, "last": ts, "versions": set()})
            g["count"] += 1
            g["first"], g["last"] = min(g["first"], ts), max(g["last"], ts)
            if e.get("version"):
                g["versions"].add(e["version"])

        top = sorted(groups.values(), key=lambda g: -g["count"])[:10]
        for g in top:
            g["first"], g["last"], g["versions"] = _iso(g["first"]), _iso(g["last"]), sorted(g["versions"])
        return {"window_minutes": minutes, "total_lines": len(lines), "groups": top}

    def deploys(self, service: str, hours: int):
        lines = self._query(self._selector(service) + ' |= "Deployed commit"', hours * 60, limit=200)
        if not lines:
            return {"note": f"No deploy markers in the last {hours}h"}
        return [{"time": _iso(ts), "version": _parse(line).get("version"),
                 "msg": str(_parse(line).get("msg", ""))[:120]} for ts, line in lines[-10:]]