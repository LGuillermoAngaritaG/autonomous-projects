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
    # select_project now requires location to point at a real dir. Give every
    # fixture a valid one (the project folder, which exists) unless the fm
    # already sets location explicitly (negative tests rely on that).
    if "location:" not in fm and fm.startswith("---\n"):
        fm = fm.replace("---\n", f"---\nlocation: {proj}\n", 1)
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
        "---\npriority: 1\nuse_git: true\nstate: working\n"
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


def test_non_md_files_dont_count_as_work(tmp_path):
    # Picker must count only *.md, matching the worker. A stray non-.md file in
    # 01_to-do/ or 00_tasks/ must not report phantom work (or the work/improve
    # branch wakes every tick over an empty bucket, burning agent calls).
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "StrayFiles",
        "---\npriority: 1\nstate: working\nmax_ideas: 0\nmax_reviews: 0\nmax_to_do: 5\n---\n",
        {"01_to-do": ["notes.txt"], "00_tasks": ["scratch.log"]},
    )
    _age(root)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    row = next(r for r in table if r["project_name"] == "StrayFiles")
    assert row["count_01_to_do"] == 0
    assert row["count_00_tasks"] == 0
    # nothing left -> excluded
    assert select_project(table, min_idle=0)["project_name"] == ""


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
        "reason": "no work left",
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


def test_per_project_idle_wins(tmp_path):
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "HasOverride",
        "---\npriority: 1\nstate: working\nmax_ideas: 10\nidle_hours: 2\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    _make_project(
        root, "NoOverride",
        "---\npriority: 2\nstate: working\nmax_ideas: 10\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    _age(root)  # both ~1h idle
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    # NoOverride passes the global min_idle (15 min), HasOverride needs 120 min → excluded.
    chosen = select_project(table, min_idle=15)
    assert chosen["project_name"] == "NoOverride"


def test_per_project_idle_absent_falls_back(tmp_path):
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "NoKey",
        "---\npriority: 1\nstate: working\nmax_ideas: 10\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    _age(root)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    # No idle_hours key → uses global min_idle
    chosen = select_project(table, min_idle=9999)
    assert chosen["project_name"] == ""  # excluded by the huge global idle gate


def test_reason_selected(tmp_path):
    root = _build(tmp_path)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    chosen = select_project(table)
    assert chosen["reason"] == "selected"
    assert chosen["project_name"] == "Project-A"


def test_reason_no_projects_found(tmp_path):
    root = tmp_path / "Projects"
    root.mkdir()
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    chosen = select_project(table)
    assert chosen["reason"] == "no projects found"


def test_reason_all_paused(tmp_path):
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "PausedProj",
        "---\npriority: 1\nstate: paused\nmax_ideas: 10\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    _age(root)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    chosen = select_project(table)
    assert chosen["reason"] == "all paused"


def test_reason_none_idle_yet(tmp_path):
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "Fresh",
        "---\npriority: 1\nstate: working\nmax_ideas: 10\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    chosen = select_project(table)
    assert chosen["reason"] == "none idle yet"


def test_reason_no_work_left(tmp_path):
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "Done",
        "---\npriority: 1\nstate: working\nmax_ideas: 0\nmax_reviews: 0\nmax_to_do: 0\n---\n",
        {},
    )
    _age(root)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    chosen = select_project(table)
    assert chosen["reason"] == "no work left"


def test_format_reason_line():
    block = format_selection(
        {"project_name": "X", "ideas_left": 1, "reviews_left": 2,
         "to_do_left": 3, "to_improve_left": 4, "reason": "selected"}
    )
    assert block.endswith("\nreason: selected")


def test_format_reason_omitted_when_absent():
    block = format_selection(
        {"project_name": "X", "ideas_left": 1, "reviews_left": 2,
         "to_do_left": 3, "to_improve_left": 4}
    )
    assert "reason" not in block
    assert block == (
        'project_name: "X"\nideas_left: 1\nreviews_left: 2\n'
        "to_do_left: 3\nto_improve_left: 4"
    )


def test_per_project_idle_malformed_degrade(tmp_path):
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "BadVal",
        "---\npriority: 1\nstate: working\nmax_ideas: 10\nidle_hours: abc\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    _age(root)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    # idle_hours: abc → degraded to None → uses global min_idle → passes at 0
    chosen = select_project(table, min_idle=0)
    assert chosen["project_name"] == "BadVal"


def test_coerce_float_none_returns_none():
    from src.parse_frontmatter import _coerce_float
    assert _coerce_float(None, None) is None


def test_coerce_float_valid():
    from src.parse_frontmatter import _coerce_float
    assert _coerce_float(2.5, None) == 2.5
    assert _coerce_float("3.0", 0.0) == 3.0


def test_format_block(tmp_path):
    block = format_selection(
        {"project_name": "X", "ideas_left": 1, "reviews_left": 2,
         "to_do_left": 3, "to_improve_left": 4}
    )
    assert block == (
        'project_name: "X"\nideas_left: 1\nreviews_left: 2\n'
        "to_do_left: 3\nto_improve_left: 4"
    )


def test_stray_file_under_root_is_skipped(tmp_path, capsys):
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "RealProject",
        "---\npriority: 1\nstate: working\nmax_ideas: 10\nmax_reviews: 0\nmax_to_do: 0\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    (root / ".DS_Store").write_text("x")
    _age(root)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    assert ".DS_Store" not in {r["project_name"] for r in table}
    chosen = select_project(table, min_idle=0)
    assert chosen["project_name"] == "RealProject"
    assert ".DS_Store" in capsys.readouterr().err


def test_skips_project_without_project_md(tmp_path, capsys):
    # A half-set-up folder (stages + queued task, no project.md) must not be
    # picked just because defaults fill in state: working.
    root = tmp_path / "Projects"
    root.mkdir()
    proj = root / "NoSettings"
    for stage in ("00_backlog", "00_tasks", "01_to-do", "02_in-progress", "03_to-review"):
        (proj / stage).mkdir(parents=True)
    (proj / "01_to-do" / "task_1.md").write_text("x", encoding="utf-8")
    _age(root)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    chosen = select_project(table, min_idle=0)
    assert chosen["project_name"] == ""
    assert "NoSettings: no project.md" in capsys.readouterr().err


def test_skips_project_with_missing_location(tmp_path):
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "BlankLoc",
        "---\nlocation:\npriority: 1\nstate: working\nmax_ideas: 10\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    _make_project(
        root, "DeadLoc",
        "---\nlocation: /does/not/exist\npriority: 1\nstate: working\nmax_ideas: 10\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    _age(root)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    assert select_project(table, min_idle=0)["project_name"] == ""


def test_state_normalized_case_insensitive(tmp_path):
    # `state: Working` (capital W) must still select — the value is trimmed and
    # lower-cased before the `== "working"` comparison.
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "CapState",
        "---\npriority: 1\nstate: Working\nmax_ideas: 10\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    _age(root)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    assert select_project(table, min_idle=0)["project_name"] == "CapState"


def test_missing_priority_defaults_to_middle(tmp_path):
    # Omitting priority should default to the neutral middle (3), not sink to 5.
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "NoPriority",
        "---\nstate: working\nmax_ideas: 10\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    _age(root)
    table = merge_frontmatter(root, compute_idle_times(root))
    assert next(r for r in table if r["project_name"] == "NoPriority")["priority"] == 3


def test_unrecognized_state_warns_and_skips(tmp_path, capsys):
    root = tmp_path / "Projects"
    root.mkdir()
    _make_project(
        root, "Typo",
        "---\npriority: 1\nstate: workign\nmax_ideas: 10\n---\n",
        {"00_backlog": ["idea_1.md"]},
    )
    _age(root)
    table = count_files(root, merge_frontmatter(root, compute_idle_times(root)))
    assert select_project(table, min_idle=0)["project_name"] == ""
    err = capsys.readouterr().err
    assert "Typo: unrecognized state 'workign'" in err
