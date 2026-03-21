"""Background task execution for long-running git operations.

Runs callables in a thread and schedules the completion callback on
the main Blender thread via bpy.app.timers.
"""

from __future__ import annotations

import threading
from typing import Any, Callable

import bpy


def run_in_background(
    fn: Callable[[], Any],
    on_complete: Callable[[Any], None],
    on_error: Callable[[Exception], None] | None = None,
) -> None:
    """Run *fn* in a background thread.

    When done, schedules *on_complete(result)* on the main thread.
    If *fn* raises, schedules *on_error(exc)* if provided.

    Args:
        fn: The callable to run in the background (no arguments).
        on_complete: Called on the main thread with fn's return value.
        on_error: Called on the main thread if fn raises an exception.
    """
    result_holder: list[Any] = []
    error_holder: list[Exception] = []

    def worker() -> None:
        try:
            result_holder.append(fn())
        except Exception as exc:
            error_holder.append(exc)

    def check_done() -> float | None:
        if thread.is_alive():
            return 0.1  # re-check in 100ms
        if error_holder:
            if on_error:
                on_error(error_holder[0])
        elif result_holder:
            on_complete(result_holder[0])
        return None  # unregister timer

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    bpy.app.timers.register(check_done, first_interval=0.1)
