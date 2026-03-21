"""Unit tests for AuthStore — verifies fallback behaviour when platform keychains fail."""

from __future__ import annotations

import json
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import MagicMock, patch

import pytest

from gitblend.infrastructure.auth_store import AuthStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _store(tmp_path: Path) -> AuthStore:
    store = AuthStore()
    store.FALLBACK_PATH = tmp_path / "credentials.json"
    return store


# ---------------------------------------------------------------------------
# Fallback round-trip
# ---------------------------------------------------------------------------

class TestFallback:
    def test_save_and_load(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store._fallback_save("github.com", "token123")
        assert store._fallback_load("github.com") == "token123"

    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        assert store._fallback_load("github.com") is None

    def test_delete(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store._fallback_save("github.com", "token123")
        store._fallback_delete("github.com")
        assert store._fallback_load("github.com") is None

    def test_multiple_hosts(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store._fallback_save("github.com", "tok-a")
        store._fallback_save("gitlab.com", "tok-b")
        assert store._fallback_load("github.com") == "tok-a"
        assert store._fallback_load("gitlab.com") == "tok-b"


# ---------------------------------------------------------------------------
# Windows: _win_save falls back when cmdkey fails
# ---------------------------------------------------------------------------

class TestWindowsFallback:
    def test_win_save_falls_back_on_cmdkey_error(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        with patch(
            "gitblend.infrastructure.auth_store.subprocess.run",
            side_effect=CalledProcessError(1, ["cmdkey"]),
        ):
            store._win_save("github.com", "tok-win")

        # Token must have been saved to the JSON fallback
        assert store._fallback_load("github.com") == "tok-win"

    def test_win_save_falls_back_on_file_not_found(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        with patch(
            "gitblend.infrastructure.auth_store.subprocess.run",
            side_effect=FileNotFoundError("cmdkey not found"),
        ):
            store._win_save("github.com", "tok-win2")

        assert store._fallback_load("github.com") == "tok-win2"

    def test_win_load_falls_back_when_powershell_returns_empty(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store._fallback_save("github.com", "tok-fallback")

        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch(
            "gitblend.infrastructure.auth_store.subprocess.run",
            return_value=mock_result,
        ):
            token = store._win_load("github.com")

        assert token == "tok-fallback"

    def test_win_load_falls_back_on_exception(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        store._fallback_save("github.com", "tok-fallback2")

        with patch(
            "gitblend.infrastructure.auth_store.subprocess.run",
            side_effect=FileNotFoundError("powershell not found"),
        ):
            token = store._win_load("github.com")

        assert token == "tok-fallback2"


# ---------------------------------------------------------------------------
# macOS: _mac_save falls back when security CLI fails
# ---------------------------------------------------------------------------

class TestMacFallback:
    def test_mac_save_falls_back_on_security_error(self, tmp_path: Path) -> None:
        store = _store(tmp_path)

        def fake_run(cmd, **kwargs):
            if "add-generic-password" in cmd:
                raise CalledProcessError(1, cmd)
            # Allow delete to succeed silently
            return MagicMock(returncode=0)

        with patch("gitblend.infrastructure.auth_store.subprocess.run", side_effect=fake_run):
            store._mac_save("github.com", "tok-mac")

        assert store._fallback_load("github.com") == "tok-mac"

    def test_mac_save_falls_back_on_file_not_found(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        with patch(
            "gitblend.infrastructure.auth_store.subprocess.run",
            side_effect=FileNotFoundError("security not found"),
        ):
            store._mac_save("github.com", "tok-mac2")

        assert store._fallback_load("github.com") == "tok-mac2"
