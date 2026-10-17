from functools import lru_cache

from app.config import settings


@lru_cache
def code_provider():
    if settings.CODE_PROVIDER == "github":
        from app.providers.github import GitHubCodeProvider
        return GitHubCodeProvider(settings.GITHUB_TOKEN)
    from app.providers.fake import FakeCodeProvider
    return FakeCodeProvider()


@lru_cache
def log_provider():
    if settings.LOGS_PROVIDER == "loki":
        from app.providers.loki import LokiLogProvider
        return LokiLogProvider(settings.LOKI_URL)
    from app.providers.fake import FakeLogProvider
    return FakeLogProvider()


@lru_cache
def metrics_provider():
    if settings.METRICS_PROVIDER == "prometheus":
        from app.providers.prometheus import PrometheusMetricsProvider
        return PrometheusMetricsProvider(settings.PROMETHEUS_URL)
    from app.providers.fake import FakeMetricsProvider
    return FakeMetricsProvider()