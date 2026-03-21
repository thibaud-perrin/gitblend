"""Tests for the Result type."""

from __future__ import annotations

import pytest

from gitblend.domain.result import Err, Ok, err, is_err, is_ok, ok, unwrap


def test_ok_holds_value() -> None:
    r = ok(42)
    assert isinstance(r, Ok)
    assert r.value == 42


def test_err_holds_error() -> None:
    r = err("oops")
    assert isinstance(r, Err)
    assert r.error == "oops"


def test_is_ok_true_for_ok() -> None:
    assert is_ok(ok("hello"))


def test_is_ok_false_for_err() -> None:
    assert not is_ok(err("bad"))


def test_is_err_true_for_err() -> None:
    assert is_err(err("bad"))


def test_is_err_false_for_ok() -> None:
    assert not is_err(ok("good"))


def test_unwrap_returns_value() -> None:
    assert unwrap(ok("hello")) == "hello"


def test_unwrap_raises_on_err() -> None:
    from gitblend.domain.errors import GitBlendError, ErrorKind
    error = GitBlendError("boom", ErrorKind.INTERNAL)
    with pytest.raises(GitBlendError):
        unwrap(err(error))


def test_ok_is_frozen() -> None:
    r = ok(1)
    with pytest.raises(Exception):
        r.value = 2  # type: ignore[misc]


def test_err_is_frozen() -> None:
    r = err("x")
    with pytest.raises(Exception):
        r.error = "y"  # type: ignore[misc]
