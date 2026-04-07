"""Convert LaTeX equations to Unicode symbols."""

import re
from typing import Final

LATEX_SYMBOLS: Final[dict[str, str]] = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "zeta": "ζ",
    "eta": "η",
    "theta": "θ",
    "iota": "ι",
    "kappa": "κ",
    "lambda": "λ",
    "mu": "μ",
    "nu": "ν",
    "xi": "ξ",
    "omicron": "ο",
    "pi": "π",
    "rho": "ρ",
    "sigma": "σ",
    "tau": "τ",
    "upsilon": "υ",
    "phi": "φ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω",
    "Alpha": "Α",
    "Beta": "Β",
    "Gamma": "Γ",
    "Delta": "Δ",
    "Epsilon": "Ε",
    "Zeta": "Ζ",
    "Eta": "Η",
    "Theta": "Θ",
    "Iota": "Ι",
    "Kappa": "Κ",
    "Lambda": "Λ",
    "Mu": "Μ",
    "Nu": "Ν",
    "Xi": "Ξ",
    "Omicron": "Ο",
    "Pi": "Π",
    "Rho": "Ρ",
    "Sigma": "Σ",
    "Tau": "Τ",
    "Upsilon": "Υ",
    "Phi": "Φ",
    "Chi": "Χ",
    "Psi": "Ψ",
    "Omega": "Ω",
    "infty": "∞",
    "partial": "∂",
    "nabla": "∇",
    "hbar": "ℏ",
    "pm": "±",
    "mp": "∓",
    "times": "×",
    "div": "÷",
    "cdot": "·",
    "ast": "∗",
    "star": "⋆",
    "circ": "∘",
    "bullet": "•",
    "oplus": "⊕",
    "otimes": "⊗",
    "odot": "⊙",
    "oslash": "⊘",
    "leq": "≤",
    "geq": "≥",
    "neq": "≠",
    "equiv": "≡",
    "approx": "≈",
    "sim": "∼",
    "propto": "∝",
    "parallel": "∥",
    "perp": "⊥",
    "in": "∈",
    "notin": "∉",
    "ni": "∋",
    "subset": "⊂",
    "supset": "⊃",
    "subseteq": "⊆",
    "supseteq": "⊇",
    "cup": "∪",
    "cap": "∩",
    "setminus": "∖",
    "emptyset": "∅",
    "forall": "∀",
    "exists": "∃",
    "nexists": "∄",
    "neg": "¬",
    "land": "∧",
    "lor": "∨",
    "Rightarrow": "⇒",
    "Leftarrow": "⇐",
    "Leftrightarrow": "⇔",
    "rightarrow": "→",
    "leftarrow": "←",
    "leftrightarrow": "↔",
    "uparrow": "↑",
    "downarrow": "↓",
    "updownarrow": "↕",
    "sum": "∑",
    "prod": "∏",
    "int": "∫",
    "iint": "∬",
    "iiint": "∭",
    "oint": "∮",
    "sqrt": "√",
    "degree": "°",
    "prime": "′",
    "doubleprime": "″",
    "ell": "ℓ",
    "Re": "ℜ",
    "Im": "ℑ",
    "aleph": "ℵ",
    "wp": "℘",
    "dag": "†",
    "ddag": "‡",
    "S": "§",
    "P": "¶",
    "copyright": "©",
    "registered": "®",
    "trademark": "™",
    "top": "⊤",
    "bot": "⊥",
    "true": "⊤",
    "false": "⊥",
    "models": "⊨",
    "vdash": "⊢",
    "dashv": "⊣",
    "Vdash": "⊩",
    "Dashv": "⊪",
    "VDash": "⊫",
    "nvdash": "⊭",
    "nVdash": "⊮",
    "nDashv": "⊯",
    "nVDash": "⊭",
    "therefore": "∴",
    "because": "∵",
    "veebar": "⊻",
    "barwedge": "⊼",
    "doublebarwedge": "⊽",
    "curlywedge": "⋏",
    "curlyvee": "⋎",
    "bigwedge": "⋀",
    "bigvee": "⋁",
    "Box": "□",
    "Diamond": "◇",
    "blacksquare": "■",
    "blacklozenge": "◆",
    "lozenge": "◊",
    "triangle": "△",
    "blacktriangle": "▲",
    "varnothing": "∅",
    "iff": "⟺",
    "impliedby": "⟸",
    "implies": "⟹",
    "Longleftrightarrow": "⟺",
}

SUBSCRIPT_DIGITS: Final[dict[str, str]] = {
    "0": "₀",
    "1": "₁",
    "2": "₂",
    "3": "₃",
    "4": "₄",
    "5": "₅",
    "6": "₆",
    "7": "₇",
    "8": "₈",
    "9": "₉",
}

SUPERSCRIPT_DIGITS: Final[dict[str, str]] = {
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
}

SUBSCRIPT_LETTERS: Final[dict[str, str]] = {
    "a": "ₐ",
    "e": "ₑ",
    "h": "ₕ",
    "i": "ᵢ",
    "j": "ⱼ",
    "k": "ₖ",
    "l": "ₗ",
    "m": "ₘ",
    "n": "ₙ",
    "o": "ₒ",
    "p": "ₚ",
    "r": "ₛ",
    "t": "ₜ",
    "u": "ᵤ",
    "v": "ᵥ",
    "x": "ₓ",
}

SUPERSCRIPT_LETTERS: Final[dict[str, str]] = {
    "a": "ᵃ",
    "b": "ᵇ",
    "c": "ᶜ",
    "d": "ᵈ",
    "e": "ᵉ",
    "f": "ᶠ",
    "g": "ᵍ",
    "h": "ʰ",
    "i": "ⁱ",
    "j": "ʲ",
    "k": "ᵏ",
    "l": "ˡ",
    "m": "ᵐ",
    "n": "ⁿ",
    "o": "ᵒ",
    "p": "ᵖ",
    "r": "ʳ",
    "s": "ˢ",
    "t": "ᵗ",
    "u": "ᵘ",
    "v": "ᵛ",
    "w": "ʷ",
    "x": "ˣ",
    "y": "ʸ",
    "z": "ᶻ",
}


def _convert_subscript(content: str) -> str:
    """Convert subscript content to Unicode."""
    result = []
    i = 0
    while i < len(content):
        char = content[i]
        if char in SUBSCRIPT_DIGITS:
            result.append(SUBSCRIPT_DIGITS[char])
        elif char in SUBSCRIPT_LETTERS:
            result.append(SUBSCRIPT_LETTERS[char])
        elif char == "+":
            result.append("₊")
        elif char == "-":
            result.append("₋")
        else:
            result.append(char)
        i += 1
    return "".join(result)


def _convert_superscript(content: str) -> str:
    """Convert superscript content to Unicode."""
    result = []
    i = 0
    while i < len(content):
        char = content[i]
        if char in SUPERSCRIPT_DIGITS:
            result.append(SUPERSCRIPT_DIGITS[char])
        elif char in SUPERSCRIPT_LETTERS:
            result.append(SUPERSCRIPT_LETTERS[char])
        elif char == "+":
            result.append("⁺")
        elif char == "-":
            result.append("⁻")
        elif char == "=":
            result.append("⁼")
        else:
            result.append(char)
        i += 1
    return "".join(result)


def _find_matching_brace(text: str, start: int) -> int:
    """Find matching closing brace for opening brace at start."""
    if start >= len(text) or text[start] != "{":
        return -1
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def latex_to_unicode(text: str) -> str:
    """Convert LaTeX math expressions to Unicode symbols.

    Args:
        text: Text potentially containing LaTeX math expressions

    Returns:
        Text with LaTeX converted to Unicode where possible

    Examples:
        >>> latex_to_unicode(r"$\\alpha + \\beta = \\gamma$")
        'α + β = γ'
        >>> latex_to_unicode(r"$x_1^2 + x_2^2$")
        'x₁² + x₂²'
        >>> latex_to_unicode(r"$\\nabla^2 \\\\phi = \\\\rho/\\\\epsilon_0$")
        '∇² φ = ρ/ε₀'
    """
    result = text
    
    sqrt_n_pattern = re.compile(r"\\sqrt\[(\d+)\]\{([^{}]+)\}")
    for match in list(sqrt_n_pattern.finditer(result)):
        expr = match.group(2)
        replacement = f"({expr})^(1/{match.group(1)})"
        result = result.replace(match.group(0), replacement, 1)

    def process_sqrt_nested(text: str) -> str:
        while True:
            match = re.search(r"\\sqrt\{([^{}]+)\}", text)
            if not match:
                break
            expr = match.group(1).strip()
            replacement = f"√({expr})"
            text = text[:match.start()] + replacement + text[match.end():]
        return text

    result = process_sqrt_nested(result)

    def process_frac_nested(text: str) -> str:
        while True:
            match = re.search(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", text)
            if not match:
                break
            num = match.group(1).strip()
            den = match.group(2).strip()
            replacement = f"({num})/({den})"
            text = text[:match.start()] + replacement + text[match.end():]
        return text

    result = process_frac_nested(result)

    for latex in sorted(LATEX_SYMBOLS.keys(), key=len, reverse=True):
        unicode_char = LATEX_SYMBOLS[latex]
        result = result.replace(f"\\{latex}", unicode_char)

    while True:
        match = re.search(r"_\{([^}]+)\}", result)
        if not match:
            break
        replacement = _convert_subscript(match.group(1))
        result = result[:match.start()] + replacement + result[match.end():]

    while True:
        match = re.search(r"\^\{([^}]+)\}", result)
        if not match:
            break
        replacement = _convert_superscript(match.group(1))
        result = result[:match.start()] + replacement + result[match.end():]

    while True:
        match = re.search(r"_(\w)", result)
        if not match:
            break
        char = match.group(1)
        if char in SUBSCRIPT_DIGITS:
            replacement = SUBSCRIPT_DIGITS[char]
        elif char in SUBSCRIPT_LETTERS:
            replacement = SUBSCRIPT_LETTERS[char]
        else:
            break
        result = result[:match.start()] + replacement + result[match.end():]

    while True:
        match = re.search(r"\^(\w)", result)
        if not match:
            break
        char = match.group(1)
        if char in SUPERSCRIPT_DIGITS:
            replacement = SUPERSCRIPT_DIGITS[char]
        elif char in SUPERSCRIPT_LETTERS:
            replacement = SUPERSCRIPT_LETTERS[char]
        else:
            break
        result = result[:match.start()] + replacement + result[match.end():]

    result = re.sub(r"\$([^$]+)\$", r"\1", result)
    result = re.sub(r"\\\[(.+?)\\\]", r"\1", result, flags=re.DOTALL)

    result = result.replace("\\(", "")
    result = result.replace("\\)", "")
    result = result.replace("\\ ", " ")
    result = result.replace("\\!", "")
    result = result.replace("\\,", " ")
    result = result.replace("\\;", " ")
    result = result.replace("\\:", " ")

    return result