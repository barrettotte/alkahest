"""Run external tools through one validated, shell-free process boundary."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

_RUN = subprocess.run


def run_process(
    arguments: Sequence[str | os.PathLike[str]], **options: Any
) -> subprocess.CompletedProcess[Any]:
    """Resolve and execute one argument vector without invoking a shell."""
    if isinstance(arguments, (str, bytes)) or not arguments:
        raise ValueError("process arguments must be a nonempty sequence")
    command = [os.fspath(argument) for argument in arguments]
    if any(not isinstance(argument, str) for argument in command):
        raise ValueError("process arguments must resolve to text")
    if any(not argument or "\0" in argument for argument in command):
        raise ValueError("process arguments must be nonempty and contain no null bytes")
    if "shell" in options or "executable" in options:
        raise ValueError("the trusted process boundary does not accept shell or executable options")

    requested = Path(command[0])
    if requested.is_absolute():
        executable = requested
    elif requested.parent != Path("."):
        base = Path(options.get("cwd", Path.cwd()))
        executable = (base / requested).resolve()
    else:
        found = shutil.which(command[0])
        if found is None:
            raise FileNotFoundError(f"required executable was not found: {command[0]}")
        executable = Path(found).resolve()
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise PermissionError(f"process executable is not an executable file: {executable}")
    command[0] = str(executable)
    return _RUN(command, shell=False, **options)
