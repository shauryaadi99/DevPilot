"""GitHub API client integration.

Provides safe repository access, metadata retrieval, recursive tree inspection,
and manifest extraction without cloning the entire repository.
"""

import base64
from typing import Any, Dict, List, Optional
import httpx

from app.core.logging import logger

GITHUB_API_BASE = "https://api.github.com"


class GitHubError(Exception):
    """Base exception for GitHub API errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class GitHubClient:
    """Encapsulated GitHub REST API client."""

    def __init__(self, token: Optional[str] = None, timeout: float = 20.0):
        self.token = token
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "DevPilot-Agent-Platform",
        }
        if self.token and self.token.strip():
            headers["Authorization"] = f"Bearer {self.token.strip()}"
        return headers

    async def get_authenticated_user(self) -> Dict[str, Any]:
        """Validate token and fetch basic authenticated user details."""
        if not self.token:
            raise GitHubError("GitHub token is required to authenticate.", status_code=401)

        url = f"{GITHUB_API_BASE}/user"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers())
            except Exception as e:
                logger.error(f"GitHub connection error: {e}")
                raise GitHubError("Failed to connect to GitHub API.", status_code=503)

        if res.status_code == 401:
            raise GitHubError("Invalid or expired GitHub token.", status_code=401)
        if res.status_code != 200:
            raise GitHubError(f"GitHub returned HTTP {res.status_code}", status_code=res.status_code)

        data = res.json()
        return {
            "login": data.get("login"),
            "name": data.get("name"),
            "avatar_url": data.get("avatar_url"),
            "html_url": data.get("html_url"),
            "public_repos": data.get("public_repos"),
        }

    async def list_repositories(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List repositories accessible to the user, sorted by recently updated."""
        if not self.token:
            raise GitHubError("GitHub token required to list user repositories.", status_code=401)

        url = f"{GITHUB_API_BASE}/user/repos"
        params = {
            "sort": "updated",
            "per_page": min(limit, 100),
            "affiliation": "owner,collaborator",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers(), params=params)
            except Exception as e:
                logger.error(f"GitHub connection error: {e}")
                raise GitHubError("Failed to reach GitHub API.", status_code=503)

        if res.status_code == 401:
            raise GitHubError("Invalid GitHub token.", status_code=401)
        if res.status_code != 200:
            raise GitHubError(f"Failed to list repositories: {res.text}", status_code=res.status_code)

        repos = res.json()
        return [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "full_name": r.get("full_name"),
                "owner": r.get("owner", {}).get("login", ""),
                "default_branch": r.get("default_branch", "main"),
                "is_private": r.get("private", False),
                "html_url": r.get("html_url"),
                "description": r.get("description"),
                "language": r.get("language"),
                "stargazers_count": r.get("stargazers_count", 0),
                "updated_at": r.get("updated_at"),
            }
            for r in repos
        ]

    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch metadata for a specific repository."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers())
            except Exception as e:
                logger.error(f"GitHub API connection failed: {e}")
                raise GitHubError("Failed to connect to GitHub API.", status_code=503)

        if res.status_code == 404:
            raise GitHubError(f"Repository {owner}/{repo} not found.", status_code=404)
        if res.status_code == 401:
            raise GitHubError("Unauthorized access to repository.", status_code=401)
        if res.status_code != 200:
            raise GitHubError(f"GitHub error {res.status_code}", status_code=res.status_code)

        r = res.json()
        return {
            "id": r.get("id"),
            "name": r.get("name"),
            "full_name": r.get("full_name"),
            "owner": r.get("owner", {}).get("login", ""),
            "default_branch": r.get("default_branch", "main"),
            "is_private": r.get("private", False),
            "html_url": r.get("html_url"),
            "description": r.get("description"),
            "language": r.get("language"),
            "stargazers_count": r.get("stargazers_count", 0),
            "updated_at": r.get("updated_at"),
        }

    async def get_tree(self, owner: str, repo: str, branch: str = "main") -> List[Dict[str, Any]]:
        """Fetch recursive Git file tree."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{branch}"
        params = {"recursive": "1"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers(), params=params)
            except Exception as e:
                logger.error(f"GitHub tree fetch error: {e}")
                raise GitHubError("Failed to fetch repository tree.", status_code=503)

        if res.status_code == 404:
            # Try master branch if main not found
            if branch == "main":
                return await self.get_tree(owner, repo, branch="master")
            raise GitHubError(f"Branch {branch} not found in {owner}/{repo}.", status_code=404)

        if res.status_code != 200:
            raise GitHubError(f"Failed to fetch tree: HTTP {res.status_code}", status_code=res.status_code)

        data = res.json()
        tree = data.get("tree", [])
        return [
            {
                "path": item.get("path"),
                "type": item.get("type"),  # "blob" or "tree"
                "size": item.get("size", 0),
            }
            for item in tree
        ]

    async def get_file_content(self, owner: str, repo: str, path: str, branch: Optional[str] = None) -> Optional[str]:
        """Fetch raw content of a specific file."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        params = {}
        if branch:
            params["ref"] = branch

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.get(url, headers=self._get_headers(), params=params)
            except Exception as e:
                logger.warning(f"Failed to fetch {path} from {owner}/{repo}: {e}")
                return None

        if res.status_code != 200:
            return None

        data = res.json()
        if data.get("encoding") == "base64" and data.get("content"):
            try:
                decoded = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                return decoded
            except Exception:
                return None
        return None
