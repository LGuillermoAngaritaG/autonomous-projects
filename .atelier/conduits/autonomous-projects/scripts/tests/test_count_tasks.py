"""Tests for count_tasks.py. Run: uv run pytest (from scripts/)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "work-one-todo" / "scripts"))
from count_tasks import count_md_files


def test_count_md_files_happy(tmp_path):
    for name in ("task_foo.md", "task_bar.md", "readme.txt", "notes.md"):
        (tmp_path / name).write_text("")
    assert count_md_files(str(tmp_path)) == 3


def test_count_md_files_missing_dir():
    assert count_md_files("/nonexistent/folder") == 0


def test_count_md_files_empty_dir(tmp_path):
    assert count_md_files(str(tmp_path)) == 0


def test_count_md_files_no_md(tmp_path):
    (tmp_path / "readme.txt").write_text("")
    (tmp_path / "data.csv").write_text("")
    assert count_md_files(str(tmp_path)) == 0


def test_count_md_files_case_insensitive(tmp_path):
    (tmp_path / "TASK.MD").write_text("")
    (tmp_path / "Note.Md").write_text("")
    assert count_md_files(str(tmp_path)) == 2


def test_count_md_files_unreadable_dir_swallowed(tmp_path):
    folder = tmp_path / "unreadable"
    folder.mkdir()
    folder.chmod(0o000)
    try:
        assert count_md_files(str(folder)) == 0
    finally:
        folder.chmod(0o755)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__]))
