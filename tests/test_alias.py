"""Tests for miru/alias.py — model alias management."""

import pytest

import miru.alias as alias_mod
from miru.alias import alias_add, alias_delete, alias_list, alias_show, resolve_alias
from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolate_alias_file(tmp_path, monkeypatch):
    alias_file = tmp_path / "aliases.toml"
    monkeypatch.setattr(alias_mod, "ALIAS_FILE", alias_file)


class TestResolveAlias:
    def test_unknown_name_returns_itself(self) -> None:
        assert resolve_alias("gemma3:latest") == "gemma3:latest"

    def test_resolves_registered_alias(self) -> None:
        alias_add("g3", "gemma3:latest")
        assert resolve_alias("g3") == "gemma3:latest"

    def test_load_missing_file_returns_empty(self) -> None:
        assert resolve_alias("x") == "x"


class TestAliasAdd:
    def test_add_and_list(self, capsys) -> None:
        alias_add("g3", "gemma3:latest")
        assert resolve_alias("g3") == "gemma3:latest"
        captured = capsys.readouterr()
        assert "criado" in captured.out

    def test_duplicate_same_model_allowed(self, capsys) -> None:
        alias_add("g3", "gemma3:latest")
        alias_add("g3", "gemma3:latest")
        assert "já existe" not in capsys.readouterr().out

    def test_duplicate_different_model_warns(self, capsys) -> None:
        alias_add("g3", "gemma3:latest")
        capsys.readouterr()  # discard first call output
        alias_add("g3", "llama3")
        captured = capsys.readouterr()
        assert "already exists" in captured.out
        assert resolve_alias("g3") == "gemma3:latest"


class TestAliasDelete:
    def test_delete_requires_force(self, capsys) -> None:
        alias_add("g3", "gemma3:latest")
        alias_delete("g3")
        assert "Use --force" in capsys.readouterr().out
        assert resolve_alias("g3") == "gemma3:latest"

    def test_delete_with_force(self, capsys) -> None:
        alias_add("g3", "gemma3:latest")
        alias_delete("g3", force=True)
        assert "deletado" in capsys.readouterr().out
        assert resolve_alias("g3") == "g3"

    def test_delete_missing_exits(self) -> None:
        with pytest.raises(SystemExit):
            alias_delete("nope")


class TestAliasShow:
    def test_show_existing(self, capsys) -> None:
        alias_add("g3", "gemma3:latest")
        alias_show("g3")
        captured = capsys.readouterr()
        assert "gemma3:latest" in captured.out

    def test_show_missing(self, capsys) -> None:
        alias_show("nope")
        captured = capsys.readouterr()
        assert "não é um alias" in captured.out


class TestAliasList:
    def test_list_empty(self, capsys) -> None:
        alias_list()
        assert "Nenhum alias" in capsys.readouterr().out

    def test_list_with_entries(self, capsys) -> None:
        alias_add("g3", "gemma3:latest")
        alias_add("q7", "qwen2.5:7b")
        alias_list()
        captured = capsys.readouterr()
        assert "g3" in captured.out
        assert "q7" in captured.out


class TestCliIntegration:
    def test_cli_add_and_resolve(self) -> None:
        result = runner.invoke(app, ["alias", "add", "g3", "gemma3:latest"])
        assert result.exit_code == 0
        assert resolve_alias("g3") == "gemma3:latest"

    def test_cli_list(self) -> None:
        result = runner.invoke(app, ["alias", "list"])
        assert result.exit_code == 0
