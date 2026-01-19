from __future__ import annotations

import curses
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .actions import append_ctl_log, run_reconcile, run_worker_once
from .config import Paths, get_paths
from .diagnostics import collect_warnings
from .fs import Job, list_jobs, move_job, read_job_contents
from .logs import read_entries, tail_lines
from .systemd import list_timers, status_unit


@dataclass
class Selection:
    queue: str = "pending"
    index: int = 0


@dataclass
class UiState:
    view: str = "queue"
    selection: Selection = field(default_factory=Selection)
    log_name: str = "worker"
    message: str = ""


def _get_queue_jobs(paths: Paths, queue: str) -> List[Job]:
    if queue == "pending":
        return list_jobs(paths.pending, "pending")
    if queue == "in_progress":
        return list_jobs(paths.in_progress, "in_progress")
    if queue == "failed":
        return list_jobs(paths.failed, "failed")
    return list_jobs(paths.done, "done")


def _draw_header(stdscr: "curses._CursesWindow", title: str, width: int) -> None:
    stdscr.addstr(0, 0, title.ljust(width)[:width], curses.A_REVERSE)


def _draw_footer(stdscr: "curses._CursesWindow", text: str, y: int, width: int) -> None:
    stdscr.addstr(y, 0, text.ljust(width)[:width], curses.A_REVERSE)


def _clip(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def _selected_job(jobs: List[Job], selection: Selection) -> Optional[Job]:
    if not jobs:
        return None
    idx = max(0, min(selection.index, len(jobs) - 1))
    selection.index = idx
    return jobs[idx]


def _render_queue_view(stdscr: "curses._CursesWindow", paths: Paths, state: UiState) -> None:
    height, width = stdscr.getmaxyx()
    jobs = _get_queue_jobs(paths, state.selection.queue)
    pending = len(list_jobs(paths.pending, "pending"))
    in_progress = len(list_jobs(paths.in_progress, "in_progress"))
    failed = len(list_jobs(paths.failed, "failed"))
    done = len(list_jobs(paths.done, "done"))

    header = (
        f"BandcampSync TUI — Queue View | pending={pending} in_progress={in_progress} "
        f"failed={failed} done={done}"
    )
    _draw_header(stdscr, header, width)

    left_width = max(30, width // 2)
    stdscr.addstr(2, 0, f"Queue: {state.selection.queue}")
    for i, job in enumerate(jobs[: height - 6]):
        prefix = "> " if i == state.selection.index else "  "
        line = f"{prefix}{job.job_id} {job.url}"
        stdscr.addstr(3 + i, 0, _clip(line, left_width - 1))

    selected = _selected_job(jobs, state.selection)
    detail_x = left_width + 1
    if selected:
        stdscr.addstr(2, detail_x, f"Job: {selected.job_id}")
        stdscr.addstr(3, detail_x, f"Queue: {selected.queue}")
        stdscr.addstr(4, detail_x, _clip(f"URL: {selected.url}", width - detail_x - 1))
        content = read_job_contents(selected.path)
        stdscr.addstr(6, detail_x, "Contents:")
        for i, line in enumerate(content.splitlines()[:4]):
            stdscr.addstr(7 + i, detail_x, _clip(line, width - detail_x - 1))

        stdscr.addstr(12, detail_x, "History:")
        entries = read_entries(paths.worker_log, limit=200)
        history = [e.raw for e in entries if e.job_id == selected.job_id][-5:]
        for i, line in enumerate(history):
            stdscr.addstr(13 + i, detail_x, _clip(line, width - detail_x - 1))

    footer = "Keys: 1=Queue 2=Logs 3=Actions 4=Dashboard | p/i/f/d switch queue | ↑/↓ select | q=quit"
    _draw_footer(stdscr, footer, height - 1, width)


def _render_logs_view(stdscr: "curses._CursesWindow", paths: Paths, state: UiState) -> None:
    height, width = stdscr.getmaxyx()
    _draw_header(stdscr, f"BandcampSync TUI — Log View ({state.log_name})", width)

    log_path = {
        "worker": paths.worker_log,
        "reconcile": paths.reconcile_log,
        "enqueue": paths.enqueue_log,
        "ctl": paths.ctl_log,
    }.get(state.log_name, paths.worker_log)

    lines = tail_lines(log_path, limit=height - 4)
    for i, line in enumerate(lines):
        stdscr.addstr(2 + i, 0, _clip(line, width - 1))

    footer = "Keys: 1=Queue 2=Logs 3=Actions 4=Dashboard | w/r/e/c choose log | q=quit"
    _draw_footer(stdscr, footer, height - 1, width)


def _render_actions_view(stdscr: "curses._CursesWindow", paths: Paths, state: UiState) -> None:
    height, width = stdscr.getmaxyx()
    _draw_header(stdscr, "BandcampSync TUI — Actions (explicit, confirmed)", width)

    stdscr.addstr(2, 0, "Actions:")
    stdscr.addstr(3, 2, "r  Run reconcile once")
    stdscr.addstr(4, 2, "w  Process ONE job (worker.sh)")
    stdscr.addstr(5, 2, "t  Retry failed job (selected job in failed queue)")
    stdscr.addstr(6, 2, "e  Requeue job (selected job in in_progress/failed)")

    if state.message:
        stdscr.addstr(8, 0, _clip(f"Last action: {state.message}", width - 1))

    stdscr.addstr(10, 0, "Selection:")
    jobs = _get_queue_jobs(paths, state.selection.queue)
    selected = _selected_job(jobs, state.selection)
    if selected:
        stdscr.addstr(11, 2, _clip(f"{selected.queue} {selected.job_id} {selected.url}", width - 3))
    else:
        stdscr.addstr(11, 2, "(no job selected)")

    footer = "Keys: 1=Queue 2=Logs 3=Actions 4=Dashboard | confirm with y/n | q=quit"
    _draw_footer(stdscr, footer, height - 1, width)


def _render_dashboard_view(stdscr: "curses._CursesWindow", paths: Paths, state: UiState) -> None:
    height, width = stdscr.getmaxyx()
    _draw_header(stdscr, "BandcampSync Dashboard (read-only by default)", width)

    pending = len(list_jobs(paths.pending, "pending"))
    in_progress = len(list_jobs(paths.in_progress, "in_progress"))
    failed = len(list_jobs(paths.failed, "failed"))
    done = len(list_jobs(paths.done, "done"))

    stdscr.addstr(2, 0, f"Queues: pending={pending} in_progress={in_progress} failed={failed} done={done}")

    timer = list_timers("bandcamp-sync-reconcile.timer")
    stdscr.addstr(4, 0, "Reconcile timer:")
    for i, line in enumerate(timer.stdout.splitlines()[:3] if timer.ok else [timer.stderr]):
        stdscr.addstr(5 + i, 2, _clip(line, width - 3))

    path_unit = status_unit("bandcamp-sync-worker.path")
    stdscr.addstr(9, 0, "Worker path unit:")
    for i, line in enumerate(path_unit.stdout.splitlines()[:3] if path_unit.ok else [path_unit.stderr]):
        stdscr.addstr(10 + i, 2, _clip(line, width - 3))

    entries = read_entries(paths.worker_log, limit=200)
    last_done = next((e for e in reversed(entries) if e.action == "job_transition" and "done" in e.detail), None)
    last_done_line = last_done.raw if last_done else "(no successful downloads yet)"
    stdscr.addstr(14, 0, _clip(f"Last successful download: {last_done_line}", width - 1))

    warnings = collect_warnings(paths)
    stdscr.addstr(16, 0, "Warnings:")
    if warnings:
        for i, warning in enumerate(warnings[:4]):
            stdscr.addstr(17 + i, 2, _clip(f"{warning.code}: {warning.message}", width - 3))
    else:
        stdscr.addstr(17, 2, "(none)")

    recent = tail_lines(paths.worker_log, limit=5)
    stdscr.addstr(22, 0, "Recent activity:")
    for i, line in enumerate(recent):
        stdscr.addstr(23 + i, 2, _clip(line, width - 3))

    footer = "Keys: 1=Queue 2=Logs 3=Actions 4=Dashboard | a=actions (confirm) | q=quit"
    _draw_footer(stdscr, footer, height - 1, width)


def _confirm(stdscr: "curses._CursesWindow", prompt: str) -> bool:
    height, width = stdscr.getmaxyx()
    stdscr.addstr(height - 2, 0, _clip(prompt + " (y/n)", width - 1))
    stdscr.refresh()
    while True:
        ch = stdscr.getch()
        if ch in (ord("y"), ord("Y")):
            return True
        if ch in (ord("n"), ord("N")):
            return False


def _handle_action(stdscr: "curses._CursesWindow", paths: Paths, state: UiState, action: str) -> None:
    if action == "reconcile":
        if _confirm(stdscr, "Run reconcile now?"):
            append_ctl_log(paths, "ctl_reconcile", "-", "manual reconcile triggered")
            result = run_reconcile(paths)
            state.message = f"reconcile rc={result.returncode}"
    elif action == "worker":
        if _confirm(stdscr, "Process ONE job now?"):
            append_ctl_log(paths, "ctl_worker", "-", "manual worker triggered")
            result = run_worker_once(paths)
            state.message = f"worker rc={result.returncode}"
    elif action == "retry_failed":
        jobs = _get_queue_jobs(paths, state.selection.queue)
        selected = _selected_job(jobs, state.selection)
        if not selected or selected.queue != "failed":
            state.message = "select a failed job first"
            return
        if _confirm(stdscr, f"Retry failed job {selected.job_id}?"):
            move_job(selected, paths.pending)
            append_ctl_log(paths, "ctl_retry", selected.job_id, "failed->pending")
            state.message = f"requeued {selected.job_id}"
    elif action == "requeue":
        jobs = _get_queue_jobs(paths, state.selection.queue)
        selected = _selected_job(jobs, state.selection)
        if not selected or selected.queue not in {"failed", "in_progress"}:
            state.message = "select failed/in_progress job first"
            return
        if _confirm(stdscr, f"Requeue job {selected.job_id} to pending?"):
            move_job(selected, paths.pending)
            append_ctl_log(paths, "ctl_requeue", selected.job_id, f"{selected.queue}->pending")
            state.message = f"requeued {selected.job_id}"


def _handle_key(stdscr: "curses._CursesWindow", paths: Paths, state: UiState, ch: int, dashboard_only: bool) -> bool:
    if ch in (ord("q"), ord("Q")):
        return True

    if ch == ord("1"):
        state.view = "queue"
    elif ch == ord("2"):
        state.view = "logs"
    elif ch == ord("3") and not dashboard_only:
        state.view = "actions"
    elif ch == ord("4"):
        state.view = "dashboard"

    if state.view == "queue":
        if ch in (ord("p"), ord("P")):
            state.selection.queue = "pending"
            state.selection.index = 0
        elif ch in (ord("i"), ord("I")):
            state.selection.queue = "in_progress"
            state.selection.index = 0
        elif ch in (ord("f"), ord("F")):
            state.selection.queue = "failed"
            state.selection.index = 0
        elif ch in (ord("d"), ord("D")):
            state.selection.queue = "done"
            state.selection.index = 0
        elif ch == curses.KEY_UP:
            state.selection.index = max(0, state.selection.index - 1)
        elif ch == curses.KEY_DOWN:
            state.selection.index += 1

    if state.view == "logs":
        if ch in (ord("w"), ord("W")):
            state.log_name = "worker"
        elif ch in (ord("r"), ord("R")):
            state.log_name = "reconcile"
        elif ch in (ord("e"), ord("E")):
            state.log_name = "enqueue"
        elif ch in (ord("c"), ord("C")):
            state.log_name = "ctl"

    if state.view == "actions" and not dashboard_only:
        if ch in (ord("r"), ord("R")):
            _handle_action(stdscr, paths, state, "reconcile")
        elif ch in (ord("w"), ord("W")):
            _handle_action(stdscr, paths, state, "worker")
        elif ch in (ord("t"), ord("T")):
            _handle_action(stdscr, paths, state, "retry_failed")
        elif ch in (ord("e"), ord("E")):
            _handle_action(stdscr, paths, state, "requeue")

    if state.view == "dashboard" and ch in (ord("a"), ord("A")) and not dashboard_only:
        state.view = "actions"

    return False


def run_tui(dashboard_only: bool = False) -> None:
    paths = get_paths()

    def _loop(stdscr: "curses._CursesWindow") -> None:
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(200)
        state = UiState(view="dashboard" if dashboard_only else "queue")

        while True:
            stdscr.erase()
            if state.view == "queue":
                _render_queue_view(stdscr, paths, state)
            elif state.view == "logs":
                _render_logs_view(stdscr, paths, state)
            elif state.view == "actions":
                _render_actions_view(stdscr, paths, state)
            else:
                _render_dashboard_view(stdscr, paths, state)

            stdscr.refresh()
            ch = stdscr.getch()
            if ch != -1:
                if _handle_key(stdscr, paths, state, ch, dashboard_only):
                    break
            time.sleep(0.1)

    curses.wrapper(_loop)
