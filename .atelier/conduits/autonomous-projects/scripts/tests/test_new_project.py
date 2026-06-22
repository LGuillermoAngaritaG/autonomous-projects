"""Tests for new_project.py. Run: uv run pytest"""
import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from new_project import STAGE_FOLDERS, create_project, validate_slug


# ---------------------------------------------------------------------------
# validate_slug
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("slug", [
    "my-proj", "a1", "hello", "multi-word-slug", "a", "1abc", "abc123-def456",
])
def test_valid_slugs(slug):
    assert validate_slug(slug) is True


@pytest.mark.parametrize("slug", [
    "My-Proj", "my_proj", "my proj", "", "-leading", "trailing-",
    "UPPER", "has space", "double--dash",
])
def test_invalid_slugs(slug):
    assert validate_slug(slug) is False


# ---------------------------------------------------------------------------
# create_project — happy path
# ---------------------------------------------------------------------------

TEMPLATE = """\
---
location: path-to-work-on
priority: 1-5
use_git: true/false
state: working|paused
max_ideas: 10
max_reviews: 5
max_to_do: 5
---
"""


def _template(tmp_path: Path) -> Path:
    p = tmp_path / "project_template.md"
    p.write_text(TEMPLATE, encoding="utf-8")
    return p


def test_happy_path(tmp_path):
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    tmpl = _template(tmp_path)
    loc = str(tmp_path / "codebase")
    (tmp_path / "codebase").mkdir()

    result = create_project("my-proj", loc, projects_root, tmpl)

    assert result == projects_root / "my-proj"
    assert result.is_dir()

    for folder in STAGE_FOLDERS:
        assert (result / folder).is_dir()

    project_md = result / "project.md"
    assert project_md.is_file()
    text = project_md.read_text(encoding="utf-8")
    assert f"location: {loc}" in text


def test_location_line_is_rewritten(tmp_path):
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    tmpl = _template(tmp_path)
    loc = str(tmp_path / "codebase")
    (tmp_path / "codebase").mkdir()

    create_project("my-proj", loc, projects_root, tmpl)
    text = (projects_root / "my-proj" / "project.md").read_text(encoding="utf-8")
    assert "location: path-to-work-on" not in text


# ---------------------------------------------------------------------------
# Rejection cases
# ---------------------------------------------------------------------------

def test_invalid_slug_rejected(tmp_path):
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    tmpl = _template(tmp_path)
    with pytest.raises(ValueError, match="lowercase kebab-case"):
        create_project("Bad Slug", str(tmp_path), projects_root, tmpl)
    assert not (projects_root / "Bad Slug").exists()


def test_already_exists_rejected(tmp_path):
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    (projects_root / "existing").mkdir()
    tmpl = _template(tmp_path)
    with pytest.raises(FileExistsError, match="already exists"):
        create_project("existing", str(tmp_path), projects_root, tmpl)


def test_missing_location_rejected(tmp_path):
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    tmpl = _template(tmp_path)
    missing = str(tmp_path / "does-not-exist")
    with pytest.raises(OSError, match="does not exist or is not writable"):
        create_project("my-proj", missing, projects_root, tmpl)
    assert not (projects_root / "my-proj").exists()


@pytest.mark.skipif(os.name == "nt", reason="chmod 0 not portable to Windows")
def test_unwritable_location_rejected(tmp_path):
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    tmpl = _template(tmp_path)
    unwritable = tmp_path / "unwritable"
    unwritable.mkdir()
    unwritable.chmod(0o000)
    try:
        with pytest.raises(OSError, match="does not exist or is not writable"):
            create_project("my-proj", str(unwritable), projects_root, tmpl)
    finally:
        unwritable.chmod(0o755)  # restore so tmp_path cleanup works
    assert not (projects_root / "my-proj").exists()


# ---------------------------------------------------------------------------
# Atomicity — failure during build leaves nothing behind
# ---------------------------------------------------------------------------

def test_atomicity_bad_template_path(tmp_path):
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    bad_template = tmp_path / "nonexistent_template.md"
    loc = str(tmp_path / "codebase")
    (tmp_path / "codebase").mkdir()

    with pytest.raises(OSError, match="Template not found"):
        create_project("my-proj", loc, projects_root, bad_template)

    assert not (projects_root / "my-proj").exists()

    leftovers = list(projects_root.iterdir())
    assert len(leftovers) == 0, f"Leftover temp dirs: {leftovers}"


def test_atomicity_creates_nothing_on_bad_slug(tmp_path):
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    tmpl = _template(tmp_path)
    with pytest.raises(ValueError):
        create_project("BAD", str(tmp_path), projects_root, tmpl)
    assert list(projects_root.iterdir()) == []
