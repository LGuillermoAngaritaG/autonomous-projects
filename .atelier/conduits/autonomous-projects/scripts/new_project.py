"""One-command project scaffolder.

Usage:
    uv run python new_project.py <name> --location <path>

Creates projects/<name>/ with project.md (from the template, location: rewritten)
and all 7 stage folders. Atomic: builds in a temp dir, renames on success.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path


SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

STAGE_FOLDERS = [
    "00_abandoned",
    "00_backlog",
    "00_tasks",
    "01_to-do",
    "02_in-progress",
    "03_to-review",
    "04_done",
]


def validate_slug(name: str) -> bool:
    """Return True iff *name* is valid lowercase kebab-case."""
    return bool(SLUG_RE.fullmatch(name))


def create_project(
    name: str,
    location: str,
    projects_root: Path,
    template_path: Path,
) -> Path:
    """Create a new project under *projects_root*.

    Validates inputs first, then builds atomically in a temp dir.

    Returns the created project path.

    Raises:
        ValueError: invalid slug.
        FileExistsError: project directory already exists.
        OSError: *location* is not a writable directory, or template/projects_root
            is missing.
    """
    if not validate_slug(name):
        raise ValueError(
            f"Invalid project name {name!r}: must be lowercase kebab-case "
            "(letters, digits, hyphens only; no leading/trailing hyphens)."
        )

    target = projects_root / name
    if target.exists():
        raise FileExistsError(f"Project {name!r} already exists at {target}.")

    loc = Path(location)
    if not loc.exists() or not os.access(str(loc), os.W_OK):
        raise OSError(
            f"--location {location!r} does not exist or is not writable."
        )

    if not template_path.exists():
        raise OSError(f"Template not found at {template_path}.")

    projects_root.mkdir(parents=True, exist_ok=True)

    tmp_dir = Path(tempfile.mkdtemp(dir=projects_root))
    try:
        for folder in STAGE_FOLDERS:
            (tmp_dir / folder).mkdir(parents=True)

        tmpl = template_path.read_text(encoding="utf-8")
        project_md = re.sub(
            r"^location:.*", f"location: {location}", tmpl, count=1,
            flags=re.MULTILINE,
        )
        (tmp_dir / "project.md").write_text(project_md, encoding="utf-8")

        os.rename(str(tmp_dir), str(target))
    except BaseException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise

    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a new autonomous project."
    )
    parser.add_argument("name", help="Project name (lowercase kebab-case)")
    parser.add_argument(
        "--location",
        required=True,
        help="Path to the codebase the project will work on (must exist, writable)",
    )
    args = parser.parse_args(argv)

    script_dir = Path(__file__).resolve().parent
    template_path = script_dir.parent / "references" / "project_template.md"
    projects_root = Path.cwd() / "projects"

    try:
        path = create_project(args.name, args.location, projects_root, template_path)
    except (ValueError, FileExistsError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Created project {args.name!r} at {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
