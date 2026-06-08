#
# test_lib_utils.py
#

import pytest

from pathlib import Path
import logging
import os
import time
from unittest.mock import patch, Mock, call
import argparse
import sys
import inspect

from pipeline.lib_utils import find_project_root, setup_logging, opt_get, find_file, info_desc, retry


## find_project_root


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



## setup_logging

@pytest.fixture(autouse=True)
def cleanup_root_logger():
    """
    Ensure logger handlers are cleaned before/after each test
    to avoid cross-test contamination.
    """
    logger = logging.getLogger()

    # Before test
    logger.handlers.clear()

    yield

    # After test
    logger.handlers.clear()


def test_setup_logging_creates_log_directory(tmp_path):
    log_dir = "test_logs"

    with patch("time.strftime", return_value="20240101_120000"):
        log_file = setup_logging(
            verbose=False,
            dirname=log_dir,
            root_dir=str(tmp_path),
        )

    expected_dir = tmp_path / log_dir

    assert expected_dir.exists()
    assert expected_dir.is_dir()

    assert str(expected_dir) in log_file


def test_setup_logging_returns_correct_log_file_path(tmp_path):
    with patch("time.strftime", return_value="20240101_120000"):
        log_file = setup_logging(
            verbose=False,
            dirname="logs",
            root_dir=str(tmp_path),
        )

    expected = tmp_path / "logs" / "pipeline_20240101_120000.log"

    assert log_file == str(expected)


def test_setup_logging_sets_debug_level_when_verbose(tmp_path):
    with patch("time.strftime", return_value="20240101_120000"):
        setup_logging(
            verbose=True,
            root_dir=str(tmp_path),
        )

    logger = logging.getLogger()

    assert logger.level == logging.DEBUG


def test_setup_logging_sets_info_level_when_not_verbose(tmp_path):
    with patch("time.strftime", return_value="20240101_120000"):
        setup_logging(
            verbose=False,
            root_dir=str(tmp_path),
        )

    logger = logging.getLogger()

    assert logger.level == logging.INFO


def test_setup_logging_adds_two_handlers(tmp_path):
    with patch("time.strftime", return_value="20240101_120000"):
        setup_logging(
            verbose=False,
            root_dir=str(tmp_path),
        )

    logger = logging.getLogger()

    assert len(logger.handlers) == 2

    assert any(
        isinstance(h, logging.StreamHandler)
        for h in logger.handlers
    )

    assert any(
        isinstance(h, logging.FileHandler)
        for h in logger.handlers
    )


def test_setup_logging_handlers_use_correct_formatter(tmp_path):
    expected_format = "%(asctime)s | %(levelname)s | %(message)s"

    with patch("time.strftime", return_value="20240101_120000"):
        setup_logging(
            verbose=False,
            root_dir=str(tmp_path),
        )

    logger = logging.getLogger()

    for handler in logger.handlers:
        assert handler.formatter is not None
        assert handler.formatter._fmt == expected_format


def test_setup_logging_clears_existing_handlers(tmp_path):
    logger = logging.getLogger()

    dummy_handler = logging.StreamHandler()
    logger.addHandler(dummy_handler)

    # Verify our handler was added
    assert dummy_handler in logger.handlers

    with patch("time.strftime", return_value="20240101_120000"):
        setup_logging(
            verbose=False,
            root_dir=str(tmp_path),
        )

    # Old handler should be removed
    assert dummy_handler not in logger.handlers

    # setup_logging should install exactly:
    # - one StreamHandler
    # - one FileHandler
    stream_handlers = [
        h for h in logger.handlers
        if isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.FileHandler)
    ]

    file_handlers = [
        h for h in logger.handlers
        if isinstance(h, logging.FileHandler)
    ]

    assert len(stream_handlers) == 1
    assert len(file_handlers) == 1


def test_setup_logging_creates_log_file(tmp_path):
    with patch("time.strftime", return_value="20240101_120000"):
        log_file = setup_logging(
            verbose=False,
            root_dir=str(tmp_path),
        )

    # Trigger actual file write
    logging.getLogger().info("test message")

    assert os.path.exists(log_file)
    assert os.path.isfile(log_file)


def test_setup_logging_writes_log_message_to_file(tmp_path):
    with patch("time.strftime", return_value="20240101_120000"):
        log_file = setup_logging(
            verbose=False,
            root_dir=str(tmp_path),
        )

    test_message = "hello unit test"

    logging.getLogger().info(test_message)

    with open(log_file, "r") as f:
        contents = f.read()

    assert test_message in contents
    assert "INFO" in contents


def test_setup_logging_file_handler_append_mode(tmp_path):
    with patch("time.strftime", return_value="20240101_120000"):
        setup_logging(
            verbose=False,
            root_dir=str(tmp_path),
        )

    logger = logging.getLogger()

    file_handler = next(
        h for h in logger.handlers
        if isinstance(h, logging.FileHandler)
    )

    assert file_handler.mode == "a"


def test_setup_logging_multiple_calls_do_not_duplicate_handlers(tmp_path):
    with patch("time.strftime", return_value="20240101_120000"):
        setup_logging(
            verbose=False,
            root_dir=str(tmp_path),
        )

    logger = logging.getLogger()

    assert len(logger.handlers) == 2

    with patch("time.strftime", return_value="20240101_120001"):
        setup_logging(
            verbose=False,
            root_dir=str(tmp_path),
        )

    # Still exactly 2 handlers
    assert len(logger.handlers) == 2



def test_setup_logging_raises_if_directory_creation_fails(tmp_path):
    with patch("os.makedirs", side_effect=PermissionError):
        with pytest.raises(PermissionError):
            setup_logging(
                verbose=False,
                root_dir=str(tmp_path),
            )


## opt_get


# -------------------------------------------------------------------
# Basic behavior
# -------------------------------------------------------------------

def test_returns_default_when_argument_missing(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])

    result = opt_get("port", default=80, cast=int)

    assert result == 80


def test_returns_argument_value(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--port", "8080"])

    result = opt_get("port", default=80, cast=int)

    assert result == 8080


# -------------------------------------------------------------------
# Type casting
# -------------------------------------------------------------------

@pytest.mark.parametrize(
    "argv, cast, expected",
    [
        (["prog", "--value", "10"], int, 10),
        (["prog", "--value", "3.14"], float, 3.14),
        (["prog", "--value", "hello"], str, "hello"),
    ],
)
def test_casting(monkeypatch, argv, cast, expected):
    monkeypatch.setattr(sys, "argv", argv)

    result = opt_get("value", cast=cast)

    assert result == expected
    assert isinstance(result, type(expected))


# -------------------------------------------------------------------
# Invalid cast handling
# -------------------------------------------------------------------

def test_invalid_integer_cast_raises_system_exit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--port", "not-an-int"])

    with pytest.raises(SystemExit):
        opt_get("port", cast=int)


def test_invalid_float_cast_raises_system_exit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--ratio", "abc"])

    with pytest.raises(SystemExit):
        opt_get("ratio", cast=float)


# -------------------------------------------------------------------
# Unknown arguments should be ignored
# -------------------------------------------------------------------

def test_unknown_arguments_are_ignored(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--unknown", "x", "--port", "5000"]
    )

    result = opt_get("port", default=80, cast=int)

    assert result == 5000


def test_multiple_unknown_arguments_are_ignored(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--foo", "1",
            "--bar", "2",
            "--port", "9000",
            "--baz", "3",
        ],
    )

    result = opt_get("port", cast=int)

    assert result == 9000


# -------------------------------------------------------------------
# Edge cases
# -------------------------------------------------------------------

def test_none_default(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])

    result = opt_get("token")

    assert result is None


def test_empty_string_value(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--name", ""])

    result = opt_get("name")

    assert result == ""


def test_zero_integer_value(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--count", "0"])

    result = opt_get("count", cast=int)

    assert result == 0


def test_negative_integer_value(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--offset", "-5"])

    result = opt_get("offset", cast=int)

    assert result == -5


# -------------------------------------------------------------------
# Boolean behavior
# -------------------------------------------------------------------

@pytest.mark.parametrize(
    "value, expected",
    [
        ("True", True),
        ("False", True),  # bool("False") == True in Python
        ("", False),
    ],
)
def test_bool_cast_behavior(monkeypatch, value, expected):
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--flag", value]
    )

    result = opt_get("flag", cast=bool)

    assert result == expected


# -------------------------------------------------------------------
# Argument naming
# -------------------------------------------------------------------

def test_argument_name_is_dynamic(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--custom-option", "value"]
    )

    result = opt_get("custom-option")

    assert result == "value"


# -------------------------------------------------------------------
# Repeated calls
# -------------------------------------------------------------------

def test_multiple_calls_with_different_arguments(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--port", "7000"]
    )

    port = opt_get("port", cast=int)

    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--host", "localhost"]
    )

    host = opt_get("host")

    assert port == 7000
    assert host == "localhost"


## find_file

def test_find_file_returns_matching_file(tmp_path):
    """
    Should return the absolute resolved path when exactly one file exists.
    """
    target = tmp_path / "config.yaml"
    target.write_text("data")

    result = find_file("config.yaml", root_dir=tmp_path)

    assert result == target.resolve()


def test_find_file_searches_recursively(tmp_path):
    """
    Should locate files in nested subdirectories.
    """
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)

    target = nested / "settings.json"
    target.write_text("{}")

    result = find_file("settings.json", root_dir=tmp_path)

    assert result == target.resolve()


def test_find_file_raises_when_missing(tmp_path):
    """
    Should raise FileNotFoundError when no file exists.
    """
    with pytest.raises(FileNotFoundError) as exc_info:
        find_file("missing.txt", root_dir=tmp_path)

    assert "No file named 'missing.txt'" in str(exc_info.value)


def test_find_file_raises_when_multiple_matches_exist(tmp_path):
    """
    Should raise ValueError when multiple matching files are found.
    """
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"

    dir1.mkdir()
    dir2.mkdir()

    file1 = dir1 / "duplicate.txt"
    file2 = dir2 / "duplicate.txt"

    file1.write_text("one")
    file2.write_text("two")

    with pytest.raises(ValueError) as exc_info:
        find_file("duplicate.txt", root_dir=tmp_path)

    message = str(exc_info.value)

    assert "Multiple files named 'duplicate.txt'" in message
    assert str(file1) in message
    assert str(file2) in message


def test_find_file_ignores_directories_with_same_name(tmp_path):
    """
    Should ignore directories and only match files.
    """
    matching_dir = tmp_path / "target.txt"
    matching_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        find_file("target.txt", root_dir=tmp_path)


def test_find_file_returns_resolved_absolute_path(tmp_path):
    """
    Returned path should be fully resolved and absolute.
    """
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    target = subdir / "app.ini"
    target.write_text("[app]")

    result = find_file("app.ini", root_dir=tmp_path)

    assert result.is_absolute()
    assert result == target.resolve()



## info_desc

class NoSize:
    pass


class HasName:
    def __init__(self, name):
        self.name = name


class FakeSized:
    def __len__(self):
        return 42


def get_log(caplog):
    return caplog.records[-1].message


def test_explicit_label(caplog):
    caplog.set_level(logging.DEBUG)

    data = [1, 2, 3]
    info_desc(data, label="my_list")

    msg = get_log(caplog)

    assert msg == "my_list: type=list, size=3"


def test_auto_label_from_variable_name(caplog):
    caplog.set_level(logging.DEBUG)

    users = ["Alice", "Bob"]
    info_desc(users)

    msg = get_log(caplog)

    assert msg == "users: type=list, size=2"


def test_auto_label_fallback_obj(caplog):
    caplog.set_level(logging.DEBUG)

    info_desc(object())

    msg = get_log(caplog)

    assert msg.startswith("obj: type=object, size=N/A")


def test_no_sized_object(caplog):
    caplog.set_level(logging.DEBUG)

    obj = NoSize()
    info_desc(obj, label="no_size")

    msg = get_log(caplog)

    assert "size=N/A" in msg
    assert "type=NoSize" in msg


def test_custom_len_object(caplog):
    caplog.set_level(logging.DEBUG)

    obj = FakeSized()
    info_desc(obj, label="fake")

    msg = get_log(caplog)

    assert "size=42" in msg


def test_object_with_name(caplog):
    caplog.set_level(logging.DEBUG)

    obj = HasName("data.csv")
    info_desc(obj, label="file")

    msg = get_log(caplog)

    assert "name=data.csv" in msg


def test_object_without_name(caplog):
    caplog.set_level(logging.DEBUG)

    obj = [1, 2, 3]
    info_desc(obj, label="list")

    msg = get_log(caplog)

    assert "name=" not in msg


def test_multiple_references_same_object(caplog):
    caplog.set_level(logging.DEBUG)

    data = [1, 2, 3]
    alias = data

    info_desc(data)

    msg = get_log(caplog)

    # Should still pick one valid variable name
    assert msg.split(":")[0] in {"data", "alias"}


def test_inspect_fallback(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)

    class DummyFrame:
        f_back = type("F", (), {"f_locals": {}})()

    monkeypatch.setattr(inspect, "currentframe", lambda: DummyFrame())

    obj = object()
    info_desc(obj)

    msg = get_log(caplog)

    assert msg.startswith("obj:")


def test_dict_and_list_sizes(caplog):
    caplog.set_level(logging.DEBUG)

    caplog.clear()
    info_desc({"a": 1, "b": 2}, label="d")
    msg1 = get_log(caplog)
    assert "size=2" in msg1

    caplog.clear()
    info_desc([1, 2, 3, 4], label="l")
    msg2 = get_log(caplog)
    assert "size=4" in msg2


def test_logging_called_with_correct_message(monkeypatch):
    called = {}

    def fake_debug(msg):
        called["msg"] = msg

    monkeypatch.setattr(logging, "debug", fake_debug)

    info_desc([1, 2], label="test")

    assert called["msg"] == "test: type=list, size=2"


## retry

def test_success_first_try():
    def func():
        return "ok"

    wrapped = retry(retries=3)(func)

    result = wrapped()

    assert result == "ok"


def test_success_after_retries():
    calls = {"count": 0}

    def mock_func():
        calls["count"] += 1
        if calls["count"] == 1:
            raise ValueError("fail")
        return "success"

    wrapped = retry(retries=3, delay=0)(mock_func)

    result = wrapped()

    assert result == "success"
    assert calls["count"] == 2


def test_exhaust_retries_raises_last_exception():
    calls = {"count": 0}

    def mock_func():
        calls["count"] += 1
        raise ValueError("always fails")

    wrapped = retry(retries=3, delay=0)(mock_func)

    with pytest.raises(ValueError, match="always fails"):
        wrapped()

    assert calls["count"] == 3


def test_non_retry_exception_not_caught():
    attempts = 0

    def mock_func():
        nonlocal attempts
        attempts += 1
        raise TypeError("no retry")

    wrapped = retry(retries=3, exceptions=(ValueError,))(mock_func)

    with pytest.raises(TypeError, match="no retry"):
        wrapped()

    assert attempts == 1


def test_delay_backoff_pattern():
    attempts = 0

    def mock_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("fail")
        return "ok"

    with patch("time.sleep") as sleep_mock:
        wrapped = retry(retries=3, delay=1)(mock_func)

        result = wrapped()

        assert result == "ok"

        # sleep called after first and second failure
        assert sleep_mock.call_args_list == [call(1), call(2)]


def test_logging_calls():
    attempts = 0

    def mock_func():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ValueError("fail")
        return "ok"

    with patch("logging.debug") as debug_mock, \
         patch("logging.warning") as warning_mock:

        wrapped = retry(retries=3, delay=0)(mock_func)
        wrapped()

        debug_mock.assert_called()
        warning_mock.assert_called_once()


def test_last_error_is_raised():
    def mock_func():
        raise RuntimeError("boom")

    wrapped = retry(retries=2, delay=0)(mock_func)

    with pytest.raises(RuntimeError) as exc:
        wrapped()

    assert str(exc.value) == "boom"



def test_single_retry_attempt():
    spy = Mock()

    def mock_func():
        spy()
        raise ValueError("fail")

    wrapped = retry(retries=1, delay=0)(mock_func)

    with pytest.raises(ValueError, match="fail"):
        wrapped()

    spy.assert_called_once()