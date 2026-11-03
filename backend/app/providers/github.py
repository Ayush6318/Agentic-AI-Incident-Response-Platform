import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx

from app.providers.base import ProviderError
from app.services import ServiceConfig, as_config

API = "https://api.github.com"
SHA = re.compile(r"[0-9a-fA-F]{4,40}")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MAX_FILES, MAX_AGE_DAYS = 10, 14


def _first_line(message: str) -> str:
    return (message or "").splitlines()[0][:200] if message else ""


def _msg(r: httpx.Response) -> str:
    try:
        return str(r.json().get("message", ""))[:160]
    except Exception:
        return ""


class GitHubCodeProvider:
    def __init__(self, token: str = "", client: httpx.Client | None = None):
        self.default_token = token
        self.client = client or httpx.Client(base_url=API, timeout=15.0)

    def _request(self, method, path, token, *, params=None, json=None, allow_404=False):
        if not token:
            raise ProviderError("No GitHub token is configured for this service")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28"}
        try:
            r = self.client.request(method, path, params=params, json=json, headers=headers)
        except httpx.HTTPError as e:
            raise ProviderError(f"GitHub unreachable: {e}")
        if r.status_code == 404 and allow_404:
            return None
        if r.status_code == 404:
            raise ProviderError("GitHub 404: repository, branch or commit not found, or the token has no access to it")
        if r.status_code in (401, 403):
            raise ProviderError(f"GitHub {r.status_code}: token invalid, missing a permission, or rate limited ({_msg(r)})")
        if r.status_code >= 400:
            raise ProviderError(f"GitHub error {r.status_code}: {_msg(r)}")
        return r.json() if r.content else {}

    def _cfg(self, service) -> ServiceConfig:
        cfg = as_config(service)
        if not cfg.repo:
            raise ProviderError(f"No GitHub repository is configured for service '{cfg.name}'")
        return cfg

    def verify_access(self, repo: str, token: str) -> dict:
        if not REPO.fullmatch(repo or ""):
            raise ProviderError("Repository must look like owner/name")
        info = self._request("GET", f"/repos/{repo}", token)
        self._request("GET", f"/repos/{repo}/commits", token, params={"per_page": 1})
        return {"default_branch": info.get("default_branch", "main"), "private": bool(info.get("private"))}

    # ---------------------------------------------------------------- reads
    def recent_commits(self, service, hours: int):
        cfg = self._cfg(service)
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
        items = self._request("GET", f"/repos/{cfg.repo}/commits", cfg.token or self.default_token,
                              params={"since": since, "per_page": 15, "sha": cfg.default_branch})
        if not items:
            return {"note": f"No commits in the last {hours}h. Try a larger window."}
        return [{"sha": c["sha"][:7], "time": c["commit"]["author"]["date"], "author": c["commit"]["author"]["name"],
                 "message": _first_line(c["commit"]["message"])} for c in items]

    def commit_diff(self, service, sha: str):
        if not SHA.fullmatch(sha or ""):
            raise ProviderError("sha must be 4 to 40 hex characters")
        cfg = self._cfg(service)
        c = self._request("GET", f"/repos/{cfg.repo}/commits/{sha}", cfg.token or self.default_token)
        files = [{"file": f["filename"], "status": f["status"], "additions": f["additions"],
                  "deletions": f["deletions"], "patch": (f.get("patch") or "")[:2500]} for f in c.get("files", [])[:8]]
        return {"sha": c["sha"][:7], "time": c["commit"]["author"]["date"],
                "message": c["commit"]["message"][:300], "files": files}

    # ---------------------------------------------------------------- real remediation
    def _blob_sha(self, repo, path, ref, token):
        data = self._request("GET", f"/repos/{repo}/contents/{quote(path, safe='/')}", token,
                             params={"ref": ref}, allow_404=True)
        if data is None:
            return None
        if isinstance(data, list) or data.get("type") != "file":
            raise ProviderError(f"{path} is not a regular file, so it cannot be reverted automatically")
        return data["sha"]

    def create_revert_pr(self, cfg: ServiceConfig, sha: str, incident_id: int, summary: str = "",
                         merge: bool = False) -> dict:
        if not SHA.fullmatch(sha or ""):
            raise ProviderError("sha must be 4 to 40 hex characters")
        token, repo, base = cfg.write_token, cfg.repo, cfg.default_branch
        if not (cfg.can_write and token):
            raise ProviderError("This service is read-only: remediation is not enabled")

        # 1. is this commit safe to revert automatically?
        c = self._request("GET", f"/repos/{repo}/commits/{sha}", token)
        full, parents, files = c["sha"], c.get("parents", []), c.get("files", [])
        if len(parents) != 1:
            raise ProviderError("Only single-parent (non-merge) commits can be reverted automatically")
        if not files or len(files) > MAX_FILES:
            raise ProviderError(f"Commit changes {len(files)} files; automatic revert supports 1 to {MAX_FILES}")
        if any(f["status"] not in ("added", "modified", "removed") for f in files):
            raise ProviderError("Commit renames or copies files; automatic revert does not support that")
        when = datetime.fromisoformat(c["commit"]["author"]["date"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - when > timedelta(days=MAX_AGE_DAYS):
            raise ProviderError(f"Commit is older than {MAX_AGE_DAYS} days; revert it manually")
        parent_sha, title_line = parents[0]["sha"], _first_line(c["commit"]["message"])

        # 2. current head, and is the commit part of the branch history?
        head = self._request("GET", f"/repos/{repo}/git/ref/heads/{quote(base, safe='/')}", token)["object"]["sha"]
        head_tree = self._request("GET", f"/repos/{repo}/git/commits/{head}", token)["tree"]["sha"]
        status = self._request("GET", f"/repos/{repo}/compare/{full}...{head}", token).get("status")
        if status not in ("ahead", "identical"):
            raise ProviderError(f"Commit is not part of the {base} branch history")

        # 3. already reverted?
        for x in self._request("GET", f"/repos/{repo}/commits", token, params={"sha": base, "per_page": 30}):
            if(x["sha"] == full):
                break
            m = x["commit"]["message"]
            if full in m or m.startswith(f'Revert "{title_line}"'):
                raise ProviderError(f"Commit appears to be reverted already ({x['sha'][:7]})")

        # 4. per-file conflict check; new tree entries set each file back to its parent's version
        entries = []
        for f in files:
            path = f["filename"]
            at_commit = self._blob_sha(repo, path, full, token)
            at_head = self._blob_sha(repo, path, head, token)
            at_parent = self._blob_sha(repo, path, parent_sha, token)
            if at_head != at_commit:
                raise ProviderError(f"Cannot revert automatically: {path} was changed again after this commit")
            if at_parent != at_head:
                entries.append({"path": path, "mode": "100644", "type": "blob", "sha": at_parent})  # None deletes
        if not entries:
            raise ProviderError("Nothing to revert: the files already match the parent version")

        # 5. one new commit, one branch, one pull request
        tree = self._request("POST", f"/repos/{repo}/git/trees", token,
                             json={"base_tree": head_tree, "tree": entries})["sha"]
        message = (f'Revert "{title_line}"\n\nThis reverts commit {full}.\n\n'
                   f"Proposed by the Incident Response Agent after human approval (incident #{incident_id}).")
        new_commit = self._request("POST", f"/repos/{repo}/git/commits", token,
                                   json={"message": message, "tree": tree, "parents": [head]})["sha"]
        branch = f"incident-agent/revert-{full[:7]}-i{incident_id}"
        self._request("POST", f"/repos/{repo}/git/refs", token, json={"ref": f"refs/heads/{branch}", "sha": new_commit})
        body = (f"Revert proposed by the Incident Response Agent after human approval.\n\n"
                f"**Incident:** #{incident_id}\n**Reverted commit:** `{full}`\n\n### Analysis\n{summary[:1500]}\n\n"
                f"_Review the diff before merging. Merging this pull request rolls the change back._")
        pr = self._request("POST", f"/repos/{repo}/pulls", token,
                           json={"title": f'Revert "{title_line}"', "head": branch, "base": base, "body": body})

        result = {"status": "pr_opened", "pr_number": pr["number"], "pr_url": pr["html_url"], "branch": branch,
                  "reverted_commit": full[:7], "files": [e["path"] for e in entries], "detail": ""}
        if merge:
            try:
                self._request("PUT", f"/repos/{repo}/pulls/{pr['number']}/merge", token,
                              json={"merge_method": "merge", "commit_title": f"Merge revert of {full[:7]}"})
                result["status"] = "merged"
            except ProviderError as e:
                result["detail"] = f"Pull request opened, but automatic merge failed: {e}"
        return result