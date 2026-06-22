"""Tests for count_remaining.py. Run: uv run pytest (from scripts/)"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "generate-idea" / "scripts"))
from count_remaining import count_files, parse_cap


def test_parse_cap_happy(tmp_path):
    doc = tmp_path / "project.md"
    doc.write_text("max_ideas: 20\n", encoding="utf-8")
    assert parse_cap(str(doc), "max_ideas") == 20


def test_parse_cap_missing_file():
    assert parse_cap("/nonexistent/project.md", "max_ideas") == 0


def test_parse_cap_blank_value(tmp_path):
    doc = tmp_path / "project.md"
    doc.write_text("max_ideas: \n", encoding="utf-8")
    assert parse_cap(str(doc), "max_ideas") == 0


def test_parse_cap_non_numeric(tmp_path):
    doc = tmp_path / "project.md"
    doc.write_text("max_ideas: abc\n", encoding="utf-8")
    assert parse_cap(str(doc), "max_ideas") == 0


def test_parse_cap_unreadable_file(tmp_path):
    doc = tmp_path / "project.md"
    doc.write_text("max_ideas: 20\n", encoding="utf-8")
    doc.chmod(0o000)
    try:
        assert parse_cap(str(doc), "max_ideas") == 0
    finally:
        doc.chmod(0o644)


def test_parse_cap_unreadable_dir_no_crash(tmp_path):
    doc = tmp_path / "project.md"
    doc.write_text("max_ideas: 20\n", encoding="utf-8")
    assert parse_cap(str(doc), "max_ideas") == 20


def test_count_files_happy(tmp_path):
    for name in ("idea_one.md", "idea_two.md", "not_an_idea.txt"):
        (tmp_path / name).write_text("")
    assert count_files(str(tmp_path), "idea_") == 2


def test_count_files_missing_folder():
    assert count_files("/nonexistent/folder", "idea_") == 0


def test_count_files_empty_folder(tmp_path):
    assert count_files(str(tmp_path), "idea_") == 0


def test_count_files_no_match(tmp_path):
    (tmp_path / "review_one.md").write_text("")
    assert count_files(str(tmp_path), "idea_") == 0


def test_count_files_unreadable_folder(tmp_path):
    folder = tmp_path / "unreadable"
    folder.mkdir()
    folder.chmod(0o000)
    try:
        assert count_files(str(folder), "idea_") == 0
    finally:
        folder.chmod(0o755)


def test_count_files_review_prefix(tmp_path):
    for name in ("review_one.md", "review_two.md", "review_three.md", "idea_one.md"):
        (tmp_path / name).write_text("")
    assert count_files(str(tmp_path), "review_") == 3


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__]))
