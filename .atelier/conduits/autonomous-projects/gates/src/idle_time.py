"""Module 1: compute idle_time (minutes) per project from stage-folder mtimes."""

import time
from pathlib import Path

STAGE_FOLDERS = ("00_backlog", "01_to-do", "02_in-progress", "03_to-review")


def newest_mtime(path: Path) -> float:
    """Newest mtime of `path` and everything under it; 0.0 if missing/empty.

    :param path: directory to scan.
    :returns: the largest mtime found, or 0.0.
    """
    if not path.exists():
        return 0.0
    newest = path.stat().st_mtime
    for child in path.rglob("*"):
        newest = max(newest, child.stat().st_mtime)
    return newest


def compute_idle_times(projects_root: Path, now: float | None = None) -> list[dict]:
    """Build the base table: one row per project with its idle_time in minutes.

    :param projects_root: directory holding project subdirectories.
    :param now: reference epoch seconds (defaults to time.time()).
    :returns: rows of {"project_name": str, "idle_time": float}.
    """
    now = time.time() if now is None else now
    rows: list[dict] = []
    for project in sorted(p for p in projects_root.iterdir() if p.is_dir()):
        last_touched = max(
            (newest_mtime(project / stage) for stage in STAGE_FOLDERS),
            default=0.0,
        )
        idle_minutes = (now - last_touched) / 60.0
        rows.append({"project_name": project.name, "idle_time": idle_minutes})
    return rows
