from app.config import settings

SERVICES = {
    "payment-service": {
        "repo": settings.GITHUB_REPO,
        "loki_labels": {"service": "payment-service"},
        "prom_job": "payment-service",
    },
}


class UnknownService(Exception):
    pass


def get_service(name: str) -> dict:
    key = name.strip().lower()
    if key not in SERVICES:
        raise UnknownService(f"Unknown service '{name}'. Known services: {', '.join(SERVICES)}")
    return SERVICES[key]