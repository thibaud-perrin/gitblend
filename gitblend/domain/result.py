"""Result type for explicit error handling without exceptions.

Usage:
    result: Result[str, GitBlendError] = ok("hello")
    if is_ok(result):
        print(result.value)
    else:
        print(result.error)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Ok(Generic[T]):
    """Successful result carrying a value."""

    value: T


@dataclass(frozen=True)
class Err(Generic[E]):
    """Failed result carrying an error."""

    error: E


# Union type alias — use as Result[ValueType, ErrorType]
type Result[T, E] = Ok[T] | Err[E]


def ok(value: T) -> Ok[T]:
    """Construct a successful result."""
    return Ok(value)


def err(error: E) -> Err[E]:
    """Construct a failed result."""
    return Err(error)


def is_ok(result: Ok[T] | Err[E]) -> bool:
    """Return True if the result is Ok."""
    return isinstance(result, Ok)


def is_err(result: Ok[T] | Err[E]) -> bool:
    """Return True if the result is Err."""
    return isinstance(result, Err)


def unwrap(result: Ok[T] | Err[E]) -> T:
    """Return the value or raise the error as an exception."""
    if isinstance(result, Ok):
        return result.value
    raise result.error  # type: ignore[misc]
