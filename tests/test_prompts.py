"""Tests for miru/ui/prompts.py — interactive prompt helpers."""

from unittest.mock import patch

from miru.ui.prompts import confirm, prompt_choice, prompt_input, prompt_multiselect


class TestConfirm:
    def test_yes(self) -> None:
        with patch("miru.ui.prompts.Prompt.ask", return_value="y"):
            assert confirm("Delete?") is True

    def test_no(self) -> None:
        with patch("miru.ui.prompts.Prompt.ask", return_value="n"):
            assert confirm("Delete?") is False

    def test_uppercase_yes(self) -> None:
        with patch("miru.ui.prompts.Prompt.ask", return_value="Y"):
            assert confirm("Delete?") is True


class TestPromptInput:
    def test_returns_value(self) -> None:
        with patch("miru.ui.prompts.Prompt.ask", return_value="hello"):
            assert prompt_input("Name:") == "hello"

    def test_password_flag_passed(self) -> None:
        with patch("miru.ui.prompts.Prompt.ask", return_value="secret") as mock_ask:
            prompt_input("Password:", password=True)
            assert mock_ask.call_args.kwargs.get("password") is True


class TestPromptChoice:
    def test_returns_choice(self) -> None:
        with patch("miru.ui.prompts.Prompt.ask", return_value="en_US"):
            assert prompt_choice("Lang:", ["pt_BR", "en_US"], default="en_US") == "en_US"

    def test_choices_passed(self) -> None:
        with patch("miru.ui.prompts.Prompt.ask", return_value="a") as mock_ask:
            prompt_choice("Pick:", ["a", "b"])
            assert mock_ask.call_args.kwargs.get("choices") == ["a", "b"]


class TestPromptMultiselect:
    def test_empty_answer_returns_defaults(self) -> None:
        with patch("miru.ui.prompts.Prompt.ask", return_value=""):
            assert prompt_multiselect("Pick:", ["a", "b"], defaults=["a"]) == ["a"]

    def test_parses_indices(self) -> None:
        with patch("miru.ui.prompts.Prompt.ask", return_value="1 3"):
            assert prompt_multiselect("Pick:", ["a", "b", "c"]) == ["a", "c"]

    def test_out_of_range_indices_ignored(self) -> None:
        with patch("miru.ui.prompts.Prompt.ask", return_value="1 99"):
            assert prompt_multiselect("Pick:", ["a", "b"]) == ["a"]

    def test_invalid_input_returns_defaults(self) -> None:
        with patch("miru.ui.prompts.Prompt.ask", return_value="abc"):
            assert prompt_multiselect("Pick:", ["a"], defaults=["a"]) == ["a"]
