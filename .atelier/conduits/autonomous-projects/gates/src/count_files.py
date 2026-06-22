"""Module 3: count files per stage folder and append columns to the table."""

from pathlib import Path


def _count(folder: Path, pattern: str = "*") -> int:
    """Count files (not subdirs) in `folder` matching `pattern`; 0 if missing."""
    if not folder.is_dir():
        return 0
    return sum(1 for p in folder.glob(pattern) if p.is_file())


def count_files(projects_root: Path, table: list[dict]) -> list[dict]:
    """Append per-stage file counts to each row.

    :param projects_root: directory holding project subdirectories.
    :param table: rows from earlier pipeline stages.
    :returns: the same rows, each with count_* columns added.
    """
    for row in table:
        project = projects_root / row["project_name"]
        backlog = project / "00_backlog"
        row["count_00_ideas"] = _count(backlog, "idea_*")
        row["count_00_reviews"] = _count(backlog, "review_*")
        row["count_00_tasks"] = _count(project / "00_tasks", "*.md")
        row["count_01_to_do"] = _count(project / "01_to-do", "*.md")
        row["count_02_in_progress"] = _count(project / "02_in-progress")
        row["count_03_to_review"] = _count(project / "03_to-review")
    return table
