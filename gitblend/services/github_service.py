"""GitHub REST API service.

No third-party GitHub SDK — uses urllib.request directly so there
are zero extra dependencies to bundle into the Blender extension.
"""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

_SSL_CONTEXT = ssl.create_default_context()

from ..domain.errors import AuthError, GitBlendError, NetworkError
from ..domain.models import DeviceFlowData, GitHubRepo, PullRequest, Release
from ..domain.result import Result, err, ok
from ..infrastructure.auth_store import AuthStore

_API_BASE = "https://api.github.com"
_GITHUB_HOST = "github.com"

# OAuth app client ID for device flow (public, non-secret)
_CLIENT_ID = "Ov23lijVNY7BP9XRWwkC"


class GitHubService:
    """Thin wrapper around GitHub REST API.

    All methods return Result[T, GitBlendError].
    """

    def __init__(self, auth: AuthStore) -> None:
        self._auth = auth

    # ------------------------------------------------------------------ #
    # Authentication                                                       #
    # ------------------------------------------------------------------ #

    def authenticate_pat(self, token: str) -> Result[str, GitBlendError]:
        """Validate a PAT and save it if valid. Returns the username."""
        try:
            data = self._request("GET", "/user", token=token)
        except GitBlendError as e:
            return err(e)
        username = data.get("login", "")
        if not username:
            return err(AuthError("Token is valid but no username returned."))
        try:
            self._auth.save_token(_GITHUB_HOST, token)
            self._auth.save_meta(_GITHUB_HOST, "username", username)
        except Exception as e:
            return err(AuthError(f"Token valid but could not save credentials: {e}"))
        return ok(username)

    def start_device_flow(self) -> Result[DeviceFlowData, GitBlendError]:
        """Start the GitHub device authorization flow.

        Returns DeviceFlowData containing user_code and verification_uri.
        The user must visit the URI and enter the code to authorize.
        """
        try:
            body = json.dumps({
                "client_id": _CLIENT_ID,
                "scope": "repo user",
            }).encode()
            req = urllib.request.Request(
                "https://github.com/login/device/code",
                data=body,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return err(AuthError(
                    "Device flow is not configured for this installation. "
                    "Use 'Connect with Token' (PAT) instead."
                ))
            return err(NetworkError(f"HTTP {e.code}: {e.reason}"))
        except urllib.error.URLError as e:
            return err(NetworkError(str(e)))
        except Exception as e:
            return err(NetworkError(str(e)))

        if "error" in data:
            description = data.get("error_description") or data["error"]
            return err(AuthError(f"GitHub: {description}"))

        return ok(DeviceFlowData(
            device_code=data["device_code"],
            user_code=data["user_code"],
            verification_uri=data["verification_uri"],
            expires_in=data.get("expires_in", 900),
            interval=data.get("interval", 5),
        ))

    def poll_device_flow(
        self,
        device_code: str,
        interval: int = 5,
        max_attempts: int = 60,
    ) -> Result[str, GitBlendError]:
        """Poll for device flow completion. Returns the access token when granted.

        Blocks until authorized or max_attempts reached.
        """
        for _ in range(max_attempts):
            try:
                body = json.dumps({
                    "client_id": _CLIENT_ID,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                }).encode()
                req = urllib.request.Request(
                    "https://github.com/login/oauth/access_token",
                    data=body,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT) as resp:
                    data = json.loads(resp.read().decode())
            except urllib.error.URLError as e:
                return err(NetworkError(str(e)))

            if "access_token" in data:
                token = data["access_token"]
                try:
                    self._auth.save_token(_GITHUB_HOST, token)
                except Exception as e:
                    return err(AuthError(f"Authorized but could not save credentials: {e}"))
                return ok(token)

            error_code = data.get("error", "")
            if error_code == "authorization_pending":
                time.sleep(interval)
                continue
            elif error_code == "slow_down":
                interval += 5
                time.sleep(interval)
                continue
            elif error_code in ("expired_token", "access_denied"):
                return err(AuthError(f"Device flow failed: {error_code}"))

        return err(AuthError("Device flow timed out — user did not authorize in time."))

    def get_authenticated_user(self) -> Result[str, GitBlendError]:
        """Return the authenticated username."""
        try:
            data = self._request("GET", "/user")
            return ok(data.get("login", ""))
        except GitBlendError as e:
            return err(e)

    def is_authenticated(self) -> bool:
        return self._auth.has_token(_GITHUB_HOST)

    def logout(self) -> None:
        self._auth.delete_token(_GITHUB_HOST)

    # ------------------------------------------------------------------ #
    # Repositories                                                         #
    # ------------------------------------------------------------------ #

    def create_repo(
        self,
        name: str,
        private: bool = True,
        description: str = "",
    ) -> Result[GitHubRepo, GitBlendError]:
        try:
            data = self._request("POST", "/user/repos", {
                "name": name,
                "private": private,
                "description": description,
                "auto_init": False,
            })
            return ok(self._parse_repo(data))
        except GitBlendError as e:
            return err(e)

    def get_repo(self, owner: str, name: str) -> Result[GitHubRepo, GitBlendError]:
        try:
            data = self._request("GET", f"/repos/{owner}/{name}")
            return ok(self._parse_repo(data))
        except GitBlendError as e:
            return err(e)

    def list_user_repos(self) -> Result[list[GitHubRepo], GitBlendError]:
        try:
            data = self._request("GET", "/user/repos?per_page=100&sort=updated")
            if not isinstance(data, list):
                return ok([])
            return ok([self._parse_repo(r) for r in data])
        except GitBlendError as e:
            return err(e)

    def list_blender_repos(self, username: str) -> Result[list[GitHubRepo], GitBlendError]:
        """Return repos owned by username that have the 'blender' topic."""
        try:
            data = self._request(
                "GET",
                f"/search/repositories?q=topic:blender+user:{username}&sort=updated&per_page=100",
            )
            items = data.get("items", []) if isinstance(data, dict) else []
            return ok([self._parse_repo(r) for r in items])
        except GitBlendError as e:
            return err(e)

    # ------------------------------------------------------------------ #
    # Pull Requests                                                        #
    # ------------------------------------------------------------------ #

    def create_pr(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str = "",
    ) -> Result[PullRequest, GitBlendError]:
        try:
            data = self._request("POST", f"/repos/{owner}/{repo}/pulls", {
                "title": title,
                "head": head,
                "base": base,
                "body": body,
            })
            return ok(self._parse_pr(data))
        except GitBlendError as e:
            return err(e)

    def list_prs(self, owner: str, repo: str) -> Result[list[PullRequest], GitBlendError]:
        try:
            data = self._request("GET", f"/repos/{owner}/{repo}/pulls?state=open")
            if not isinstance(data, list):
                return ok([])
            return ok([self._parse_pr(pr) for pr in data])
        except GitBlendError as e:
            return err(e)

    # ------------------------------------------------------------------ #
    # Releases                                                             #
    # ------------------------------------------------------------------ #

    def create_release(
        self,
        owner: str,
        repo: str,
        tag: str,
        name: str,
        body: str = "",
        draft: bool = False,
        prerelease: bool = False,
    ) -> Result[Release, GitBlendError]:
        try:
            data = self._request("POST", f"/repos/{owner}/{repo}/releases", {
                "tag_name": tag,
                "name": name,
                "body": body,
                "draft": draft,
                "prerelease": prerelease,
            })
            return ok(self._parse_release(data))
        except GitBlendError as e:
            return err(e)

    def list_releases(self, owner: str, repo: str) -> Result[list[Release], GitBlendError]:
        try:
            data = self._request("GET", f"/repos/{owner}/{repo}/releases")
            if not isinstance(data, list):
                return ok([])
            return ok([self._parse_release(r) for r in data])
        except GitBlendError as e:
            return err(e)

    # ------------------------------------------------------------------ #
    # Internal HTTP helpers                                                #
    # ------------------------------------------------------------------ #

    def _request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> Any:
        url = f"{_API_BASE}{path}"
        body = json.dumps(data).encode() if data else None
        token = token or self._get_token()
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "gitblend/0.1.0",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if body:
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30, context=_SSL_CONTEXT) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode() if e else ""
            if e.code in (401, 403):
                raise AuthError(f"HTTP {e.code}: {body_text}") from e
            raise NetworkError(f"HTTP {e.code}: {body_text}") from e
        except urllib.error.URLError as e:
            raise NetworkError(str(e)) from e

    def _get_token(self) -> str:
        token = self._auth.load_token(_GITHUB_HOST)
        if not token:
            raise AuthError("Not authenticated. Connect to GitHub first.")
        return token

    # ------------------------------------------------------------------ #
    # Parsers                                                              #
    # ------------------------------------------------------------------ #

    def _parse_repo(self, data: dict[str, Any]) -> GitHubRepo:
        return GitHubRepo(
            name=data.get("name", ""),
            full_name=data.get("full_name", ""),
            url=data.get("html_url", ""),
            clone_url=data.get("clone_url", ""),
            ssh_url=data.get("ssh_url", ""),
            default_branch=data.get("default_branch", "main"),
            private=data.get("private", True),
            description=data.get("description") or "",
            topics=data.get("topics", []),
        )

    def _parse_pr(self, data: dict[str, Any]) -> PullRequest:
        return PullRequest(
            number=data.get("number", 0),
            title=data.get("title", ""),
            url=data.get("html_url", ""),
            state=data.get("state", "open"),
            head=data.get("head", {}).get("ref", ""),
            base=data.get("base", {}).get("ref", "main"),
            author=data.get("user", {}).get("login", ""),
            body=data.get("body") or "",
        )

    def _parse_release(self, data: dict[str, Any]) -> Release:
        return Release(
            tag=data.get("tag_name", ""),
            name=data.get("name", ""),
            url=data.get("html_url", ""),
            published_at=data.get("published_at", ""),
            body=data.get("body") or "",
            draft=data.get("draft", False),
            prerelease=data.get("prerelease", False),
        )
