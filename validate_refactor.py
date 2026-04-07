#!/usr/bin/env python3
"""Validation script for refactored modules.

Tests basic functionality of:
- i18n system
- Core modules (config, errors)
- UI modules (render, progress)
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def test_i18n() -> bool:
    """Test internationalization system."""
    from miru.core.i18n import t, set_language, detect_language, SUPPORTED_LANGUAGES
    
    print("Testing i18n...")
    
    # Test detection
    detected = detect_language()
    print(f"  ✓ Detected language: {detected}")
    assert detected in SUPPORTED_LANGUAGES
    
    # Test all supported languages
    for lang in SUPPORTED_LANGUAGES:
        set_language(lang)
        msg = t("error.model_not_found", model="test")
        assert msg, f"No message for {lang}"
        print(f"  ✓ {lang}: {msg[:40]}...")
    
    # Test fallback
    set_language("invalid_lang")
    msg = t("error.model_not_found", model="test")
    assert msg, "No fallback message"
    print("  ✓ Fallback to default works")
    
    return True


def test_core_errors() -> bool:
    """Test core error classes."""
    from miru.core.errors import (
        MiruError,
        ModelNotFoundError,
        ConnectionError,
        ValidationError,
    )
    from miru.core.i18n import set_language
    
    print("\nTesting core errors...")
    
    set_language("en_US")
    
    # Test ModelNotFoundError
    err = ModelNotFoundError("gemma3", ["llama3", "qwen2"])
    assert "gemma3" in err.message
    assert err.suggestion
    print("  ✓ ModelNotFoundError creates message and suggestion")
    
    # Test ConnectionError
    err = ConnectionError("http://localhost:11434")
    assert "localhost" in err.message
    assert err.suggestion
    print("  ✓ ConnectionError creates message and suggestion")
    
    # Test ValidationError
    err = ValidationError("Invalid value", field="test")
    assert err.message == "Invalid value"
    print("  ✓ ValidationError works")
    
    # Test MiruError base
    err = MiruError("Test error", suggestion="Try this")
    assert "Test error" in str(err)
    assert "Try this" in str(err)
    print("  ✓ MiruError base class works")
    
    return True


def test_core_config() -> bool:
    """Test core configuration."""
    from miru.core.config import Config, load_config, get_config_value
    
    print("\nTesting core config...")
    
    # Test default config
    config = Config()
    assert config.default_host == "http://localhost:11434"
    print("  ✓ Config defaults work")
    
    # Test load
    loaded = load_config()
    assert isinstance(loaded, Config)
    print("  ✓ Config loads successfully")
    
    # Test get_config_value
    host = get_config_value("default_host")
    assert host, "No host value"
    print("  ✓ get_config_value works")
    
    return True


def test_ui_render() -> bool:
    """Test UI rendering functions."""
    from miru.ui.render import render_error, render_success, render_warning, render_info
    from miru.core.i18n import set_language, t
    import io
    from contextlib import redirect_stdout
    
    print("\nTesting UI render...")
    
    set_language("pt_BR")
    
    # Capture output
    output = io.StringIO()
    
    with redirect_stdout(output):
        render_success(t("success.session_saved", filename="test.json"))
    assert "✓" in output.getvalue()
    print("  ✓ render_success works")
    
    output = io.StringIO()
    with redirect_stdout(output):
        render_error(t("error.model_not_found", model="test"))
    assert "✗" in output.getvalue()
    print("  ✓ render_error works")
    
    output = io.StringIO()
    with redirect_stdout(output):
        render_warning("Test warning")
    assert "⚠" in output.getvalue()
    print("  ✓ render_warning works")
    
    output = io.StringIO()
    with redirect_stdout(output):
        render_info("Test info")
    assert "ℹ" in output.getvalue()
    print("  ✓ render_info works")
    
    return True


def test_ui_prompts() -> bool:
    """Test UI prompt utilities (import only)."""
    from miru.ui.prompts import confirm, prompt_input, prompt_choice
    
    print("\nTesting UI prompts...")
    print("  ✓ Imports successful (interactive tests skipped)")
    
    return True


def test_ui_progress() -> bool:
    """Test UI progress utilities (import only)."""
    from miru.ui.progress import ProgressReporter, create_progress, track_progress
    
    print("\nTesting UI progress...")
    print("  ✓ Imports successful")
    
    # Test creation
    reporter = ProgressReporter("Test")
    assert reporter.description == "Test"
    print("  ✓ ProgressReporter instantiation works")
    
    progress = create_progress("Test")
    assert progress is not None
    print("  ✓ create_progress works")
    
    return True


def test_cli_options() -> bool:
    """Test CLI options module."""
    from miru.cli_options import Host, Quiet, Model, Temperature
    
    print("\nTesting CLI options...")
    print("  ✓ All options imported successfully")
    
    return True


def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print("Validating miru refactored modules")
    print("=" * 60)
    
    tests = [
        test_i18n,
        test_core_errors,
        test_core_config,
        test_ui_render,
        test_ui_prompts,
        test_ui_progress,
        test_cli_options,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())