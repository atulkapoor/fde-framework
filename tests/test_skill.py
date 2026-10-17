"""The skill a coding agent loads, held to the framework it describes:
every command it names exists, every tool it names is served, the
commands it forbids are the ones that write a project, the manifests
point at it, and DECLINED.md names releases that happened."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from fde.cli import app

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "fde" / "SKILL.md"
FRONT = re.compile(r"^---\n(.*?)\n---\n", re.S)


def commands_in_cli() -> set[str]:
    group = __import__("typer").main.get_command(app)
    return set(group.commands)


def test_the_skill_has_the_frontmatter_an_agent_reads():
    front = FRONT.match(SKILL.read_text())
    assert front, "SKILL.md starts with YAML frontmatter"
    meta = yaml.safe_load(front.group(1))
    assert meta["name"] == "fde" and re.fullmatch(r"[a-z][a-z0-9-]{0,63}", meta["name"])
    assert 50 < len(meta["description"]) <= 1024
    assert "Never builds" in meta["description"]


def test_every_command_the_skill_names_exists_and_every_tool_is_served():
    from fde.mcp_server import TOOLS

    text = SKILL.read_text()
    named = set(re.findall(r"`fde ([a-z-]+)", text))
    missing = named - commands_in_cli() - {"--version"}
    assert not missing, f"the skill names commands that do not exist: {sorted(missing)}"
    tools = re.findall(r"`(triage|start|frame|status|next|stage|debt|stop_when|history)`", text)
    assert set(tools) == set(TOOLS), "the skill names every served tool and no other"


def test_the_skill_puts_building_and_signing_in_the_persons_hands():
    """Stated as whose act each thing is, not as a prohibition: a ban drags
    the banned act into context; a hand-over names who acts."""
    text = SKILL.read_text()
    theirs = text[text.index("## Whose act each thing is"):text.index("## One exchange")]
    for command in ("fde build", "fde implement", "fde waive"):
        assert command in theirs, command
    assert "yours to run" in theirs and "Never" not in theirs
    steps = text[text.index("## What to do, in order"):text.index("## Whose act each thing is")]
    for command in ("fde build", "fde implement", "fde waive"):
        assert command not in steps, f"{command} appears as something to do"
    assert " ".join(steps.split()).count("Done when") == 6, "every step ends on done"


def test_the_manifests_point_at_the_skill_and_agree_on_the_name():
    plugin = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())
    market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    assert plugin["name"] == "fde" and plugin["license"] == "Apache-2.0"
    for entry in plugin["skills"]:
        assert (REPO / entry / "SKILL.md").exists(), entry
    assert [p["name"] for p in market["plugins"]] == ["fde"]
    assert market["plugins"][0]["source"] == "./"
    import tomllib

    version = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["version"]
    assert plugin["version"] == version, "the plugin's version is the package's"


def test_declined_names_releases_that_happened_and_states_the_bar():
    text = (REPO / "DECLINED.md").read_text()
    assert "## The bar" in text and "## Declined" in text
    changelog = (REPO / "CHANGELOG.md").read_text()
    released = set(re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.M))
    cited = set(re.findall(r"\b0\.1\.\d+\b", text[text.index("## Declined"):]))
    unknown = cited - released
    assert not unknown, f"DECLINED.md cites releases the changelog does not have: {unknown}"
    rows = [line for line in text.splitlines() if line.startswith("| ") and "|---" not in line]
    assert len(rows) >= 12
