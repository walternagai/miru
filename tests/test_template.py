"""Tests for miru/template.py — prompt template persistence and rendering."""

import json

import pytest

import miru.template as template_mod
from miru.template import PromptTemplate, _delete_template, _list_templates, _save_template


@pytest.fixture(autouse=True)
def _isolate_template_dir(tmp_path, monkeypatch):
    template_dir = tmp_path / "templates"
    template_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(template_mod, "TEMPLATE_DIR", template_dir)


class TestPromptTemplate:
    def test_to_dict_from_dict_roundtrip(self) -> None:
        tpl = PromptTemplate(
            name="n", prompt="Hello {name}",
            system_prompt="Be {tone}", parameters=["name"],
        )
        assert PromptTemplate.from_dict(tpl.to_dict()) == tpl

    def test_render_replaces_prompt_and_system(self) -> None:
        tpl = PromptTemplate(name="n", prompt="Hello {name}", system_prompt="Be {tone}")
        prompt, system = tpl.render(name="World", tone="kind")
        assert prompt == "Hello World"
        assert system == "Be kind"

    def test_render_keeps_unfilled_placeholders(self) -> None:
        tpl = PromptTemplate(name="n", prompt="Hi {a} and {b}")
        prompt, _ = tpl.render(a="1")
        assert prompt == "Hi 1 and {b}"

    def test_render_system_none(self) -> None:
        tpl = PromptTemplate(name="n", prompt="P {x}")
        prompt, system = tpl.render(x="v")
        assert prompt == "P v"
        assert system is None


class TestPersistence:
    def test_save_and_list(self) -> None:
        tpl = PromptTemplate(name="summarize", prompt="Resuma: {text}")
        _save_template(tpl)
        templates = _list_templates()
        assert len(templates) == 1
        assert templates[0].name == "summarize"
        assert templates[0].prompt == "Resuma: {text}"
        assert templates[0].created_at is not None
        assert templates[0].modified_at is not None

    def test_save_overwrites_prompt_keeping_existing_created(self) -> None:
        tpl = PromptTemplate(name="t", prompt="p", created_at="2020-01-01T00:00:00")
        _save_template(tpl)
        tpl.prompt = "p2"  # same object reused
        _save_template(tpl)
        saved = _list_templates()[0]
        assert saved.created_at == "2020-01-01T00:00:00"
        assert saved.prompt == "p2"

    def test_list_sorted_and_skips_corrupt(self, tmp_path) -> None:
        template_mod.TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        (template_mod.TEMPLATE_DIR / "a.json").write_text('{"name": "a", "prompt": "p"}', encoding="utf-8")
        (template_mod.TEMPLATE_DIR / "b.json").write_text("{bad", encoding="utf-8")
        (template_mod.TEMPLATE_DIR / "c.json").write_text('{"name": "c", "prompt": "p"}', encoding="utf-8")
        names = [t.name for t in _list_templates()]
        assert names == ["a", "c"]

    def test_list_empty_when_no_dir(self) -> None:
        assert _list_templates() == []

    def test_delete_template(self) -> None:
        tpl = PromptTemplate(name="x", prompt="p")
        _save_template(tpl)
        assert _delete_template("x") is True
        assert _delete_template("x") is False
        assert _list_templates() == []

    def test_file_contains_expected_json(self, tmp_path) -> None:
        template_mod.TEMPLATE_DIR = tmp_path / "templates"
        _save_template(PromptTemplate(name="y", prompt="hello", metadata={"k": "v"}))
        path = template_mod.TEMPLATE_DIR / "y.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["name"] == "y"
        assert data["metadata"] == {"k": "v"}
