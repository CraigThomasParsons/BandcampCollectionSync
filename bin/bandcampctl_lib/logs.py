from __future__ import annotations

import time
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional


@dataclass(frozen=True)
class LogEntry:
    timestamp: str
    action: str
    job_id: str
    detail: str
    raw: str


_LOG_RE = re.compile(
    r"^(?P<ts>\S+)\s+action=(?P<action>\S+)\s+job_id=(?P<job_id>\S+)\s+detail=\"(?P<detail>.*)\"$"
)


def parse_line(line: str) -> Optional[LogEntry]:
    # Expected format: ISO action=... job_id=... detail="..."
    match = _LOG_RE.match(line.strip())
    if not match:
        return None
    return LogEntry(
        timestamp=match.group("ts"),
        action=match.group("action"),
        job_id=match.group("job_id"),
        detail=match.group("detail"),
        raw=line.rstrip("\n"),
    )


def read_entries(path: Path, limit: int = 200) -> List[LogEntry]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []
    entries: List[LogEntry] = []
    for line in lines[-limit:]:
        entry = parse_line(line)
        if entry:
            entries.append(entry)
    return entries


def tail_lines(path: Path, limit: int = 50) -> List[str]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []
    return lines[-limit:]


def follow(path: Path, sleep_s: float = 0.5) -> Iterator[str]:
    # Simple follow generator (tail -f style).
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8", errors="replace") as handle:
        handle.seek(0, 2)
        while True:
            line = handle.readline()
            if not line:
                time.sleep(sleep_s)
                continue
            yield line.rstrip("\n")


def most_recent_entry(paths: Iterable[Path]) -> Optional[LogEntry]:
    latest: Optional[LogEntry] = None
    for path in paths:
        entries = read_entries(path, limit=50)
        if not entries:
            continue
        candidate = entries[-1]
        if not latest or candidate.timestamp > latest.timestamp:
            latest = candidate
    return latest
