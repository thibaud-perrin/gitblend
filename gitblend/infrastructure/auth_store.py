"""Credential storage for GitHub tokens.

Tries platform-specific keychains first, falls back to a plaintext file
in the user's Blender config directory with a clear warning.
"""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path


class AuthStore:
    """Platform-aware credential store.

    Priority:
      macOS  → Keychain via `security` CLI
      Windows → Windows Credential Manager via `cmdkey` / PowerShell
      Linux  → Secret Service via `secret-tool` (if available)
      All    → JSON fallback in ~/.config/gitblend/credentials.json
    """

    FALLBACK_PATH = Path.home() / ".config" / "gitblend" / "credentials.json"
    KEYCHAIN_SERVICE = "gitblend"

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def save_token(self, host: str, token: str) -> None:
        sys = platform.system()
        if sys == "Darwin":
            self._mac_save(host, token)
        elif sys == "Windows":
            self._win_save(host, token)
        elif sys == "Linux":
            self._linux_save(host, token)
        else:
            self._fallback_save(host, token)

    def load_token(self, host: str) -> str | None:
        sys = platform.system()
        if sys == "Darwin":
            return self._mac_load(host)
        elif sys == "Windows":
            return self._win_load(host)
        elif sys == "Linux":
            return self._linux_load(host)
        else:
            return self._fallback_load(host)

    def delete_token(self, host: str) -> None:
        sys = platform.system()
        if sys == "Darwin":
            self._mac_delete(host)
        elif sys == "Windows":
            self._win_delete(host)
        elif sys == "Linux":
            self._linux_delete(host)
        else:
            self._fallback_delete(host)

    def has_token(self, host: str) -> bool:
        return self.load_token(host) is not None

    # ------------------------------------------------------------------ #
    # macOS Keychain                                                       #
    # ------------------------------------------------------------------ #

    def _mac_save(self, host: str, token: str) -> None:
        # Delete first to avoid duplicate errors
        self._mac_delete(host)
        subprocess.run(
            [
                "security", "add-generic-password",
                "-s", self.KEYCHAIN_SERVICE,
                "-a", host,
                "-w", token,
            ],
            check=True,
            capture_output=True,
        )

    def _mac_load(self, host: str) -> str | None:
        result = subprocess.run(
            [
                "security", "find-generic-password",
                "-s", self.KEYCHAIN_SERVICE,
                "-a", host,
                "-w",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
        return self._fallback_load(host)

    def _mac_delete(self, host: str) -> None:
        subprocess.run(
            [
                "security", "delete-generic-password",
                "-s", self.KEYCHAIN_SERVICE,
                "-a", host,
            ],
            capture_output=True,
        )

    # ------------------------------------------------------------------ #
    # Windows Credential Manager                                           #
    # ------------------------------------------------------------------ #

    def _win_save(self, host: str, token: str) -> None:
        target = f"{self.KEYCHAIN_SERVICE}/{host}"
        subprocess.run(
            ["cmdkey", f"/add:{target}", f"/user:{host}", f"/pass:{token}"],
            check=True,
            capture_output=True,
        )

    def _win_load(self, host: str) -> str | None:
        try:
            ps = (
                f'$cred = Get-StoredCredential -Target "{self.KEYCHAIN_SERVICE}/{host}"; '
                f'if ($cred) {{ $cred.GetNetworkCredential().Password }}'
            )
            result = subprocess.run(
                ["powershell", "-Command", ps],
                capture_output=True,
                text=True,
            )
            token = result.stdout.strip()
            return token if token else self._fallback_load(host)
        except FileNotFoundError:
            return self._fallback_load(host)

    def _win_delete(self, host: str) -> None:
        target = f"{self.KEYCHAIN_SERVICE}/{host}"
        subprocess.run(["cmdkey", f"/delete:{target}"], capture_output=True)

    # ------------------------------------------------------------------ #
    # Linux Secret Service                                                 #
    # ------------------------------------------------------------------ #

    def _linux_save(self, host: str, token: str) -> None:
        result = subprocess.run(
            ["secret-tool", "store", "--label", f"gitblend/{host}",
             "service", self.KEYCHAIN_SERVICE, "account", host],
            input=token,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            self._fallback_save(host, token)

    def _linux_load(self, host: str) -> str | None:
        result = subprocess.run(
            ["secret-tool", "lookup", "service", self.KEYCHAIN_SERVICE, "account", host],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
        return self._fallback_load(host)

    def _linux_delete(self, host: str) -> None:
        subprocess.run(
            ["secret-tool", "clear", "service", self.KEYCHAIN_SERVICE, "account", host],
            capture_output=True,
        )

    # ------------------------------------------------------------------ #
    # Plaintext fallback                                                   #
    # ------------------------------------------------------------------ #

    def _fallback_save(self, host: str, token: str) -> None:
        data = self._fallback_read_all()
        data[host] = token
        self.FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.FALLBACK_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _fallback_load(self, host: str) -> str | None:
        return self._fallback_read_all().get(host)

    def _fallback_delete(self, host: str) -> None:
        data = self._fallback_read_all()
        data.pop(host, None)
        self.FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.FALLBACK_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _fallback_read_all(self) -> dict[str, str]:
        if not self.FALLBACK_PATH.exists():
            return {}
        try:
            return json.loads(self.FALLBACK_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
