import math
import time
from datetime import datetime, timezone

import httpx

from app.providers.base import ProviderError
from app.services import get_service

# The model picks a name; only these queries ever run. {job} comes from the service registry.
METRICS = {
        "error_rate_percent": '(sum(rate(http_requests_total{{job="{job}",status=~"5.."}}[1m])) or vector(0)) '
                          '/ sum(rate(http_requests_total{{job="{job}"}}[1m])) * 100',
    "request_rate": 'sum(rate(http_requests_total{{job="{job}"}}[1m]))',
    "latency_p95_seconds": 'histogram_quantile(0.95, sum by (le) '
                           '(rate(http_request_duration_seconds_bucket{{job="{job}"}}[1m])))',
    "db_pool_in_use": 'db_pool_in_use{{job="{job}"}}',
    "db_pool_waiting": 'db_pool_waiting{{job="{job}"}}',
    "db_pool_usage_percent": 'db_pool_in_use{{job="{job}"}} / db_pool_max{{job="{job}"}} * 100',
    "memory_mb": 'process_resident_memory_bytes{{job="{job}"}} / 1e6',
    "service_up": 'up{{job="{job}"}}',
}


def _iso(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec="seconds")


def _r(x: float) -> float:
    return round(x, 3)


class PrometheusMetricsProvider:
    metric_names = list(METRICS)

    def __init__(self, base_url: str, client: httpx.Client | None = None):
        self.base_url = base_url
        self.client = client or httpx.Client(base_url=base_url, timeout=10.0)

    def _get(self, path: str, **params):
        try:
            r = self.client.get(path, params=params)
        except httpx.HTTPError as e:
            raise ProviderError(f"Prometheus unreachable at {self.base_url}: {e}")
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code >= 400 or data.get("status") != "success":
            raise ProviderError(f"Prometheus error: {data.get('error', r.status_code)}")
        return data["data"]

    def query(self, service: str, metric: str, minutes: int):
        if metric not in METRICS:
            raise ProviderError(f"Unknown metric '{metric}'. Available: {', '.join(METRICS)}")
        job = get_service(service)["prom_job"]
        end = time.time()
        step = max(15, minutes * 60 // 300)
        data = self._get("/api/v1/query_range", query=METRICS[metric].format(job=job),
                         start=end - minutes * 60, end=end, step=step)
        if not data["result"]:
            return {"metric": metric, "note": "No data returned:no matching series. The service may be down or not scraped, or nothing has happened yet (for example no traffic)."}

        pts = [(float(t), float(v)) for t, v in data["result"][0]["values"] if math.isfinite(float(v))]
        if not pts:
            return {"metric": metric, "note": "No finite values in this window (no traffic?)."}

        vals = [v for _, v in pts]
        out = {"metric": metric, "window_minutes": minutes,"step_seconds": step,"first": _r(vals[0]), "last": _r(vals[-1]),
               "min": _r(min(vals)), "max": _r(max(vals)), "avg": _r(sum(vals) / len(vals))}
        positive = [t for t, v in pts if v > 0]
        if positive:
            out["first_above_zero_at"], out["last_above_zero_at"] = _iso(positive[0]), _iso(positive[-1])
        else:
            out["always_zero"] = True
        
        n = len(pts)
        if n > 1:
            i = max(range(1, n), key=lambda k: abs(pts[k][1] - pts[k - 1][1]))
            out["biggest_jump"] = {"at": _iso(pts[i][0]), "from": _r(pts[i - 1][1]), "to": _r(pts[i][1])}
        idx = sorted({round(k * (n - 1) / 7) for k in range(8)}) if n > 8 else range(n)
        out["points"] = [{"t": _iso(pts[k][0]), "v": _r(pts[k][1])} for k in idx]
        return out

    def alerts(self, service: str):
        get_service(service)
        out = []
        for a in self._get("/api/v1/alerts")["alerts"]:
            labels = a.get("labels", {})
            if labels.get("service") not in (None, service):
                continue
            out.append({"alert": labels.get("alertname"), "state": a["state"], "since": a.get("activeAt"),
                        "severity": labels.get("severity"), "summary": a.get("annotations", {}).get("summary")})
        return out or {"note": "No pending or firing alerts"}
      
    def running_version(self, service: str):
      
      job = get_service(service)["prom_job"]
      info = self._get("/api/v1/query", query=f'app_info{{job="{job}"}}')["result"]
      if not info:
            return {"note": "No version information: the service is down, not scraped, or exposes no app_info metric."}
      out = {"versions": sorted({s["metric"].get("version") for s in info})}
      start = self._get("/api/v1/query", query=f'process_start_time_seconds{{job="{job}"}}')["result"]
      if start:
            out["running_since"] = _iso(float(start[0]["value"][1]))
      return out