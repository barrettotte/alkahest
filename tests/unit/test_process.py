"""Unit tests for the validated external-process boundary."""

import sys

import pytest

from alkahest.process import run_process


def test_process_resolves_executable_and_never_uses_a_shell() -> None:
    result = run_process(
        [sys.executable, "-c", "print('safe process')"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == "safe process\n"


@pytest.mark.parametrize("arguments", ([], [""], ["value\0with-null"]))
def test_process_rejects_unsafe_argument_vectors(arguments) -> None:
    with pytest.raises((ValueError, FileNotFoundError)):
        run_process(arguments)


@pytest.mark.parametrize("option", ("shell", "executable"))
def test_process_rejects_execution_overrides(option) -> None:
    options = {option: True}
    with pytest.raises(ValueError, match="does not accept shell or executable"):
        run_process([sys.executable, "-V"], **options)
