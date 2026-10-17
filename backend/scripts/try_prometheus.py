from app.providers.prometheus import PrometheusMetricsProvider
from app.config import settings

p = PrometheusMetricsProvider(settings.PROMETHEUS_URL)
for m in ["error_rate_percent", "db_pool_usage_percent", "memory_mb"]:
    print(p.query("payment-service", m, 30))
print(p.alerts("payment-service"))