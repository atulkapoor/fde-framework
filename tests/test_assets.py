"""The images say what the code says. The README banner and the social
card carried "seven gates" for fifteen releases after the eighth gate
shipped, because they had been drawn once by hand; an outside reader
found the banner contradicting the README it headed. Each image now
carries its words in a PNG text chunk, and this holds them to the gate
count the gates module reports."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("PIL", reason="Pillow draws the assets")

from PIL import Image  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def brand():
    spec = importlib.util.spec_from_file_location("brand", REPO / "assets" / "brand.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_banners_and_the_social_card_name_the_gate_count_the_code_has():
    expected = brand().pipeline()
    assert "gates" in expected
    for name in ("banner-light", "banner-dark", "social-preview"):
        with Image.open(REPO / "assets" / f"{name}.png") as image:
            words = image.text.get("fde:words")
        assert words == expected, (
            f"assets/{name}.png says {words!r}, the code says {expected!r}: "
            "run .venv/bin/python assets/brand.py and commit the images")
