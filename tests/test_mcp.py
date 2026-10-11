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


def test_the_envelope_is_versioned_and_every_status_is_reachable(tmp_path, monkeypatch):
    import jsonschema

    from fde import mcp_server
    from fde.mcp_server import ENVELOPE_SCHEMA, SCHEMA_VERSION, STATUSES, reply, run_command

    monkeypatch.setenv("FDE_WORKSPACE", str(tmp_path))
    server = build_server()
    seen = {}
    ok = asyncio.run(server.call_tool("triage", {"statements": ["Route.", "Read PDFs."]}))
    seen["ok"] = ok.structured_content
    refused = asyncio.run(server.call_tool("status", {"engagement": "/etc"}))
    seen["refused"] = refused.structured_content
    blocked = asyncio.run(server.call_tool("status", {"engagement": "nowhere"}))
    seen["blocked"] = blocked.structured_content
    failed = reply("status", "boom", "failed", False)
    seen["failed"] = failed.structured_content
    assert failed.is_error and not ok.is_error
    for status in STATUSES:
        assert seen[status]["status"] == status
        assert seen[status]["schema_version"] == SCHEMA_VERSION
        jsonschema.validate(seen[status], ENVELOPE_SCHEMA)

    class Broken:
        output = "half-written"
        exit_code = 1
        exception = RuntimeError("the record is corrupt")

    monkeypatch.setattr("typer.testing.CliRunner.invoke", lambda self, app, argv: Broken())
    text, status = run_command(["status", "x"])
    assert status == "failed" and "RuntimeError" in text
    assert mcp_server.workspace() == tmp_path.resolve()


def test_doctor_measures_the_install_and_fails_only_on_what_the_core_needs(tmp_path):
    from typer.testing import CliRunner

    from fde.cli import DEFAULT_ROOT, app

    runner = CliRunner()
    healthy = runner.invoke(app, ["doctor", "--registry", str(DEFAULT_ROOT)])
    assert healthy.exit_code == 0, healthy.output
    assert "ok python" in healthy.output and "ok registry" in healthy.output
    assert "extra [mcp]" in healthy.output and "docker" in healthy.output
    assert "the core can run" in healthy.output
    sick = runner.invoke(app, ["doctor", "--registry", str(tmp_path / "nowhere")])
    assert sick.exit_code == 1 and "NO registry" in sick.output
    assert "something the core needs is missing" in sick.output


# --- the interface as a product: the second call finds the first call's work


def test_an_engagement_is_found_by_the_name_start_gave_it(tmp_path, monkeypatch):
    """`start(name="acme")` then `status(engagement="acme")` is the sequence
    an agent writes first. Before this test the second call looked at
    <workspace>/acme, found nothing, and said so; the record was at
    engagements/acme, where `start` had put it and where `fde status acme`
    finds it on the command line."""
    monkeypatch.setenv("FDE_WORKSPACE", str(tmp_path))
    server = build_server()
    opened = asyncio.run(server.call_tool("start", {
        "name": "acme", "statement": "Route each support message to one of 77 queues."}))
    assert opened.structured_content["status"] == "ok"
    assert (tmp_path / "engagements" / "acme" / "facts").is_dir()
    for tool, expected in (("status", "blocked by"), ("next", "next: fde "),
                           ("stage", "acme: discovery"), ("debt", "decision debt as of"),
                           ("history", "acme: history"),
                           ("stop_when", "no stop conditions on record")):
        result = asyncio.run(server.call_tool(tool, {"engagement": "acme"}))
        assert expected in result.content[0].text, (tool, result.content[0].text)
        assert result.structured_content["status"] == "ok", (tool, result.structured_content)
    framed = asyncio.run(server.call_tool("frame", {
        "engagement": "acme",
        "text": "Two agents triage 9,000 emails a month by hand and misroute about 12 percent."}))
    assert framed.structured_content["status"] == "ok" and framed.structured_content["mutated"]
    # The path form still works, and a name that climbs is still refused
    # before anything is looked for.
    by_path = asyncio.run(server.call_tool("status", {"engagement": "engagements/acme"}))
    assert by_path.structured_content["status"] == "ok"
    climbing = asyncio.run(server.call_tool("status", {"engagement": "../acme"}))
    assert climbing.structured_content["status"] == "refused"
    assert "outside the workspace" in climbing.content[0].text


def test_a_corrupt_record_is_a_sentence_naming_the_file_not_a_traceback(tmp_path, monkeypatch):
    monkeypatch.setenv("FDE_WORKSPACE", str(tmp_path))
    server = build_server()
    asyncio.run(server.call_tool("start", {
        "name": "acme", "statement": "Route each support message to one of 77 queues."}))
    asyncio.run(server.call_tool("frame", {
        "engagement": "acme", "text": "Two agents triage 9,000 emails a month by hand."}))
    record = next((tmp_path / "engagements" / "acme" / "facts").glob("*.yaml"))
    with record.open("a") as fh:
        fh.write('{"this is": not yaml\n')
    for tool in ("status", "next", "debt"):
        result = asyncio.run(server.call_tool(tool, {"engagement": "acme"}))
        text = result.content[0].text
        assert result.structured_content["status"] != "ok", tool
        assert record.stem in text and "cannot read" in text, (tool, text)
        assert "Traceback" not in text, (tool, text)


def test_the_schema_is_published_and_is_what_every_reply_follows(tmp_path, monkeypatch):
    import json

    import jsonschema
    from typer.testing import CliRunner

    from fde.cli import app
    from fde.mcp_server import ENVELOPE_SCHEMA, SCHEMA_VERSION, TOOLS

    result = CliRunner().invoke(app, ["mcp", "--schema"])
    assert result.exit_code == 0, result.output
    published = json.loads(result.output)
    assert published == ENVELOPE_SCHEMA
    jsonschema.Draft202012Validator.check_schema(published)
    assert published["$id"].endswith(f"/v{SCHEMA_VERSION}")
    # The schema's list of tools is the server's list of tools.
    monkeypatch.setenv("FDE_WORKSPACE", str(tmp_path))
    server = build_server()
    assert {t.name for t in asyncio.run(server.list_tools())} == set(TOOLS)
    # And an envelope with a field it does not name, or a status it does not
    # name, fails validation: a client can trust the schema to be the contract.
    good = asyncio.run(server.call_tool("triage", {"statements": ["Route."]})).structured_content
    jsonschema.validate(good, published)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**good, "extra": 1}, published)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**good, "status": "done"}, published)


def test_mutated_is_measured_so_a_failed_write_that_left_changes_says_so(tmp_path, monkeypatch):
    """Version 1 of the envelope said mutated only on a writing tool's
    exit 0, which assumed a failure had written nothing. A command can
    write half a record and then raise. Version 2 hashes the record
    before and after."""
    from fde import mcp_server
    from fde.mcp_server import SCHEMA_VERSION

    assert SCHEMA_VERSION == 2
    monkeypatch.setenv("FDE_WORKSPACE", str(tmp_path))
    server = build_server()
    opened = asyncio.run(server.call_tool("start", {
        "name": "acme", "statement": "Route each support message to one of 77 queues."}))
    assert opened.structured_content["mutated"] is True
    root = tmp_path / "engagements" / "acme"

    def half_written(args, registry=True):
        (root / "facts" / "0009-frame.yaml").write_text("session_id: '0009'\n")
        return "half-written", "failed"

    monkeypatch.setattr(mcp_server, "run_command", half_written)
    framed = asyncio.run(server.call_tool("frame", {"engagement": "acme", "text": "x"}))
    assert framed.structured_content["status"] == "failed"
    assert framed.structured_content["mutated"] is True
    # And a refusal that ran nothing, or a write that changed nothing, says false.
    monkeypatch.setattr(mcp_server, "run_command", lambda args, registry=True: ("no", "blocked"))
    again = asyncio.run(server.call_tool("start", {"name": "acme", "statement": "x"}))
    assert again.structured_content["mutated"] is False
    reading = asyncio.run(server.call_tool("status", {"engagement": "acme"}))
    assert reading.structured_content["mutated"] is False
