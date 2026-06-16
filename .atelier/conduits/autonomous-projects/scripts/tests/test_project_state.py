"""Self-check for the gate logic. Run: python3 tests/test_project_state.py"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from project_state import ProjectState


def _setup(fm_lines, idea, review, in_review, todo, in_progress) -> ProjectState:
    root = Path(tempfile.mkdtemp())
    name = "demo"
    wd = root / "projects" / "working"
    wd.mkdir(parents=True)
    body = "---\n" + "\n".join(fm_lines) + "\n---\n# Goal\nx\n"
    (wd / f"{name}.md").write_text(body)
    tasks = root / "tasks" / name
    for sub in ("backlog", "in-review", "to-do", "in-progress"):
        (tasks / sub).mkdir(parents=True)
    for i in range(idea):
        (tasks / "backlog" / f"idea_{i}.md").write_text("x")
    for i in range(review):
        (tasks / "backlog" / f"review_{i}.md").write_text("x")
    for i in range(in_review):
        (tasks / "in-review" / f"r_{i}.md").write_text("x")
    for i in range(todo):
        (tasks / "to-do" / f"t_{i}.md").write_text("x")
    for i in range(in_progress):
        (tasks / "in-progress" / f"p_{i}.md").write_text("x")
    return ProjectState(root, name)


def main() -> None:
    caps = ["max_ideas: 2", "max_reviews: 2", "max_to_review: 2"]

    # under all caps with a to-do -> every gate open
    g = _setup(caps, 1, 1, 1, 1, 0).gates()
    assert g == {"generate_idea": True, "generate_review": True,
                 "work_on_to_do": True}, g

    # ideas at cap -> generate_idea false; reviews under -> true
    g = _setup(caps, 2, 0, 0, 1, 0).gates()
    assert g["generate_idea"] is False
    assert g["generate_review"] is True

    # no to-do/in-progress task -> work false even with empty review backlog
    g = _setup(caps, 0, 0, 0, 0, 0).gates()
    assert g["work_on_to_do"] is False

    # in-review full -> work false even with a to-do task
    g = _setup(caps, 0, 0, 2, 1, 0).gates()
    assert g["work_on_to_do"] is False

    # an in-progress task counts as work
    g = _setup(caps, 0, 0, 0, 0, 1).gates()
    assert g["work_on_to_do"] is True

    # missing caps -> generate gates stay open; in-review never full
    g = _setup([], 5, 5, 5, 1, 0).gates()
    assert g == {"generate_idea": True, "generate_review": True,
                 "work_on_to_do": True}, g

    # --- next_task_path ordering ---
    def add_task(state, name, priority, comment="", review=False) -> str:
        body = (f"---\npriority: {priority}\n---\n# Description\nx\n"
                f"# User comments\n{comment + chr(10) if comment else ''}")
        f = state.tasks / "to-do" / (("review_" if review else "") + name + ".md")
        f.write_text(body)
        return str(f.resolve())

    # empty to-do -> ""
    assert _setup(caps, 0, 0, 0, 0, 0).next_task_path() == ""

    # priority wins
    s = _setup(caps, 0, 0, 0, 0, 0)
    add_task(s, "low", priority=5)
    hi = add_task(s, "high", priority=1)
    assert s.next_task_path() == hi

    # same priority -> human-commented first
    s = _setup(caps, 0, 0, 0, 0, 0)
    add_task(s, "plain", priority=2)
    noted = add_task(s, "noted", priority=2, comment="do X first")
    assert s.next_task_path() == noted

    # same priority + comment status -> review_ first
    s = _setup(caps, 0, 0, 0, 0, 0)
    add_task(s, "task", priority=2)
    rev = add_task(s, "thing", priority=2, review=True)
    assert s.next_task_path() == rev

    print("ok")


if __name__ == "__main__":
    main()
