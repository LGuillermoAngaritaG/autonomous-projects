"""Module 2: parse project.md YAML front-matter and merge it into the table."""

import os
import sys
from pathlib import Path

import yaml

DEFAULTS: dict = {
    "location": "",
    "priority": 5,
    "use_git": False,
    "state": "working",
    "max_ideas": 0,
    "max_reviews": 0,
    "max_to_do": 0,
    "idle_hours": None,
}
_INT_FIELDS = ("priority", "max_ideas", "max_reviews", "max_to_do")
_BOOL_FIELDS = ("use_git",)
_FLOAT_FIELDS = ("idle_hours",)


def parse_frontmatter(md_path: Path) -> dict:
    """Parse the leading ``---`` front-matter block of a markdown file.

    :param md_path: path to project.md.
    :returns: parsed mapping, or {} if file/block is missing or malformed.
    """
    if not md_path.is_file():
        return {}
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        # A typo in one project.md must not crash the whole picker (which would
        # brick the tick for every project). Skip it — defaults apply — and warn.
        print(f"warning: malformed frontmatter in {md_path}; ignoring", file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return default


def _coerce_float(value, default: float | None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        print(
            f"warning: non-numeric idle_hours {value!r}; falling back to run-level default",
            file=sys.stderr,
        )
        return default


def merge_frontmatter(projects_root: Path, table: list[dict]) -> list[dict]:
    """Merge front-matter fields (with defaults) into each row of the table.

    :param projects_root: directory holding project subdirectories.
    :param table: rows produced by compute_idle_times.
    :returns: the same rows, each enriched with front-matter fields.
    """
    for row in table:
        name = row["project_name"]
        md_path = projects_root / name / "project.md"
        # Distinguish "no project.md at all" from "present" so the picker can
        # pass over a half-set-up folder instead of treating defaulted
        # (state: working) values as a healthy project. select_project excludes
        # on this flag — the defaults below still fill keys so reads don't KeyError.
        row["has_project_md"] = md_path.is_file()
        if not row["has_project_md"]:
            print(f"warning: {name}: no project.md; skipping", file=sys.stderr)
        fm = parse_frontmatter(md_path)
        for key, default in DEFAULTS.items():
            value = fm.get(key, default)
            if key in _INT_FIELDS:
                value = _coerce_int(value, default)
            elif key in _BOOL_FIELDS:
                value = _coerce_bool(value, default)
            elif key in _FLOAT_FIELDS:
                value = _coerce_float(value, default)
            row[key] = value
        if row["has_project_md"]:
            if row["state"] not in ("working", "paused"):
                print(
                    f"warning: {name}: unrecognized state '{row['state']}'; skipping",
                    file=sys.stderr,
                )
            location = row["location"]
            if not location or not os.path.isdir(location):
                print(
                    f"warning: {name}: location '{location}' not found; skipping",
                    file=sys.stderr,
                )
    return table
