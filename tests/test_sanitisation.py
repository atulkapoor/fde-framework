"""Guards on what may enter a public repository.

This project is seeded from confidential material and from research notes. Both
live outside the repo and must stay there. A one-time audit is the wrong
guarantee -- these run in CI on every commit.

The specific denylist of client and person names deliberately does *not* live
here: publishing a list of who a consultancy works with would leak the thing it
is meant to protect. It lives in an untracked file, read if present. What lives
here are the structural rules, which are safe to publish and catch the general
case.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# Only these may ever be tracked. Supplied material (inbox/, seed/), research and
# planning (docs/) and client work (engagements/) are excluded by construction
# rather than by remembering.
ALLOWED = (
    "src/",
    "tests/",
    "framework/",
    ".github/",
    "pyproject.toml",
    ".gitignore",
    "README.md",
    "LICENSE",
)

SECRET_PATTERNS = {
    "OpenAI-style key": r"\bsk-[A-Za-z0-9]{16,}",
    "Anthropic key": r"\bsk-ant-[A-Za-z0-9-]{16,}",
    "AWS access key": r"\bAKIA[0-9A-Z]{16}\b",
    "GitHub token": r"\bgh[pousr]_[A-Za-z0-9]{20,}",
    "Google API key": r"\bAIza[0-9A-Za-z_-]{30,}",
    "private key block": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "bearer literal": r"[Aa]uthorization\s*[:=]\s*[\"']?Bearer\s+[A-Za-z0-9._-]{20,}",
}

PII_PATTERNS = {
    # An email in source is either a real person or a placeholder; both are worth
    # a second look before the repo is public.
    "email address": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "long account-like digits": r"\b\d{12,19}\b",
    "local filesystem path": r"/(?:Users|home)/[A-Za-z0-9._-]+/",
}


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        cwd=REPO, capture_output=True, text=True, check=True,
    )
    return [line for line in out.stdout.splitlines() if line]


def tracked_text() -> dict[str, str]:
    text = {}
    for name in tracked_files():
        path = REPO / name
        if not path.exists():
            continue
        try:
            text[name] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            pytest.fail(f"{name}: binary file tracked; review before publishing")
    return text


def commit_messages() -> str:
    out = subprocess.run(
        ["git", "log", "--format=%B"], cwd=REPO, capture_output=True, text=True, check=True
    )
    return out.stdout


# --- what may be tracked -------------------------------------------------


def test_only_framework_paths_are_tracked():
    """Supplied material and research are excluded by construction."""
    stray = [f for f in tracked_files() if not f.startswith(ALLOWED)]
    assert not stray, f"tracked outside the framework: {stray}"


def test_no_supplied_material_anywhere_in_history():
    """git rm --cached leaves history intact. This is the check that catches that."""
    out = subprocess.run(
        ["git", "log", "--all", "--name-only", "--format=", "--", "seed/*", "inbox/*", "docs/*"],
        cwd=REPO, capture_output=True, text=True, check=True,
    )
    assert not out.stdout.strip(), f"supplied material still in history:\n{out.stdout[:400]}"


# --- what may be in the content -----------------------------------------


@pytest.mark.parametrize("label,pattern", SECRET_PATTERNS.items())
def test_no_credentials_in_tracked_files(label, pattern):
    for name, body in tracked_text().items():
        if name == "tests/test_sanitisation.py":
            continue  # this file names the patterns it looks for
        assert not re.search(pattern, body), f"{name}: looks like a {label}"


@pytest.mark.parametrize("label,pattern", PII_PATTERNS.items())
def test_no_personal_data_in_tracked_files(label, pattern):
    for name, body in tracked_text().items():
        if name == "tests/test_sanitisation.py":
            continue
        found = re.search(pattern, body)
        assert not found, f"{name}: {label} -- {found.group()!r}"


def test_denylisted_names_are_absent(denylist):
    """Client and person names from the supplied material.

    The list is untracked on purpose: publishing who a consultancy works with
    would leak exactly what this guard protects.
    """
    if not denylist:
        pytest.skip("no .sanitisation-denylist present")
    haystack = "\n".join(tracked_text().values()) + commit_messages()
    hits = [term for term in denylist if re.search(rf"\b{re.escape(term)}\b", haystack, re.I)]
    assert not hits, f"denylisted terms present: {hits}"


# --- authorship ----------------------------------------------------------


def test_no_commit_is_attributed_to_an_ai():
    """Every commit is the user's own work and says so."""
    out = subprocess.run(
        ["git", "log", "--format=%an%n%ae%n%cn%n%ce%n%B"],
        cwd=REPO, capture_output=True, text=True, check=True,
    )
    banned = ["claude", "anthropic", "co-authored-by", "generated with", "noreply@anthropic"]
    lowered = out.stdout.lower()
    present = [term for term in banned if term in lowered]
    assert not present, f"AI attribution in git history: {present}"


@pytest.fixture
def denylist() -> list[str]:
    path = REPO / ".sanitisation-denylist"
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
