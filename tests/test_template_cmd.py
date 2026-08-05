"""Tests for miru/template.py CLI commands — save/use/delete via typer app."""

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


class TestTemplateRunMore:
    def test_run_missing_model_falls_back_to_config(self, monkeypatch) -> None:
        import miru.template as template_mod
        from miru.core.config import Config

        template_mod._save_template(template_mod.PromptTemplate(name="t1", prompt="P {x}"))
        cfg = Config(default_model="gemma3")
        monkeypatch.setattr("miru.config_manager.load_config", lambda: cfg)
        with patch("miru.commands.run.run") as mock_run:
            result = runner.invoke(
                app, ["template", "run", "t1", "--param", "x=1", "--quiet"]
            )
            assert result.exit_code == 0
            mock_run.assert_called_once()

    def test_run_no_model_no_config_exits(self, monkeypatch) -> None:
        import miru.template as template_mod
        from miru.core.config import Config

        template_mod._save_template(template_mod.PromptTemplate(name="t1", prompt="P"))
        monkeypatch.setattr("miru.config_manager.load_config", lambda: Config())
        result = runner.invoke(app, ["template", "run", "t1", "--quiet"])
        assert result.exit_code == 1

    def test_run_with_extra_prompt(self) -> None:
        import miru.template as template_mod
        from miru.core.config import Config

        template_mod._save_template(template_mod.PromptTemplate(name="t1", prompt="P {x}"))
        monkeypatch = __import__("unittest.mock").mock.patch
        from unittest.mock import patch as _patch

        with _patch("miru.config_manager.load_config", return_value=Config(default_model="m")), \
             _patch("miru.commands.run.run") as mock_run:
            result = runner.invoke(
                app, ["template", "run", "t1", "--param", "x=1", "--extra", "extra", "--quiet"]
            )
            assert result.exit_code == 0
            assert "extra" in mock_run.call_args.kwargs.get("prompt", "")


class TestTemplateExportImport:
    def test_export_to_file(self, tmp_path) -> None:
        import miru.template as template_mod

        template_mod._save_template(template_mod.PromptTemplate(name="t1", prompt="P"))
        out = tmp_path / "t1.json"
        result = runner.invoke(app, ["template", "export", "t1", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_export_missing_exits(self) -> None:
        result = runner.invoke(app, ["template", "export", "nope"])
        assert result.exit_code == 1

    def test_import_valid(self, tmp_path) -> None:
        import json

        f = tmp_path / "t.json"
        f.write_text(json.dumps({"name": "imp", "prompt": "P"}), encoding="utf-8")
        result = runner.invoke(app, ["template", "import", str(f)])
        assert result.exit_code == 0

    def test_import_missing_file(self) -> None:
        result = runner.invoke(app, ["template", "import", "nope.json"])
        assert result.exit_code == 1

    def test_import_corrupt(self, tmp_path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("{bad", encoding="utf-8")
        result = runner.invoke(app, ["template", "import", str(f)])
        assert result.exit_code == 1


class TestTemplateSaveValidation:
    def test_save_prompt_and_system_file_conflict(self, tmp_path) -> None:
        f = tmp_path / "s.txt"
        f.write_text("sys", encoding="utf-8")
        result = runner.invoke(
            app, ["template", "save", "t1", "--prompt", "p", "--system", "x", "--system-file", str(f)]
        )
        assert result.exit_code == 1

    def test_save_missing_system_file(self) -> None:
        result = runner.invoke(
            app, ["template", "save", "t1", "--prompt", "p", "--system-file", "nope.txt"]
        )
        assert result.exit_code == 1

    def test_save_with_system_file(self, tmp_path) -> None:
        f = tmp_path / "s.txt"
        f.write_text("  system do arquivo  ", encoding="utf-8")
        result = runner.invoke(
            app, ["template", "save", "t1", "--prompt", "p", "--system-file", str(f)]
        )
        assert result.exit_code == 0
        assert template_mod._list_templates()[0].system_prompt == "system do arquivo"


class TestTemplateShowDetailed:
    def test_show_with_all_fields(self) -> None:
        template_mod._save_template(
            template_mod.PromptTemplate(
                name="full", prompt="P {x}", description="descrição", parameters=["x"],
                system_prompt="sys",
            )
        )
        result = runner.invoke(app, ["template", "show", "full"])
        assert result.exit_code == 0
        assert "descrição" in result.output
        assert "sys" in result.output
