"""The server as a client sees it: a separate process over stdio, driven by
the official MCP client, the way a coding agent drives it. The in-process
tests check each tool; these check the transport under what agents
actually do -- several calls at once, a call abandoned midway, a record
that changed on disk between calls."""

from __future__ import annotations

import asyncio
import os
import sys

import pytest

pytest.importorskip("mcp", reason="the MCP extra is not installed")

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

from fde.mcp_server import TOOLS  # noqa: E402

STATEMENT = "Route each support message to one of 77 queues."
PATIENCE = 90  # seconds; a regression hangs the server, and the test must fail, not hang


def serve_in(workspace):
    return StdioServerParameters(command=sys.executable, args=["-m", "fde.cli", "mcp"],
                                 env={**os.environ, "FDE_WORKSPACE": str(workspace)})


def drive(workspace, scenario):
    async def main():
        async with stdio_client(serve_in(workspace)) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), PATIENCE)
                return await asyncio.wait_for(scenario(session), PATIENCE)
    return asyncio.run(main())


def test_a_real_client_lists_the_tools_with_their_input_schemas_and_walks_by_name(tmp_path):
    async def scenario(session):
        listed = await session.list_tools()
        schemas = {t.name: t.input_schema for t in listed.tools}
        opened = await session.call_tool("start", {"name": "acme", "statement": STATEMENT})
        status = await session.call_tool("status", {"engagement": "acme"})
        return schemas, opened, status

    schemas, opened, status = drive(tmp_path, scenario)
    assert set(schemas) == set(TOOLS)
    for name, schema in schemas.items():
        assert schema["type"] == "object" and schema["properties"], name
        if name not in ("triage", "start"):
            assert "engagement" in schema["required"], name
    assert opened.structured_content["status"] == "ok" and opened.structured_content["mutated"]
    assert status.structured_content["status"] == "ok"
    assert "blocked by" in status.content[0].text


def test_calls_issued_at_once_all_come_back(tmp_path):
    """Claude Code issued `status` and `next` in the same breath and the
    second came back "Connection closed": the server ran them on two
    threads, and the output capture that each swaps in leaked one
    command's text onto the JSON-RPC channel. Commands are now one at a
    time inside the server."""
    async def scenario(session):
        await session.call_tool("start", {"name": "acme", "statement": STATEMENT})
        rounds = []
        for _ in range(3):
            replies = await asyncio.gather(
                *(session.call_tool(tool, {"engagement": "acme"})
                  for tool in ("status", "next", "debt", "stage", "history", "stop_when")),
                return_exceptions=True)
            rounds.append(replies)
        after = await session.call_tool("history", {"engagement": "acme"})
        return rounds, after

    rounds, after = drive(tmp_path, scenario)
    for replies in rounds:
        for reply in replies:
            assert not isinstance(reply, BaseException), repr(reply)
            assert reply.structured_content["status"] == "ok", reply.content[0].text
            assert reply.content[0].text.strip(), reply.structured_content
    assert after.structured_content["status"] == "ok"


def test_a_call_abandoned_midway_leaves_the_server_answering(tmp_path):
    async def scenario(session):
        await session.call_tool("start", {"name": "acme", "statement": STATEMENT})
        abandoned = asyncio.ensure_future(session.call_tool("next", {"engagement": "acme"}))
        await asyncio.sleep(0)
        abandoned.cancel()
        try:
            await abandoned
        except asyncio.CancelledError:
            pass
        return await session.call_tool("status", {"engagement": "acme"})

    status = drive(tmp_path, scenario)
    assert status.structured_content["status"] == "ok"


def test_the_record_is_read_fresh_so_a_change_on_disk_shows_in_the_next_call(tmp_path):
    from typer.testing import CliRunner

    from fde.cli import app

    async def scenario(session):
        await session.call_tool("start", {"name": "acme", "statement": STATEMENT})
        before = await session.call_tool("history", {"engagement": "acme"})
        # Someone at the terminal frames a brief while the server is up.
        result = CliRunner().invoke(app, ["frame", str(tmp_path / "engagements" / "acme"),
                                          "--text", "Two agents triage 9,000 emails a month "
                                                    "by hand and misroute about 12 percent."])
        assert result.exit_code == 0, result.output
        after = await session.call_tool("history", {"engagement": "acme"})
        return before.content[0].text, after.content[0].text

    before, after = drive(tmp_path, scenario)
    assert "0002-frame" not in before and "0002-frame" in after
