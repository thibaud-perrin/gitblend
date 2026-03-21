"""Blender operator reporting and user-facing notifications."""

from __future__ import annotations

import bpy

from ..domain.enums import ErrorKind
from ..domain.errors import GitBlendError


def report_info(operator: bpy.types.Operator, message: str) -> None:
    operator.report({"INFO"}, message)


def report_warning(operator: bpy.types.Operator, message: str) -> None:
    operator.report({"WARNING"}, message)


def report_error(operator: bpy.types.Operator, error: GitBlendError) -> None:
    """Report a GitBlendError to the Blender operator info area."""
    level = _error_kind_to_level(error.kind)
    operator.report({level}, error.message)
    if error.detail:
        operator.report({"WARNING"}, error.detail)
    if error.suggestion:
        operator.report({"INFO"}, f"Tip: {error.suggestion}")


def popup_message(message: str, title: str = "gitblend", icon: str = "INFO") -> None:
    """Show a popup message in Blender."""
    def draw(self: bpy.types.Menu, context: bpy.types.Context) -> None:
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def _error_kind_to_level(kind: ErrorKind) -> str:
    match kind:
        case ErrorKind.USER | ErrorKind.CONFIG:
            return "WARNING"
        case ErrorKind.AUTH | ErrorKind.NETWORK | ErrorKind.REPO:
            return "ERROR"
        case _:
            return "ERROR"
