"""Run external tools through one validated, shell-free process boundary."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

# Invoke subprocesses only after the public boundary validates the executable.
_RUN = subprocess.run


def validated_command(arguments: Sequence[str | os.PathLike[str]]) -> list[str]:
    """Convert and validate an external command argument vector."""
    if isinstance(arguments, (str, bytes)) or not arguments:
        raise ValueError("process arguments must be a nonempty sequence")

    command = [os.fspath(argument) for argument in arguments]
    if any(not argument or "\0" in argument for argument in command):
        raise ValueError("process arguments must be nonempty and contain no null bytes")
    return command


def resolve_executable(command: str, cwd: str | os.PathLike[str] | None) -> Path:
    """Resolve one executable name and require an executable file."""
    requested = Path(command)
    if requested.is_absolute():
        executable = requested
    elif requested.parent != Path("."):
        base = Path.cwd() if cwd is None else Path(cwd)
        executable = (base / requested).resolve()
    else:
        found = shutil.which(command)
        if found is None:
            raise FileNotFoundError(f"required executable was not found: {command}")
        executable = Path(found).resolve()

    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise PermissionError(f"process executable is not an executable file: {executable}")
    return executable


def run_process(
    arguments: Sequence[str | os.PathLike[str]],
    *,
    cwd: str | os.PathLike[str] | None = None,
    check: bool = False,
    capture_output: bool = False,
    text: bool = True,
    stdout: int | None = None,
    stderr: int | None = None,
    encoding: str | None = None,
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
    **unsupported: object,
) -> subprocess.CompletedProcess[str]:
    """Resolve and execute one argument vector without invoking a shell."""
    if unsupported:
        raise ValueError("the trusted process boundary does not accept shell or executable options")
    if not text:
        raise ValueError("the trusted process boundary supports text output only")

    command = validated_command(arguments)
    command[0] = str(resolve_executable(command[0], cwd))
    return _RUN(
        command,
        cwd=cwd,
        check=check,
        capture_output=capture_output,
        text=True,
        stdout=stdout,
        stderr=stderr,
        encoding=encoding,
        timeout=timeout,
        env=env,
        shell=False,
    )
