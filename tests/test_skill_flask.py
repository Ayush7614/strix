"""Tests that the Flask framework skill loads and carries expected metadata.

Guards against the skill file drifting or being renamed out of the
``frameworks`` category, which would silently break agent skill selection.
"""

from __future__ import annotations

import pytest

from strix.skills import get_all_skill_names, load_skills


_EXPECTED_MARKERS = (
    "Werkzeug",
    "SECRET_KEY",
    "session",
    "SSTI",
)


def test_flask_skill_is_discoverable() -> None:
    assert "flask" in get_all_skill_names()


def test_flask_skill_loads_with_body() -> None:
    loaded = load_skills(["frameworks/flask"])
    assert "flask" in loaded
    body = loaded["flask"]
    assert body.strip()
    assert not body.startswith("---"), "frontmatter should be stripped on load"


@pytest.mark.parametrize("marker", _EXPECTED_MARKERS)
def test_flask_skill_covers_core_techniques(marker: str) -> None:
    loaded = load_skills(["frameworks/flask"])
    assert marker in loaded["flask"]
