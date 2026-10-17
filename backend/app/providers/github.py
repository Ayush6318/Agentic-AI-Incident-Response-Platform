import re
from datetime import datetime, timedelta, timezone

import httpx

from app.providers.base import ProviderError
from app.services import get_service

SHA = re.compile(r"[0-9a-fA-F]{4,40}")


class GitHubCodeProvider:
    def __init__(self, token: str, client: httpx.Client | None = None):
        if not token:
            raise ProviderError("GITHUB_TOKEN is not set")
        self.client = client or httpx.Client(
            base_url="https://api.github.com", timeout=10.0,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28"})

    def _repo(self, service: str) -> str:
        repo = get_service(service)["repo"]
        if not repo:
            raise ProviderError(f"No GitHub repo configured for '{service}' (set GITHUB_REPO)")
        return repo

    def _get(self, path: str, **params):
        try:
            r = self.client.get(path, params=params)
        except httpx.HTTPError as e:
            raise ProviderError(f"GitHub unreachable: {e}")
        if r.status_code == 404:
            raise ProviderError("GitHub 404: repo or commit not found (check GITHUB_REPO and token access)")
        if r.status_code in (401, 403):
            raise ProviderError(f"GitHub {r.status_code}: token invalid, missing access, or rate limited")
        if r.status_code >= 400:
            raise ProviderError(f"GitHub error {r.status_code}")
        return r.json()

    def recent_commits(self, service: str, hours: int):
        repo = self._repo(service)
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
        items = self._get(f"/repos/{repo}/commits", since=since, per_page=15)
        if not items:
            return {"note": f"No commits in the last {hours}h. Try a larger window."}
        return [{"sha": c["sha"][:7], "time": c["commit"]["author"]["date"],
                 "author": c["commit"]["author"]["name"],
                 "message": c["commit"]["message"].splitlines()[0][:200]} for c in items]

    def commit_diff(self, service: str, sha: str):
        if not SHA.fullmatch(sha):                      # the model or a log line could supply anything
            raise ProviderError("sha must be 4 to 40 hex characters")
        repo = self._repo(service)
        c = self._get(f"/repos/{repo}/commits/{sha}")
        files = [{"file": f["filename"], "status": f["status"], "additions": f["additions"],
                  "deletions": f["deletions"], "patch": (f.get("patch") or "")[:2500]}
                 for f in c.get("files", [])[:8]]
        return {"sha": c["sha"][:7], "time": c["commit"]["author"]["date"],
                "message": c["commit"]["message"][:300], "files": files}