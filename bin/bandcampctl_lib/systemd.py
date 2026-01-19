from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    stdout: str
    stderr: str


def run(cmd: List[str]) -> CommandResult:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return CommandResult(ok=proc.returncode == 0, stdout=proc.stdout.strip(), stderr=proc.stderr.strip())
    except FileNotFoundError:
        return CommandResult(ok=False, stdout="", stderr="systemctl not found")


def list_timers(name: str) -> CommandResult:
    return run(["systemctl", "--user", "list-timers", name, "--no-pager"])


def status_unit(name: str) -> CommandResult:
    return run(["systemctl", "--user", "status", name, "--no-pager"])
