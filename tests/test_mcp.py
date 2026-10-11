"""The framework inside a coding agent: each tool is the command of the
same name, in-process, returning what the terminal would print."""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("mcp", reason="the MCP extra is not installed")

from fde.mcp_server import build_server, run_command  # noqa: E402


def call(server, tool, **arguments) -> str:
    result = asyncio.run(server.call_tool(tool, arguments))
    return "".join(getattr(part, "text", "") for part in result.content)


def test_the_server_offers_the_conversational_commands_and_nothing_that_builds():
    server = build_server()
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert names == {"triage", "start", "frame", "status", "next", "stage", "debt",
                     "stop_when", "history"}
    assert not names & {"build", "implement", "deploy", "architect"}


def test_triage_ranks_statements_as_the_command_does():
    server = build_server()
    text = call(server, "triage", statements=[
        "Route each inbound support message to one of seventy-seven queues; "
        "customer data may not leave our cloud account.",
        "Answer staff questions from 400 policy PDFs inside the firewall."])
    assert "ranked by what the statement already settles" in text
    assert "1." in text and "2." in text and "decidability, not value" in text


def test_start_status_and_next_walk_an_engagement(tmp_path, monkeypatch):
    monkeypatch.setenv("FDE_WORKSPACE", str(tmp_path))
    server = build_server()
    opened = call(server, "start", name="acme", base=str(tmp_path),
                  statement="Extract fields from scanned supplier invoices; data cannot leave.")
    assert "acme" in opened
    root = str(tmp_path / "acme")
    status = call(server, "status", engagement=root)
    assert "blocked by" in status
    nxt = call(server, "next", engagement=root)
    assert nxt.startswith("next: fde ")
    stage = call(server, "stage", engagement=root)
    assert "acme: discovery" in stage
    debt = call(server, "debt", engagement=root)
    assert "decision debt as of" in debt
    history = call(server, "history", engagement=root)
    assert "acme: history" in history
    stop = call(server, "stop_when", engagement=root)
    assert "no stop conditions on record" in stop


def test_a_refusal_comes_back_as_the_command_printed_it(tmp_path):
    text, status = run_command(["status", str(tmp_path / "nowhere")])
    assert "[fde exited" in text and "nowhere" in text and status == "blocked"


def test_the_thirty_second_resource_is_served():
    server = build_server()
    uris = {str(r.uri) for r in asyncio.run(server.list_resources())}
    assert "fde://thirty-seconds" in uris
    content = asyncio.run(server.read_resource("fde://thirty-seconds"))
    assert any("refuses to build" in getattr(c, "content", "") for c in content)


# --- the agent is not a person: every path it supplies stays inside the workspace


def test_paths_outside_the_workspace_are_refused_in_words(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setenv("FDE_WORKSPACE", str(workspace))
    server = build_server()
    before = sorted(p.name for p in tmp_path.iterdir())
    for base in ("../outside", str(outside), "../../", "/tmp/anywhere"):
        text = call(server, "start", name="acme", base=base, statement="Route each message.")
        assert text.startswith("refused:") and "outside the workspace" in text, (base, text)
    for engagement in ("../outside", str(outside), "/etc"):
        for tool in ("status", "next", "stage", "debt", "stop_when", "history"):
            text = call(server, tool, engagement=engagement)
            assert text.startswith("refused:"), (tool, engagement, text)
        text = call(server, "frame", engagement=engagement, text="Five hundred PDFs a day.")
        assert text.startswith("refused:")
    assert sorted(p.name for p in tmp_path.iterdir()) == before  # nothing written outside
    assert not any(outside.iterdir())


def test_a_symlink_inside_pointing_outside_is_outside(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / "link").symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv("FDE_WORKSPACE", str(workspace))
    server = build_server()
    text = call(server, "start", name="acme", base="link", statement="Route each message.")
    assert text.startswith("refused:") and not any(outside.iterdir())


def test_engagement_names_are_plain_names(tmp_path, monkeypatch):
    monkeypatch.setenv("FDE_WORKSPACE", str(tmp_path))
    server = build_server()
    for name in ("../x", "a/b", "", ".", "x" * 70, "a b"):
        text = call(server, "start", name=name, base="engagements", statement="Route.")
        assert text.startswith("refused:") and "plain name" in text, (name, text)
    assert not (tmp_path / "engagements").exists() or not any(
        (tmp_path / "engagements").iterdir())
    ok = call(server, "start", name="acme-2", base="engagements", statement="Route.")
    assert "acme-2" in ok and (tmp_path / "engagements" / "acme-2").is_dir()


def test_relative_paths_are_taken_from_the_workspace_not_the_cwd(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setenv("FDE_WORKSPACE", str(workspace))
    monkeypatch.chdir(tmp_path)  # a different cwd must not change where things land
    server = build_server()
    call(server, "start", name="acme", base="engagements", statement="Route each message.")
    assert (workspace / "engagements" / "acme").is_dir()
    assert not (tmp_path / "engagements").exists()
    status = call(server, "status", engagement="engagements/acme")
    assert "blocked by" in status


def test_the_writing_tools_say_so_and_carry_the_hints():
    server = build_server()
    tools = {t.name: t for t in asyncio.run(server.list_tools())}
    for name in ("start", "frame"):
        assert tools[name].description.startswith("WRITES:")
        assert tools[name].annotations.read_only_hint is False
    for name in ("triage", "status", "next", "stage", "debt", "stop_when", "history"):
        assert tools[name].annotations.read_only_hint is True, name


def test_the_check_mode_lists_what_is_served_without_serving(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from fde.cli import app

    monkeypatch.setenv("FDE_WORKSPACE", str(tmp_path))
    result = CliRunner().invoke(app, ["mcp", "--check"])
    assert result.exit_code == 0, result.output
    assert f"workspace {tmp_path.resolve()}" in result.output
    assert "start      writes" in result.output and "status     reads" in result.output


# --- the contract: what a tool says it does is what it does


def snapshot(root):
    import hashlib
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def test_read_only_tools_change_nothing_and_writing_tools_say_they_did(tmp_path, monkeypatch):
    monkeypatch.setenv("FDE_WORKSPACE", str(tmp_path))
    server = build_server()
    result = asyncio.run(server.call_tool("start", {"name": "acme", "base": "engagements",
                                                     "statement": "Route each message."}))
    assert result.structured_content["mutated"] is True
    root = tmp_path / "engagements" / "acme"
    before = snapshot(root)
    tools = {t.name: t for t in asyncio.run(server.list_tools())}
    for name, arguments in (("status", {}), ("next", {}), ("stage", {}), ("debt", {}),
                            ("stop_when", {}), ("history", {})):
        assert tools[name].annotations.read_only_hint is True
        result = asyncio.run(server.call_tool(name, {"engagement": "engagements/acme",
                                                     **arguments}))
        assert result.structured_content["mutated"] is False, name
        assert snapshot(root) == before, f"{name} changed the record while marked read-only"
    assert not (root / "lifecycle.jsonl").exists()  # stage previewed, nothing appended
    result = asyncio.run(server.call_tool("frame", {"engagement": "engagements/acme",
                                                     "text": "Five hundred PDFs a day arrive."}))
    assert tools["frame"].annotations.read_only_hint is False
    assert result.structured_content["mutated"] is True and snapshot(root) != before


def test_every_reply_carries_a_status_an_agent_can_branch_on(tmp_path, monkeypatch):
    monkeypatch.setenv("FDE_WORKSPACE", str(tmp_path))
    server = build_server()
    ok = asyncio.run(server.call_tool("triage", {"statements": ["Route messages.", "Read PDFs."]}))
    assert ok.structured_content["status"] == "ok" and not ok.is_error
    refused = asyncio.run(server.call_tool("status", {"engagement": "/etc"}))
    assert refused.structured_content["status"] == "refused"
    assert refused.structured_content["mutated"] is False
    blocked = asyncio.run(server.call_tool("status", {"engagement": "engagements/nowhere"}))
    assert blocked.structured_content["status"] == "blocked"
    assert "[fde exited" in blocked.content[0].text
    assert all("workspace" in r.structured_content for r in (ok, refused, blocked))


def test_starting_an_existing_engagement_cannot_overwrite_it(tmp_path, monkeypatch):
    monkeypatch.setenv("FDE_WORKSPACE", str(tmp_path))
    server = build_server()
    call(server, "start", name="acme", base="engagements", statement="Route each message.")
    root = tmp_path / "engagements" / "acme"
    call(server, "frame", engagement="engagements/acme", text="Five hundred PDFs a day arrive.")
    before = snapshot(root)
    again = asyncio.run(server.call_tool("start", {"name": "acme", "base": "engagements",
                                                    "statement": "Something else entirely."}))
    assert again.structured_content["status"] == "blocked"
    assert again.structured_content["mutated"] is False
    assert "already exists" in again.content[0].text
    assert snapshot(root) == before


def test_check_mode_creates_nothing(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from fde.cli import app

    monkeypatch.setenv("FDE_WORKSPACE", str(tmp_path))
    result = CliRunner().invoke(app, ["mcp", "--check"])
    assert result.exit_code == 0 and not any(tmp_path.iterdir())
