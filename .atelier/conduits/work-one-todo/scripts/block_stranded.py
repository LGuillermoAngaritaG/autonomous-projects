"""Move a task stranded in 02_in-progress/ to 05_blocked/ with a note.

Success in work-one-todo moves a task to 03_to-review/, so any *.md still
sitting in 02_in-progress/ after the advance loop means the loop gave up: the
reviewer never returned DONE within the retry cap, or a crash/timeout/usage
throttle cut the run off. Left there, the task is silently retried every tick,
burning quota with no note for the human. This moves it out, out loud.

Stdout contract (always exit 0):
    blocked: <path>     a file was moved to 05_blocked/
    blocked: none       nothing was stranded
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path


def block_stranded(project_dir: str | Path) -> str | None:
    """Move the first *.md left in 02_in-progress/ to 05_blocked/ with a note.

    :param project_dir: project folder holding the numbered stage subfolders.
    :returns: destination path as a string, or None if nothing was stranded.
    """
    project = Path(project_dir)
    in_progress = project / "02_in-progress"
    try:
        stranded = sorted(p for p in in_progress.glob("*.md") if p.is_file())
    except OSError:
        return None
    if not stranded:
        return None

    src = stranded[0]
    blocked = project / "05_blocked"
    blocked.mkdir(parents=True, exist_ok=True)

    dest = blocked / src.name
    if dest.exists():  # don't clobber a task blocked on an earlier run
        i = 2
        while (blocked / f"{src.stem}.{i}{src.suffix}").exists():
            i += 1
        dest = blocked / f"{src.stem}.{i}{src.suffix}"

    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    note = (
        f"\n\n# Blocked\n\n"
        f"Auto-blocked {stamp}: the work-and-review loop ended without a DONE "
        f"verdict (retry cap hit, or the run was cut off). Needs a human.\n"
    )
    try:
        with src.open("a", encoding="utf-8") as fh:
            fh.write(note)
    except OSError:
        pass  # note is best-effort; still move it out of the retry path
    src.replace(dest)
    return str(dest)


def main() -> None:
    project_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    moved = block_stranded(project_dir)
    print(f"blocked: {moved if moved else 'none'}")


if __name__ == "__main__":
    main()
