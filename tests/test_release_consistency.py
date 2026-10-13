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
    import json

    plugin = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())
    assert plugin["version"] == version, ".claude-plugin/plugin.json lags pyproject.toml"


def test_citation_and_changelog_agree_on_the_date_and_it_is_not_ahead_of_today():
    """0.1.44 shipped on October 11 dated October 12, in both files, and an
    outside reader noticed before I did. The two files must agree, and the
    date may not be in the future; the release workflow goes further and
    holds it to the day the tagged commit was authored."""
    from datetime import date, timedelta

    changelog = re.search(r"^## \[\d+\.\d+\.\d+\] — (\d{4}-\d{2}-\d{2})",
                          (REPO / "CHANGELOG.md").read_text(), re.M)
    assert changelog, "the newest CHANGELOG entry carries no date"
    citation = re.search(r"^date-released: '(\d{4}-\d{2}-\d{2})'$",
                         (REPO / "CITATION.cff").read_text(), re.M)
    assert citation and citation.group(1) == changelog.group(1), \
        "CITATION.cff date-released != the newest CHANGELOG date"
    released = date.fromisoformat(changelog.group(1))
    # A day of slack: the author's calendar and the test runner's need not
    # agree at midnight.
    assert released <= date.today() + timedelta(days=1), f"{released} has not happened yet"
