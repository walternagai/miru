"""Tests for miru/template.py CLI commands — save/use/delete via typer app."""

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


class TestTemplateSave:
    def test_save_requires_prompt(self) -> None:
        result = runner.invoke(app, ["template", "save", "t1"])
        assert result.exit_code == 1

    def test_save_prompt_and_system(self) -> None:
        result = runner.invoke(
            app, ["template", "save", "t1", "--prompt", "Olá {nome}", "--system", "seja gentil"]
        )
        assert result.exit_code == 0
        templates = template_mod._list_templates()
        assert len(templates) == 1
        assert templates[0].prompt == "Olá {nome}"

    def test_save_both_prompt_and_file(self, tmp_path) -> None:
        f = tmp_path / "p.txt"
        f.write_text("do arquivo", encoding="utf-8")
        result = runner.invoke(
            app, ["template", "save", "t1", "--prompt", "x", "--prompt-file", str(f)]
        )
        assert result.exit_code == 1

    def test_save_missing_file(self) -> None:
        result = runner.invoke(app, ["template", "save", "t1", "--prompt-file", "nope.txt"])
        assert result.exit_code == 1

    def test_save_from_file(self, tmp_path) -> None:
        f = tmp_path / "p.txt"
        f.write_text("  conteúdo do arquivo  ", encoding="utf-8")
        result = runner.invoke(app, ["template", "save", "t1", "--prompt-file", str(f)])
        assert result.exit_code == 0
        assert template_mod._list_templates()[0].prompt == "conteúdo do arquivo"

    def test_save_with_parameters(self) -> None:
        result = runner.invoke(
            app, ["template", "save", "t1", "--prompt", "{a} {b}", "--parameters", "a,b"]
        )
        assert result.exit_code == 0
        assert template_mod._list_templates()[0].parameters == ["a", "b"]


class TestTemplateList:
    def test_empty(self) -> None:
        result = runner.invoke(app, ["template", "list"])
        assert result.exit_code == 0

    def test_with_templates(self) -> None:
        template_mod._save_template(template_mod.PromptTemplate(name="x", prompt="p"))
        result = runner.invoke(app, ["template", "list"])
        assert result.exit_code == 0
        assert "x" in result.output


class TestTemplateDelete:
    def test_delete_missing(self) -> None:
        result = runner.invoke(app, ["template", "delete", "nope"])
        assert result.exit_code == 1

    def test_delete_existing(self) -> None:
        template_mod._save_template(template_mod.PromptTemplate(name="x", prompt="p"))
        result = runner.invoke(app, ["template", "delete", "x", "--force"])
        assert result.exit_code == 0
        assert template_mod._list_templates() == []
