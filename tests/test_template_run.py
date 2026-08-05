"""Tests for miru/template.py CLI show/run commands."""

from unittest.mock import patch

import pytest

import miru.template as template_mod
from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_template_dir(tmp_path, monkeypatch):
    template_dir = tmp_path / "templates"
    template_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(template_mod, "TEMPLATE_DIR", template_dir)


class TestTemplateShow:
    def test_show_missing(self) -> None:
        result = runner.invoke(app, ["template", "show", "nope"])
        assert result.exit_code == 1

    def test_show_existing(self) -> None:
        template_mod._save_template(
            template_mod.PromptTemplate(name="t1", prompt="P {x}", description="d", parameters=["x"])
        )
        result = runner.invoke(app, ["template", "show", "t1"])
        assert result.exit_code == 0
        assert "P {x}" in result.output

    def test_show_corrupt_file(self) -> None:
        (template_mod.TEMPLATE_DIR / "bad.json").write_text("{bad", encoding="utf-8")
        result = runner.invoke(app, ["template", "show", "bad"])
        assert result.exit_code == 1


class TestTemplateRun:
    def test_run_missing_template(self) -> None:
        result = runner.invoke(app, ["template", "run", "nope", "gemma3"])
        assert result.exit_code == 1

    def test_run_invalid_param(self) -> None:
        template_mod._save_template(template_mod.PromptTemplate(name="t1", prompt="P {x}"))
        result = runner.invoke(app, ["template", "run", "t1", "gemma3", "--param", "noequals"])
        assert result.exit_code == 1

    def test_run_success(self) -> None:
        template_mod._save_template(template_mod.PromptTemplate(name="t1", prompt="Olá {nome}"))
        with patch("miru.commands.run.run") as mock_run:
            result = runner.invoke(
                app, ["template", "run", "t1", "gemma3", "--param", "nome=Mundo", "--quiet"]
            )
            assert result.exit_code == 0
            mock_run.assert_called_once()
            # verify rendered prompt passed through
            call_prompt = mock_run.call_args.kwargs.get("prompt") or mock_run.call_args.args[1]
            assert "Olá Mundo" in str(call_prompt)
