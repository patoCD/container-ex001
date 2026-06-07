#
# test_lib_utils.py
#

import pytest
from pathlib import Path

from pipeline.lib_utils import find_project_root



def test_finds_root_with_marker_in_parent(tmp_path):
    # /tmp/project/ (marker here)
    project_root = tmp_path
    (project_root / "pyproject.toml").write_text("")

    # /tmp/project/src/module/
    start_dir = project_root / "src" / "module"
    start_dir.mkdir(parents=True)

    result = find_project_root(start=start_dir, marker="pyproject.toml")

    assert result == project_root.resolve()


def test_finds_root_when_marker_is_in_start_dir(tmp_path):
    project_root = tmp_path
    (project_root / "pyproject.toml").write_text("")

    result = find_project_root(start=project_root, marker="pyproject.toml")

    assert result == project_root.resolve()


def test_finds_root_with_file_as_start(tmp_path):
    project_root = tmp_path
    (project_root / "pyproject.toml").write_text("")

    file_path = project_root / "src" / "module.py"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("print('hello')")

    result = find_project_root(start=file_path, marker="pyproject.toml")

    assert result == project_root.resolve()


def test_marker_as_directory(tmp_path):
    project_root = tmp_path
    (project_root / "my_marker_dir").mkdir()

    start_dir = project_root / "a" / "b"
    start_dir.mkdir(parents=True)

    result = find_project_root(start=start_dir, marker="my_marker_dir")

    assert result == project_root.resolve()


def test_raises_when_marker_not_found(tmp_path):
    start_dir = tmp_path / "a" / "b"
    start_dir.mkdir(parents=True)

    with pytest.raises(RuntimeError) as excinfo:
        find_project_root(start=start_dir, marker="nonexistent.marker")

    assert "No se encontró raíz del proyecto" in str(excinfo.value)


def test_accepts_path_object_and_string(tmp_path):
    project_root = tmp_path
    (project_root / "pyproject.toml").write_text("")

    start_dir = project_root / "src"
    start_dir.mkdir()

    # Path object
    result1 = find_project_root(start=start_dir, marker="pyproject.toml")

    # String path
    result2 = find_project_root(start=str(start_dir), marker="pyproject.toml")

    assert result1 == project_root.resolve()
    assert result2 == project_root.resolve()