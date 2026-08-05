"""Tests for miru/commands/tools_cmd.py — tools list/show/exec/docs commands."""

import json

import pytest

from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestToolsList:
    def test_list_text(self) -> None:
        result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 0

    def test_list_json(self) -> None:
        result = runner.invoke(app, ["tools", "list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) > 0
        assert all("name" in d for d in data)

    def test_list_category_files(self) -> None:
        result = runner.invoke(app, ["tools", "list", "--category", "files"])
        assert result.exit_code == 0

    def test_list_category_nonexistent(self) -> None:
        result = runner.invoke(app, ["tools", "list", "--category", "bogus"])
        assert result.exit_code == 0


class TestToolsShow:
    def test_show_existing(self) -> None:
        result = runner.invoke(app, ["tools", "show", "read_file"])
        assert result.exit_code == 0
        assert "read_file" in result.output

    def test_show_missing_exits(self) -> None:
        result = runner.invoke(app, ["tools", "show", "nope"])
        assert result.exit_code == 1


class TestToolsExec:
    def test_exec_with_args(self) -> None:
        result = runner.invoke(app, ["tools", "exec", "list_files", "--arg", "directory=."])
        assert result.exit_code == 0

    def test_exec_invalid_arg_format(self) -> None:
        result = runner.invoke(app, ["tools", "exec", "read_file", "--arg", "noequals"])
        assert result.exit_code == 1

    def test_exec_invalid_json(self) -> None:
        result = runner.invoke(app, ["tools", "exec", "read_file", "--json", "{bad"])
        assert result.exit_code == 1

    def test_exec_unknown_tool(self) -> None:
        result = runner.invoke(app, ["tools", "exec", "nope_tool"])
        assert result.exit_code == 1


class TestToolsDocs:
    def test_docs_to_stdout(self) -> None:
        result = runner.invoke(app, ["tools", "docs"])
        assert result.exit_code == 0
        assert "#" in result.output

    def test_docs_to_file(self, tmp_path) -> None:
        out = tmp_path / "TOOLS.md"
        result = runner.invoke(app, ["tools", "docs", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert "read_file" in out.read_text(encoding="utf-8")
