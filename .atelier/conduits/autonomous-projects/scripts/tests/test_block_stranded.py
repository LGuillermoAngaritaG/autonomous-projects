"""Tests for block_stranded.py. Run: uv run pytest (from scripts/)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "work-one-todo" / "scripts"))
from block_stranded import block_stranded


def _project(tmp_path):
    proj = tmp_path / "proj"
    (proj / "02_in-progress").mkdir(parents=True)
    return proj


def test_moves_stranded_file_with_note(tmp_path):
    proj = _project(tmp_path)
    src = proj / "02_in-progress" / "task_x.md"
    src.write_text("# Description\nwork\n", encoding="utf-8")
    dest = block_stranded(proj)
    assert dest is not None
    moved = Path(dest)
    assert moved.parent.name == "05_blocked"
    assert moved.name == "task_x.md"
    assert not src.exists()
    body = moved.read_text(encoding="utf-8")
    assert body.startswith("# Description")  # original content preserved
    assert "# Blocked" in body


def test_empty_in_progress_is_noop(tmp_path):
    proj = _project(tmp_path)
    assert block_stranded(proj) is None
    assert not (proj / "05_blocked").exists()


def test_non_md_left_alone(tmp_path):
    proj = _project(tmp_path)
    (proj / "02_in-progress" / "notes.txt").write_text("x", encoding="utf-8")
    assert block_stranded(proj) is None
    assert not (proj / "05_blocked").exists()
    assert (proj / "02_in-progress" / "notes.txt").exists()


def test_name_collision_does_not_clobber(tmp_path):
    proj = _project(tmp_path)
    (proj / "05_blocked").mkdir()
    (proj / "05_blocked" / "task_x.md").write_text("first", encoding="utf-8")
    src = proj / "02_in-progress" / "task_x.md"
    src.write_text("second", encoding="utf-8")
    dest = block_stranded(proj)
    assert Path(dest).name == "task_x.2.md"
    assert (proj / "05_blocked" / "task_x.md").read_text(encoding="utf-8") == "first"


def test_missing_in_progress_dir_no_crash(tmp_path):
    proj = tmp_path / "bare"
    proj.mkdir()
    assert block_stranded(proj) is None


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__]))
