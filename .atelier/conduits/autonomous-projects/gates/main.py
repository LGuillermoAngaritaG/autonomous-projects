"""CLI entry point: recommend the next project to work on under a Projects/ root."""

import argparse
import importlib.metadata
import sys
import tomllib
from pathlib import Path

from src.count_files import count_files
from src.idle_time import compute_idle_times
from src.parse_frontmatter import merge_frontmatter
from src.select_project import MIN_IDLE_MINUTES, format_selection, select_project


def _resolve_version() -> str:
    try:
        return importlib.metadata.version("gates")
    except importlib.metadata.PackageNotFoundError:
        pyproject = Path(__file__).parent / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        return data["project"]["version"]


def main(argv: list[str] | None = None) -> int:
    """Run the four-stage pipeline and print the recommended project.

    :param argv: CLI args (defaults to sys.argv[1:]).
    :returns: process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {_resolve_version()}")
    parser.add_argument("projects_root", help="path to the Projects/ root directory")
    parser.add_argument(
        "--min-idle-minutes", type=float, default=MIN_IDLE_MINUTES,
        help=f"minimum idle minutes to qualify (default {MIN_IDLE_MINUTES})",
    )
    args = parser.parse_args(argv)

    root = Path(args.projects_root).expanduser()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2

    table = compute_idle_times(root)
    table = merge_frontmatter(root, table)
    table = count_files(root, table)
    print(format_selection(select_project(table, min_idle=args.min_idle_minutes)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
