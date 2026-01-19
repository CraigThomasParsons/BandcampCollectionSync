from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class Job:
    job_id: str
    path: Path
    url: str
    mtime: float
    queue: str


def ensure_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def read_job_url(job_path: Path) -> str:
    try:
        line = job_path.read_text(encoding="utf-8").splitlines()[0].strip()
    except Exception:
        return ""

    if line.startswith("URL="):
        return line.split("=", 1)[1].strip()
    return line


def list_jobs(queue_path: Path, queue_name: str) -> List[Job]:
    jobs: List[Job] = []
    if not queue_path.exists() or not queue_path.is_dir():
        return jobs

    for job_path in sorted(queue_path.glob("*.job")):
        job_id = job_path.stem
        url = read_job_url(job_path)
        try:
            mtime = job_path.stat().st_mtime
        except OSError:
            mtime = 0.0
        jobs.append(Job(job_id=job_id, path=job_path, url=url, mtime=mtime, queue=queue_name))
    return jobs


def move_job(job: Job, dest_queue: Path) -> Path:
    dest_queue.mkdir(parents=True, exist_ok=True)
    dest_path = dest_queue / job.path.name
    return Path(shutil.move(str(job.path), str(dest_path)))


def read_tail(path: Path, lines: int = 50) -> List[str]:
    if not path.exists():
        return []
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    content = data.splitlines()
    return content[-lines:]


def file_mtime(path: Path) -> Optional[float]:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def is_file_not_dir(path: Path) -> bool:
    return path.exists() and path.is_file()


def read_job_contents(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
