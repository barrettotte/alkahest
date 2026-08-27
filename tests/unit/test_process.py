"""Unit tests for the validated external-process boundary."""

import sys
from collections.abc import Sequence
from typing import Protocol, cast

import pytest

from alkahest.process import run_process


class UnsafeRunner(Protocol):
    """Call shape used to exercise rejected keyword options."""

    def __call__(self, arguments: Sequence[str], **options: object) -> object:
        """Pass deliberately unsupported process options."""
        ...


def test_process_resolves_executable_and_never_uses_a_shell() -> None:
    """Resolve a command and capture its text without a shell."""
    result = run_process(
        [sys.executable, "-c", "print('safe process')"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == "safe process\n"


@pytest.mark.parametrize("arguments", ([], [""], ["value\0with-null"]))
def test_process_rejects_unsafe_argument_vectors(arguments: list[str]) -> None:
    """Reject empty and null-containing argument vectors."""
    with pytest.raises((ValueError, FileNotFoundError)):
        run_process(arguments)


@pytest.mark.parametrize("option", ("shell", "executable"))
def test_process_rejects_execution_overrides(option: str) -> None:
    """Reject attempts to override process execution safety."""
    unsafe_run = cast(UnsafeRunner, run_process)
    with pytest.raises(ValueError, match="does not accept shell or executable"):
        unsafe_run([sys.executable, "-V"], **{option: True})
