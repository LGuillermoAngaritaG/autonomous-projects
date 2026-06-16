"""Self-check for the picker gates. Run: python3 tests/test_project_picker.py

Covers the riskiest gates in project_picker.py with stdlib only:
PAUSED, in-progress resume, the all-three-AND cap gate, the idle check,
and priority sort + tie-break, plus the two SKIP failure modes.

# ponytail: git-commit-time branch of is_idle is left uncovered (use_git
# false everywhere, so git_last_commit_ts returns 0 and only file mtime
# drives the check). Add a temp-repo fixture if that branch grows riskier.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from project_picker import ProjectPicker


def _mkroot() -> Path:
    root = Path(tempfile.mkdtemp())
    (root / "projects" / "working").mkdir(parents=True)
    (root / "projects" / "paused").mkdir(parents=True)
    return root


def _add(root, name, fm_lines, *, idea=0, review=0, in_review=0,
         in_progress=0, paused=False) -> Path:
    """Write a project file + its task backlogs. Returns the project .md path."""
    wd = root / "projects" / "working"
    f = wd / f"{name}.md"
    f.write_text("---\n" + "\n".join(fm_lines) + "\n---\n# Goal\nx\n")
    if paused:
        (root / "projects" / "paused" / f"{name}.md").write_text("paused")
    tasks = root / "tasks" / name
    for sub in ("backlog", "in-review", "in-progress"):
        (tasks / sub).mkdir(parents=True, exist_ok=True)
    for i in range(idea):
        (tasks / "backlog" / f"idea_{i}.md").write_text("x")
    for i in range(review):
        (tasks / "backlog" / f"review_{i}.md").write_text("x")
    for i in range(in_review):
        (tasks / "in-review" / f"r_{i}.md").write_text("x")
    for i in range(in_progress):
        (tasks / "in-progress" / f"p_{i}.md").write_text("x")
    return f


def _idle_dir(age_seconds: float | None) -> str:
    """A temp dir whose newest file is `age_seconds` old. None => empty (mtime 0)."""
    d = Path(tempfile.mkdtemp())
    if age_seconds is not None:
        fp = d / "touched.txt"
        fp.write_text("x")
        ts = time.time() - age_seconds
        os.utime(fp, (ts, ts))
    return str(d)


def _stdout(picker) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        picker.pick()
    return buf.getvalue()


def _fm_by_stem(picker) -> dict:
    return {f.stem: fm for f, fm in picker.load_projects()}


CAPS = ["max_ideas: 2", "max_reviews: 2", "max_to_review: 2"]


def test_paused_gate() -> None:
    root = _mkroot()
    _add(root, "vis", CAPS)
    _add(root, "hid", CAPS, paused=True)
    p = ProjectPicker(root, idle_hours=0.0)
    assert {f.stem for f, _ in p.load_projects()} == {"vis"}, "paused not excluded"


def test_in_progress_resume_beats_priority() -> None:
    root = _mkroot()
    # higher priority + idle, but no in-progress task
    _add(root, "aaa_high", CAPS + ["priority: 1", f"location: {_idle_dir(None)}"])
    # lower priority, but has an in-progress task -> must win
    _add(root, "zzz_busy", CAPS + ["priority: 5",
         f"location: {_idle_dir(0)}"], in_progress=1)
    p = ProjectPicker(root, idle_hours=0.0)

    winner = p.in_progress_winner(p.load_projects())
    assert winner is not None and winner[0].stem == "zzz_busy", "wrong resume winner"
    assert _stdout(p) == "zzz_busy", "in-progress did not bypass caps/idle/priority"


def test_cap_gate_all_three_and() -> None:
    root = _mkroot()
    _add(root, "full3", CAPS, idea=2, review=2, in_review=2)
    _add(root, "full2", CAPS, idea=2, review=2, in_review=1)
    _add(root, "full2b", CAPS, idea=2, review=0, in_review=2)
    _add(root, "nocap", [], idea=9, review=9, in_review=9)  # no cap fields
    p = ProjectPicker(root, idle_hours=0.0)
    fm = _fm_by_stem(p)

    assert p.caps_reached("full3", fm["full3"]) is True, "all-three full not dropped"
    assert p.caps_reached("full2", fm["full2"]) is False, "two full wrongly dropped"
    assert p.caps_reached("full2b", fm["full2b"]) is False, "two full wrongly dropped"
    assert p.caps_reached("nocap", fm["nocap"]) is False, "missing cap fields => never full"


def test_idle_check_respects_recent_edit() -> None:
    root = _mkroot()
    # location touched 1h ago
    _add(root, "proj", CAPS + ["priority: 1",
         f"location: {_idle_dir(3600)}", "use_git: false"])
    fm = _fm_by_stem(ProjectPicker(root, 0))["proj"]

    now = time.time()
    # untouched for >= 0.5h -> idle
    assert ProjectPicker(root, idle_hours=0.5).is_idle(fm, now) is True
    # within a 2h window -> recently edited, not idle
    assert ProjectPicker(root, idle_hours=2.0).is_idle(fm, now) is False

    # empty location dir -> mtime 0 -> always idle
    root2 = _mkroot()
    _add(root2, "empty", CAPS + [f"location: {_idle_dir(None)}", "use_git: false"])
    fm2 = _fm_by_stem(ProjectPicker(root2, 0))["empty"]
    assert ProjectPicker(root2, idle_hours=1.0).is_idle(fm2, time.time()) is True


def test_priority_sort_and_tiebreak() -> None:
    # priority wins
    root = _mkroot()
    _add(root, "low", CAPS + ["priority: 5", f"location: {_idle_dir(None)}"])
    _add(root, "high", CAPS + ["priority: 1", f"location: {_idle_dir(None)}"])
    assert _stdout(ProjectPicker(root, idle_hours=0.01)) == "high", "priority not honored"

    # tie on priority -> oldest project-file mtime wins
    root = _mkroot()
    older = _add(root, "older", CAPS + ["priority: 2", f"location: {_idle_dir(None)}"])
    _add(root, "newer", CAPS + ["priority: 2", f"location: {_idle_dir(None)}"])
    old_ts = time.time() - 10_000
    os.utime(older, (old_ts, old_ts))
    assert _stdout(ProjectPicker(root, idle_hours=0.01)) == "older", "tie-break wrong"


def test_skip_no_md_files() -> None:
    root = _mkroot()  # projects/working/ exists but empty
    assert _stdout(ProjectPicker(root, idle_hours=0.0)).startswith("SKIP:")


def test_skip_when_all_capped_or_non_idle() -> None:
    # all capped
    root = _mkroot()
    _add(root, "capped", CAPS, idea=2, review=2, in_review=2)
    assert _stdout(ProjectPicker(root, idle_hours=0.0)).startswith("SKIP:")

    # all non-idle (freshly touched location, huge idle window)
    root = _mkroot()
    _add(root, "fresh", CAPS + [f"location: {_idle_dir(0)}", "use_git: false"])
    assert _stdout(ProjectPicker(root, idle_hours=1000.0)).startswith("SKIP:")


def main() -> None:
    test_paused_gate()
    test_in_progress_resume_beats_priority()
    test_cap_gate_all_three_and()
    test_idle_check_respects_recent_edit()
    test_priority_sort_and_tiebreak()
    test_skip_no_md_files()
    test_skip_when_all_capped_or_non_idle()
    print("ok")


if __name__ == "__main__":
    main()
