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


def test_start_status_and_next_walk_an_engagement(tmp_path):
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
    text = run_command(["status", str(tmp_path / "nowhere")])
    assert "[fde exited" in text and "nowhere" in text


def test_the_thirty_second_resource_is_served():
    server = build_server()
    uris = {str(r.uri) for r in asyncio.run(server.list_resources())}
    assert "fde://thirty-seconds" in uris
    content = asyncio.run(server.read_resource("fde://thirty-seconds"))
    assert any("refuses to build" in getattr(c, "content", "") for c in content)
