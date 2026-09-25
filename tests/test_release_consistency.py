"""One version, in every place that states it. Two tags this week had to
be moved after the fact; this fails before the tag instead."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_pyproject_citation_and_changelog_agree_on_the_version():
    version = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["version"]
    citation = re.search(r"^version: (\S+)$", (REPO / "CITATION.cff").read_text(), re.M)
    assert citation and citation.group(1) == version, "CITATION.cff lags pyproject.toml"
    latest = re.search(r"^## \[(\d+\.\d+\.\d+)\]", (REPO / "CHANGELOG.md").read_text(), re.M)
    assert latest and latest.group(1) == version, "CHANGELOG.md's newest entry lags the version"
