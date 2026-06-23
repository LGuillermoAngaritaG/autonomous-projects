"""Move the reviewer-approved task in 02_in-progress/ to 03_to-review/.

The builder leaves its finished card in 02_in-progress/; only a DONE verdict
from the independent reviewer should promote it. This runs on that DONE verdict
and moves the single *.md there to 03_to-review/ for the human. Keeping the
move out of the builder's own "I think I'm done" step is what lets a NOT_DONE
verdict retry the card (it's still in 02_in-progress/) and lets block_stranded
park it if the loop gives up.

Stdout contract (always exit 0):
    promoted: <path>    a file was moved to 03_to-review/
    promoted: none      nothing was in 02_in-progress/
"""

from __future__ import annotations

import sys
from pathlib import Path


def promote_reviewed(project_dir: str | Path) -> str | None:
    """Move the first *.md in 02_in-progress/ to 03_to-review/.

    :param project_dir: project folder holding the numbered stage subfolders.
    :returns: destination path as a string, or None if nothing was in-progress.
    """
    project = Path(project_dir)
    in_progress = project / "02_in-progress"
    try:
        cards = sorted(p for p in in_progress.glob("*.md") if p.is_file())
    except OSError:
        return None
    if not cards:
        return None

    src = cards[0]
    to_review = project / "03_to-review"
    to_review.mkdir(parents=True, exist_ok=True)

    dest = to_review / src.name
    if dest.exists():  # don't clobber a card already awaiting human review
        i = 2
        while (to_review / f"{src.stem}.{i}{src.suffix}").exists():
            i += 1
        dest = to_review / f"{src.stem}.{i}{src.suffix}"

    src.replace(dest)
    return str(dest)


def main() -> None:
    project_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    moved = promote_reviewed(project_dir)
    print(f"promoted: {moved if moved else 'none'}")


if __name__ == "__main__":
    main()
