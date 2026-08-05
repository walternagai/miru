"""Tests for miru/logger.py — structured logging."""

import json

import pytest

import miru.logger as logger_mod
from miru.logger import Logger, enable_logging, get_logger


class TestLogger:
    def test_disabled_logger_does_nothing(self, capsys) -> None:
        logger = Logger(enabled=False, verbose=True)
        logger.info("hello")
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_verbose_writes_to_stderr(self, capsys) -> None:
        logger = Logger(enabled=True, verbose=True)
        logger.info("hello", data={"k": 1})
        captured = capsys.readouterr()
        assert "[INFO] hello" in captured.err
        assert '"k": 1' in captured.err

    def test_file_logging_writes_json_lines(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(logger_mod, "LOG_DIR", tmp_path)
        logger = Logger(enabled=True)
        logger.enable_file_logging()
        assert logger.log_file is not None
        logger.error("boom", data={"code": 500})
        lines = logger.log_file.read_text(encoding="utf-8").strip().split("\n")
        entry = json.loads(lines[0])
        assert entry["level"] == "ERROR"
        assert entry["message"] == "boom"
        assert entry["data"] == {"code": 500}

    def test_level_helpers(self, capsys) -> None:
        logger = Logger(enabled=True, verbose=True)
        logger.debug("d")
        logger.warning("w")
        captured = capsys.readouterr()
        assert "[DEBUG] d" in captured.err
        assert "[WARNING] w" in captured.err

    def test_request_response_helpers(self, capsys) -> None:
        logger = Logger(enabled=True, verbose=True)
        logger.request("POST", "http://x/api", body={"q": 1}, headers={"H": "v"})
        logger.response(200, "http://x/api", duration_ms=12.5)
        captured = capsys.readouterr()
        assert "HTTP POST http://x/api" in captured.err
        assert "HTTP 200 http://x/api" in captured.err
        assert "duration_ms" in captured.err


class TestGlobalLogger:
    def test_get_logger_singleton(self) -> None:
        logger_mod._logger = None
        logger = get_logger(enabled=True)
        assert get_logger() is logger

    def test_get_logger_merges_flags(self) -> None:
        logger_mod._logger = None
        logger = get_logger(enabled=False, verbose=False)
        get_logger(enabled=True, verbose=True)
        assert logger.enabled is True
        assert logger.verbose is True
        logger_mod._logger = None

    def test_enable_logging(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(logger_mod, "LOG_DIR", tmp_path)
        enable_logging(verbose=True)
        logger = logger_mod._logger
        assert logger is not None
        assert logger.enabled is True
        assert logger.verbose is True
        assert logger.log_file is not None
        logger_mod._logger = None
