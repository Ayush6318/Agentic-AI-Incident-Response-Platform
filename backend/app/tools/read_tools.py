from langchain_core.tools import tool

from app.providers import code_provider, log_provider, metrics_provider
from app.providers.base import ProviderError
from app.providers.util import as_tool_output
from app.services import UnknownService


def _safe(source: str, fn):
    try:
        return as_tool_output(source, fn())
    except (ProviderError, UnknownService) as e:
        return as_tool_output(source, f"ERROR: {e}")
    except Exception as e:
        return as_tool_output(source, f"ERROR: unexpected failure ({type(e).__name__}): {e}")


@tool
def search_logs(service: str, level: str = "ERROR", minutes: int = 30) -> str:
    """Search recent logs of a service. level is ERROR, WARNING or INFO (WARNING includes errors,
    INFO includes everything). minutes is how far back to look (max 1440 = 24 hours)."""
    return _safe("logs", lambda: log_provider().search(service, level.upper(), min(max(minutes, 1), 1440)))

@tool
def get_metrics(service: str, metric: str, minutes: int = 30) -> str:
    """Summarize one metric of a service over the last N minutes (max 1440 = 24 hours): first, last, min, max
    values and when the biggest change happened. Use only the metric names listed in your instructions."""
    return _safe("metrics", lambda: metrics_provider().query(service, metric, min(max(minutes, 5), 1440)))

@tool
def get_recent_deploys(service: str, hours: int = 24) -> str:
    """List recent deploy/restart markers of a service with the commit version that was started."""
    return _safe("deploys", lambda: log_provider().deploys(service, min(max(hours, 1), 168)))


@tool
def get_active_alerts(service: str) -> str:
    """List alerts that are currently pending or firing for a service."""
    return _safe("alerts", lambda: metrics_provider().alerts(service))


@tool
def get_running_version(service: str) -> str:
    """Return the commit version the service is running right now and since when. Use it to decide which
    commit to inspect."""
    return _safe("version", lambda: metrics_provider().running_version(service))

@tool
def get_recent_commits(service: str, hours: int = 24) -> str:
    """List recent commits of the service's repository (sha, time, author, first line of message)."""
    return _safe("commits", lambda: code_provider().recent_commits(service, min(max(hours, 1), 720)))


@tool
def get_commit_diff(service: str, sha: str) -> str:
    """Show the files and changed lines of one commit."""
    return _safe("diff", lambda: code_provider().commit_diff(service, sha))