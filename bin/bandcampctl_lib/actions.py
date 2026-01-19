from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
import os

from datetime import datetime

from .config import Paths


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int


def _run(cmd: List[str]) -> ActionResult:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return ActionResult(ok=proc.returncode == 0, stdout=proc.stdout.strip(), stderr=proc.stderr.strip(), returncode=proc.returncode)


def run_reconcile(paths: Paths) -> ActionResult:
    return _run([str(paths.stage / "bin" / "reconcile.sh")])


def run_worker_once(paths: Paths) -> ActionResult:
    return _run([str(paths.stage / "bin" / "worker.sh")])


def run_scaffold(paths: Paths) -> ActionResult:
    return _run([str(paths.base / "scaffold.sh")])


def ensure_exec_permissions(paths: Paths) -> List[Path]:
    # Apply +x to all *.sh scripts in the repo and the bandcampctl entrypoint.
    updated: List[Path] = []
    root = paths.base
    candidates: List[Path] = list(root.rglob("*.sh"))
    candidates.append(root / "bin" / "bandcampctl")

    for path in candidates:
        if not path.exists() or path.is_dir():
            continue
        try:
            mode = path.stat().st_mode
            new_mode = mode | 0o111
            if new_mode != mode:
                os.chmod(path, new_mode)
                updated.append(path)
        except OSError:
            continue
    return updated


def append_ctl_log(paths: Paths, action: str, job_id: str = "-", detail: str = "") -> None:
    paths.logs.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat()
    line = f'{timestamp} action={action} job_id={job_id} detail="{detail}"'
    paths.ctl_log.open("a", encoding="utf-8").write(line + "\n")
