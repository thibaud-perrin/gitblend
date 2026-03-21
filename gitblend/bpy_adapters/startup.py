"""Startup handler — restores session state after a .blend file is loaded."""

from __future__ import annotations

import bpy


@bpy.app.handlers.persistent  # type: ignore[misc]
def _on_load_post(*_args: object) -> None:
    _restore_state()


def _restore_state() -> None:
    """Restore GitHub auth state and trigger git status refresh."""
    from ..infrastructure.auth_store import AuthStore

    # Restore GitHub credentials from stored token
    try:
        auth = AuthStore()
        if auth.has_token("github.com"):
            props = bpy.context.window_manager.gitblend  # type: ignore[attr-defined]
            props.github_authenticated = True
            username = auth.load_meta("github.com", "username")
            if username:
                props.github_username = username
    except Exception:
        pass

    # Auto-refresh git status if a blend file is already open
    if bpy.data.filepath:
        def _refresh() -> None:
            try:
                bpy.ops.gitblend.refresh_status()
                bpy.ops.gitblend.refresh_branches()
            except Exception:
                pass
            return None  # unregister timer

        bpy.app.timers.register(_refresh, first_interval=0.2)


def register_handlers() -> None:
    if _on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load_post)


def unregister_handlers() -> None:
    if _on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_post)
