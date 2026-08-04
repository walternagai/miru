"""Pytest shared fixtures for miru tests."""

import pytest

from miru.core.i18n import get_language, set_language


@pytest.fixture(autouse=True)
def _restore_i18n_language():
    """Restore the global i18n language after each test.

    Many tests call ``set_language(...)`` (e.g. test_commands_i18n.py) and
    leave the module-level language changed, leaking state into other tests
    (e.g. test_renderer.py passes alone but fails in the full suite).
    """
    previous = get_language()
    yield
    set_language(previous)
