from app.config import settings
from app.providers.github import GitHubCodeProvider

p = GitHubCodeProvider(settings.GITHUB_TOKEN)
commits = p.recent_commits("payment-service", 72)
print(commits)
print(p.commit_diff("payment-service", commits[0]["sha"]))