"""Self-check over a tmp Projects/ fixture exercising the full pipeline."""

import time
from pathlib import Path

import pytest

from src.count_files import count_files
from src.idle_time import compute_idle_times
from src.parse_frontmatter import merge_frontmatter, parse_frontmatter
from src.select_project import format_selection, select_project

OLD = time.time() - 3600  # 1h ago: comfortably past the 15-min idle gate


def _make_project(root: Path, name: str, fm: str, files: dict[str, list[str]]):
    proj = root / name
    for stage in ("00_backlog", "00_tasks", "01_to-do", "02_in-progress", "03_to-review"):
        (proj / stage).mkdir(parents=True)
    (proj / "project.md").write_text(fm, encoding="utf-8")
    for stage, names in files.items():
        for fname in names:
            f = proj / stage / fname
            f.write_text("x", encoding="utf-8")


def _age(root: Path):
    """Backdate every file/dir so projects read as idle, except where overridden."""
    for p in root.rglob("*"):
        import os

        os.utime(p, (OLD, OLD))


def _build(tmp: Path) -> Path:
    root = tmp / "Projects"
    root.mkdir()
    # Eligible, high priority, work backlog present.
    _make_project(
        root, "Project-A",
        "---\nlocation: /a\npriority: 1\nuse_git: true\nstate: working\n"
        "max_ideas: 10\nmax_reviews: 5\nmax_to_do: 5\n---\n",
        {"00_backlog": ["idea_1.md", "review_1.md"], "00_tasks": ["t1.md"]},
    )
    # state: paused -> filtered out despite available work.
    _make_project(
        root, "Project-B",
        "---\npriority: 1\nstate: paused\nmax_ideas: 10\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    # Nothing left (counts meet caps, no tasks) -> filtered out.
    _make_project(
        root, "Project-C",
        "---\npriority: 1\nstate: working\nmax_ideas: 1\nmax_reviews: 0\nmax_to_do: 0\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    _age(root)
    return root


def test_selects_eligible_project(tmp_path):
    root = _build(tmp_path)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    chosen = select_project(table)
    assert chosen["project_name"] == "Project-A"
    assert chosen["ideas_left"] == 9
    assert chosen["reviews_left"] == 4
    assert chosen["to_do_left"] == 0  # 0 files in 01_to-do = nothing to work
    assert chosen["to_improve_left"] == 1


def test_to_do_left_counts_queued_tasks(tmp_path):
    # to_do_left = files actually in 01_to-do, regardless of max_to_do.
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "Queued",
        "---\npriority: 1\nstate: working\nmax_ideas: 0\nmax_to_do: 5\n---\n",
        {"01_to-do": ["a.md", "b.md"]},
    )
    _age(root)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    assert select_project(table)["to_do_left"] == 2


def test_idle_gate_excludes_fresh(tmp_path):
    root = _build(tmp_path)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    # Touch A's backlog so it reads as <15 min idle -> nothing qualifies.
    import os

    os.utime(root / "Project-A" / "00_backlog", None)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    chosen = select_project(table)
    assert chosen == {
        "project_name": "",
        "ideas_left": 0,
        "reviews_left": 0,
        "to_do_left": 0,
        "to_improve_left": 0,
    }


def test_tie_break_idle_desc(tmp_path):
    root = tmp_path / "Projects"
    root.mkdir()
    fm = "---\npriority: 1\nstate: working\nmax_ideas: 10\n---\n"
    _make_project(root, "Newer", fm, {"00_backlog": ["idea_1.md"]})
    _make_project(root, "Older", fm, {"00_backlog": ["idea_1.md"]})
    import os

    for p in (root / "Older").rglob("*"):
        os.utime(p, (OLD - 7200, OLD - 7200))  # idler
    for p in (root / "Newer").rglob("*"):
        os.utime(p, (OLD, OLD))
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    assert select_project(table)["project_name"] == "Older"


def test_min_idle_threshold_param(tmp_path):
    # A fresh project (idle ~0) is excluded at the default 15 but included at 0.
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "Fresh",
        "---\npriority: 1\nstate: working\nmax_ideas: 10\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )  # left at "now" -> idle < 15
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    assert select_project(table)["project_name"] == ""
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    assert select_project(table, min_idle=0)["project_name"] == "Fresh"


def test_parse_frontmatter_missing(tmp_path):
    assert parse_frontmatter(tmp_path / "nope.md") == {}


def test_parse_frontmatter_malformed_does_not_raise(tmp_path):
    # A typo'd project.md must yield {} (defaults), never crash the picker.
    bad = tmp_path / "project.md"
    bad.write_text("---\npriority: 1\nstate: working: oops\n---\n", encoding="utf-8")
    assert parse_frontmatter(bad) == {}


def test_select_survives_malformed_project(tmp_path):
    # One malformed project must not stop a valid sibling from being picked.
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(root, "Good", "---\npriority: 1\nstate: working\nmax_ideas: 5\n---\n",
                  {"00_backlog": ["idea_1.md"]})
    _make_project(root, "Broken", "---\nstate: working: nope\n: : :\n---\n", {})
    _age(root)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    assert select_project(table, min_idle=0)["project_name"] == "Good"


def test_version_flag_exits_zero(capsys):
    import tomllib
    from main import main

    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    expected = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert expected in capsys.readouterr().out


def test_format_block(tmp_path):
    block = format_selection(
        {"project_name": "X", "ideas_left": 1, "reviews_left": 2,
         "to_do_left": 3, "to_improve_left": 4}
    )
    assert block == (
        'project_name: "X"\nideas_left: 1\nreviews_left: 2\n'
        "to_do_left: 3\nto_improve_left: 4"
    )
