from app.providers.loki import LokiLogProvider
from app.config import settings

p = LokiLogProvider(settings.LOKI_URL)
print(p.search("payment-service", "ERROR", 30))
print(p.deploys("payment-service", 24))