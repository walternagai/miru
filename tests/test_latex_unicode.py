"""Tests for LaTeX to Unicode conversion."""

import pytest

from miru.latex_unicode import latex_to_unicode


class TestLatexToUnicode:
    """Tests for latex_to_unicode function."""

    def test_greek_letters(self) -> None:
        """Should convert Greek letters."""
        assert latex_to_unicode(r"\alpha") == "α"
        assert latex_to_unicode(r"\beta") == "β"
        assert latex_to_unicode(r"\gamma") == "γ"
        assert latex_to_unicode(r"\delta") == "δ"
        assert latex_to_unicode(r"\omega") == "ω"
        assert latex_to_unicode(r"\Omega") == "Ω"
        assert latex_to_unicode(r"\pi") == "π"
        assert latex_to_unicode(r"\theta") == "θ"

    def test_math_operators(self) -> None:
        """Should convert math operators."""
        assert latex_to_unicode(r"\pm") == "±"
        assert latex_to_unicode(r"\times") == "×"
        assert latex_to_unicode(r"\div") == "÷"
        assert latex_to_unicode(r"\cdot") == "·"
        assert latex_to_unicode(r"\leq") == "≤"
        assert latex_to_unicode(r"\geq") == "≥"
        assert latex_to_unicode(r"\neq") == "≠"
        assert latex_to_unicode(r"\approx") == "≈"

    def test_set_symbols(self) -> None:
        """Should convert set symbols."""
        assert latex_to_unicode(r"\in") == "∈"
        assert latex_to_unicode(r"\notin") == "∉"
        assert latex_to_unicode(r"\subset") == "⊂"
        assert latex_to_unicode(r"\supset") == "⊃"
        assert latex_to_unicode(r"\cup") == "∪"
        assert latex_to_unicode(r"\cap") == "∩"
        assert latex_to_unicode(r"\emptyset") == "∅"

    def test_arrows(self) -> None:
        """Should convert arrows."""
        assert latex_to_unicode(r"\rightarrow") == "→"
        assert latex_to_unicode(r"\leftarrow") == "←"
        assert latex_to_unicode(r"\Rightarrow") == "⇒"
        assert latex_to_unicode(r"\Leftarrow") == "⇐"
        assert latex_to_unicode(r"\Leftrightarrow") == "⇔"

    def test_subscript_simple(self) -> None:
        """Should convert simple subscripts."""
        assert latex_to_unicode("x_1") == "x₁"
        assert latex_to_unicode("x_2") == "x₂"
        assert latex_to_unicode("a_n") == "aₙ"
        assert latex_to_unicode("x_i") == "xᵢ"

    def test_subscript_brace(self) -> None:
        """Should convert braced subscripts."""
        assert latex_to_unicode(r"x_{1}") == "x₁"
        assert latex_to_unicode(r"x_{12}") == "x₁₂"
        assert latex_to_unicode(r"a_{n+1}") == "aₙ₊₁"

    def test_superscript_simple(self) -> None:
        """Should convert simple superscripts."""
        assert latex_to_unicode("x^2") == "x²"
        assert latex_to_unicode("x^3") == "x³"
        assert latex_to_unicode("e^n") == "eⁿ"

    def test_superscript_brace(self) -> None:
        """Should convert braced superscripts."""
        assert latex_to_unicode(r"x^{2}") == "x²"
        assert latex_to_unicode(r"x^{12}") == "x¹²"
        assert latex_to_unicode(r"a^{n+1}") == "aⁿ⁺¹"

    def test_combined_sub_super(self) -> None:
        """Should convert combined subscripts and superscripts."""
        assert latex_to_unicode("x_1^2") == "x₁²"
        assert latex_to_unicode("x_i^2") == "xᵢ²"
        assert latex_to_unicode("a_n^2 + b_n^2") == "aₙ² + bₙ²"

    def test_square_root(self) -> None:
        """Should convert square roots."""
        assert latex_to_unicode(r"\sqrt{x}") == "√(x)"
        assert latex_to_unicode(r"\sqrt{x^2 + y^2}") == "√(x² + y²)"

    def test_fraction(self) -> None:
        """Should convert fractions."""
        assert latex_to_unicode(r"\frac{a}{b}") == "(a)/(b)"
        assert latex_to_unicode(r"\frac{1}{2}") == "(1)/(2)"

    def test_complex_expression(self) -> None:
        """Should convert complex expressions."""
        result = latex_to_unicode(r"\frac{-b \pm \sqrt{b^2-4ac}}{2a}")
        assert "±" in result
        assert "√" in result

    def test_sum(self) -> None:
        """Should convert summation."""
        assert latex_to_unicode(r"\sum_{i=1}^n") == "∑ᵢ=₁ⁿ"
        result = latex_to_unicode(r"\sum_{i=1}^n x_i")
        assert "∑" in result
        assert "ᵢ" in result

    def test_integral(self) -> None:
        """Should convert integrals."""
        assert latex_to_unicode(r"\int") == "∫"
        result = latex_to_unicode(r"\int_0^\infty")
        assert "∫" in result
        assert "₀" in result

    def test_nabla(self) -> None:
        """Should convert nabla operator."""
        assert latex_to_unicode(r"\nabla") == "∇"
        assert latex_to_unicode(r"\nabla^2") == "∇²"

    def test_infinity(self) -> None:
        """Should convert infinity."""
        assert latex_to_unicode(r"\infty") == "∞"

    def test_dollar_signs(self) -> None:
        """Should remove dollar signs."""
        assert latex_to_unicode(r"$\alpha$") == "α"
        assert latex_to_unicode(r"$x^2$") == "x²"

    def test_whitespace_commands(self) -> None:
        """Should handle whitespace commands."""
        assert latex_to_unicode(r"\alpha \beta") == "α β"
        assert latex_to_unicode(r"a\,b") == "a b"

    def test_mixed_text_math(self) -> None:
        """Should handle mixed text and math."""
        result = latex_to_unicode(r"The energy is $E = mc^2$")
        assert "E = mc²" in result
        assert "energy" in result

    def test_quantum_mechanics(self) -> None:
        """Should convert quantum mechanics notation."""
        result = latex_to_unicode(r"\hbar")
        assert result == "ℏ"

    def test_logic_symbols(self) -> None:
        """Should convert logic symbols."""
        assert latex_to_unicode(r"\forall") == "∀"
        assert latex_to_unicode(r"\exists") == "∃"
        assert latex_to_unicode(r"\neg") == "¬"
        assert latex_to_unicode(r"\land") == "∧"
        assert latex_to_unicode(r"\lor") == "∨"

    def test_preserves_unknown_latex(self) -> None:
        """Should preserve unknown LaTeX commands."""
        result = latex_to_unicode(r"\unknowncommand")
        assert r"\unknowncommand" == result

    def test_propositional_logic_basic(self) -> None:
        """Should convert basic propositional logic symbols."""
        assert latex_to_unicode(r"\top") == "⊤"
        assert latex_to_unicode(r"\bot") == "⊥"
        assert latex_to_unicode(r"\neg p") == "¬ p"
        assert latex_to_unicode(r"\land") == "∧"
        assert latex_to_unicode(r"\lor") == "∨"

    def test_propositional_logic_implication(self) -> None:
        """Should convert implication symbols."""
        assert latex_to_unicode(r"\rightarrow") == "→"
        assert latex_to_unicode(r"\Rightarrow") == "⇒"
        assert latex_to_unicode(r"\implies") == "⟹"
        assert latex_to_unicode(r"\impliedby") == "⟸"
        assert latex_to_unicode(r"\iff") == "⟺"
        assert latex_to_unicode(r"\Leftrightarrow") == "⇔"
        assert latex_to_unicode(r"\Longleftrightarrow") == "⟺"

    def test_propositional_logic_derivation(self) -> None:
        """Should convert derivation/provability symbols."""
        assert latex_to_unicode(r"\vdash") == "⊢"
        assert latex_to_unicode(r"\dashv") == "⊣"
        assert latex_to_unicode(r"\models") == "⊨"
        assert latex_to_unicode(r"\nvdash") == "⊭"
        assert latex_to_unicode(r"\Vdash") == "⊩"
        assert latex_to_unicode(r"\VDash") == "⊫"

    def test_propositional_logic_parentheses(self) -> None:
        """Should convert alternative conjunction/disjunction."""
        assert latex_to_unicode(r"\veebar") == "⊻"
        assert latex_to_unicode(r"\barwedge") == "⊼"
        assert latex_to_unicode(r"\bigwedge") == "⋀"
        assert latex_to_unicode(r"\bigvee") == "⋁"

    def test_propositional_logic_modal(self) -> None:
        """Should convert modal logic symbols."""
        assert latex_to_unicode(r"\Box") == "□"
        assert latex_to_unicode(r"\Diamond") == "◇"
        assert latex_to_unicode(r"\blacksquare") == "■"

    def test_propositional_logic_inference(self) -> None:
        """Should convert inference symbols."""
        assert latex_to_unicode(r"\therefore") == "∴"
        assert latex_to_unicode(r"\because") == "∵"

    def test_propositional_expression(self) -> None:
        """Should convert full propositional expressions."""
        result = latex_to_unicode(r"(p \land q) \rightarrow (r \lor s)")
        assert result == "(p ∧ q) → (r ∨ s)"

        result = latex_to_unicode(r"\vdash p \Rightarrow q")
        assert result == "⊢ p ⇒ q"

        result = latex_to_unicode(r"\models (p \land q) \Leftrightarrow (q \land p)")
        assert "⊨" in result
        assert "∧" in result
        assert "⇔" in result