from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .config import Paths
from .fs import Job, file_mtime, is_file_not_dir, list_jobs
from .logs import read_entries


@dataclass(frozen=True)
class WarningItem:
    code: str
    message: str


def queue_dir_warnings(paths: Paths) -> List[WarningItem]:
    warnings: List[WarningItem] = []
    for label, path in {
        "pending": paths.pending,
        "in_progress": paths.in_progress,
        "failed": paths.failed,
        "done": paths.done,
    }.items():
        if is_file_not_dir(path):
            warnings.append(WarningItem(code="queue_dir_is_file", message=f"{label} queue is a file: {path}"))
    return warnings


def logs_stale_warnings(paths: Paths, max_age_s: int = 3600) -> List[WarningItem]:
    warnings: List[WarningItem] = []
    now = time.time()
    for label, log_path in {
        "worker": paths.worker_log,
        "reconcile": paths.reconcile_log,
        "enqueue": paths.enqueue_log,
    }.items():
        mtime = file_mtime(log_path)
        if mtime is None:
            continue
        if now - mtime > max_age_s:
            warnings.append(WarningItem(code="log_stale", message=f"{label} log is stale (>{max_age_s}s): {log_path}"))
    return warnings


def worker_lifecycle_warnings(paths: Paths) -> List[WarningItem]:
    # Detect a worker start without a matching end in recent logs.
    warnings: List[WarningItem] = []
    entries = read_entries(paths.worker_log, limit=200)
    last_start = None
    last_end = None
    for entry in entries:
        if entry.action == "worker_start":
            last_start = entry
        if entry.action == "worker_end":
            last_end = entry
    if last_start and (not last_end or last_end.timestamp < last_start.timestamp):
        warnings.append(WarningItem(code="worker_incomplete", message="last worker_start has no matching worker_end"))
    return warnings


def job_log_coverage_warnings(paths: Paths) -> List[WarningItem]:
    # Heuristic: warn if any job in pending/in_progress has no log entries.
    warnings: List[WarningItem] = []
    entries = read_entries(paths.worker_log, limit=500)
    seen_job_ids = {e.job_id for e in entries if e.job_id and e.job_id != "-"}

    for queue_name, queue_path in {
        "pending": paths.pending,
        "in_progress": paths.in_progress,
    }.items():
        for job in list_jobs(queue_path, queue_name):
            if job.job_id not in seen_job_ids:
                warnings.append(
                    WarningItem(
                        code="job_missing_log",
                        message=f"job {job.job_id} in {queue_name} has no worker log entries",
                    )
                )
    return warnings


def stuck_job_warnings(paths: Paths, max_age_s: int = 1800) -> List[WarningItem]:
    warnings: List[WarningItem] = []
    now = time.time()
    for job in list_jobs(paths.in_progress, "in_progress"):
        if now - job.mtime > max_age_s:
            warnings.append(
                WarningItem(
                    code="job_stuck",
                    message=f"job {job.job_id} in in_progress for >{max_age_s}s",
                )
            )
    return warnings


def collect_warnings(paths: Paths) -> List[WarningItem]:
    warnings: List[WarningItem] = []
    warnings.extend(queue_dir_warnings(paths))
    warnings.extend(worker_lifecycle_warnings(paths))
    warnings.extend(job_log_coverage_warnings(paths))
    warnings.extend(logs_stale_warnings(paths))
    warnings.extend(stuck_job_warnings(paths))
    return warnings
