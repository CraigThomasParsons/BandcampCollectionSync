from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    base: Path
    stage: Path
    inbox: Path
    logs: Path
    pending: Path
    in_progress: Path
    failed: Path
    done: Path
    worker_log: Path
    reconcile_log: Path
    enqueue_log: Path
    ctl_log: Path


def get_paths() -> Paths:
    home = Path.home()
    base = home / "BandcampSync"
    stage = base / "Sync"
    inbox = stage / "inbox"
    logs = stage / "logs"
    return Paths(
        base=base,
        stage=stage,
        inbox=inbox,
        logs=logs,
        pending=inbox / "pending",
        in_progress=inbox / "in_progress",
        failed=inbox / "failed",
        done=inbox / "done",
        worker_log=logs / "worker.log",
        reconcile_log=logs / "reconcile.log",
        enqueue_log=logs / "enqueue.log",
        ctl_log=logs / "ctl.log",
    )
