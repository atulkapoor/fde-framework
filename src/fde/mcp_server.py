"""The framework inside the coding agent.

Every tool here is the command with the same name, run in-process, and it
returns exactly what the terminal would print -- so what the agent reads
is what a person would read, refusals included. The tools are the ones
that make sense mid-conversation with an agent: which of several
problems is decidable, what an engagement still needs, the one thing to
learn next and what turns on it, where the engagement stands, what
nobody has settled, and whether the evidence says stop. Building,
implementing and deploying stay on the command line, where the person
who runs them is accountable for them.

An agent is not a person: a prompt, a repository instruction or a
document it read can steer what it passes here. So every path an agent
supplies -- an engagement, a base, a project, a journal -- is resolved
with its symlinks and must land inside one workspace, the directory the
server was started in or FDE_WORKSPACE; anything else is refused in the
tool's own words, not raised. Engagement names are plain names. The two
tools that write to the record say so in their descriptions and carry
the protocol's read-only and destructive hints, so a client can ask
before they run. The registry comes from the operator's environment,
never from the agent.

Run it with `fde mcp`; add it to a coding agent as a stdio server, for
example `claude mcp add fde -- fde mcp`. `fde mcp --check` builds the
server and lists what it serves without serving it.
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
from pathlib import Path

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

# The envelope beside every reply, as the JSON Schema a client can validate
# against (`fde mcp --schema` prints it). Bump the version when a field
# changes meaning or goes away; adding a field keeps the version.
# 2: `mutated` measured off the disk. 3: `text` required, and the schema admits
# fields it does not name, so that adding one keeps the version from here on;
# 0.1.49 added `text` under a closed version 2, which a strict client would
# have rejected, and an outside reading said so.
SCHEMA_VERSION = 3
STATUSES = ("ok", "blocked", "refused", "failed")
TOOLS = ("triage", "start", "frame", "status", "next", "stage", "debt", "stop_when", "history")
ENVELOPE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": f"https://github.com/atulkapoor/fde-framework/schemas/mcp-envelope/v{SCHEMA_VERSION}",
    "title": f"fde MCP reply envelope, version {SCHEMA_VERSION}",
    "description": "The structured content beside the text of every tool reply. The text "
                   "is what the command printed; the envelope is what an agent branches on "
                   "without parsing prose. It follows the command's exit, not its wording. "
                   "Versioning: a field changing meaning or going away bumps "
                   "schema_version; a field added does not, and this schema admits fields "
                   "it does not name so a client on this version keeps validating when one "
                   "is added.",
    "type": "object",
    "properties": {
        "schema_version": {"const": SCHEMA_VERSION,
                           "description": "Bumped when a field changes meaning or goes away."},
        "tool": {"enum": list(TOOLS), "description": "The tool that answered."},
        "status": {"enum": list(STATUSES),
                   "description": "ok: the command exited 0. blocked: it refused or a "
                                  "condition triggered (exit 1); the text says which. "
                                  "refused: a path or name was outside what the agent may "
                                  "touch; nothing ran. failed: an exception; a bug to report."},
        "mutated": {"type": "boolean",
                    "description": "True when the engagement's files changed during the "
                                   "call, measured by hashing them before and after: a "
                                   "writing tool that failed partway and left changes "
                                   "behind says true. Reading tools say false. (Version 1 "
                                   "said true only on a writing tool's exit 0, which "
                                   "assumed a failure had written nothing.)"},
        "workspace": {"type": "string",
                      "description": "The directory every path was confined to."},
        "text": {"type": "string",
                 "description": "What the command printed, verbatim: the same text as the "
                                "reply's content block. Here as well because a client that "
                                "shows the model the structured content shows only that, "
                                "and an agent that could see the status but not the words "
                                "went looking for them on disk."},
    },
    "required": ["schema_version", "tool", "status", "mutated", "workspace", "text"],
    "additionalProperties": True,
}

THIRTY_SECONDS = """\
You give it the problem as the client put it, the client's own examples,
the constraints, a baseline someone measured, and where it has to run. It
gives back an architecture decision with its receipts, an exam the build
has to pass, an implementation driven inside a fence, a deployment package,
a scorecard of what the build can prove, and a record of what was never
settled. It refuses to build until the evidence is there, and it can say
stop. Repository: https://github.com/atulkapoor/fde-framework
Bring an engagement: https://atulkapoor.github.io/fde-framework/engage.html
"""

INSTRUCTIONS = """\
fde is the decision before the AI build. Use `triage` to rank candidate
problems by what their statements already settle (decidability, not
value); `start` to open an engagement on a statement; `frame` to read a
brief into typed facts; `status` for the gates and what is still unknown;
`next` for the one thing to learn or do next and what turns on it; `stage`
for where the engagement stands on its record; `debt` for what nobody has
settled; `stop_when` for whether the evidence says stop; `history` for the
whole record in order. Every tool returns the command's own output,
refusals included, with a status beside it (ok, blocked, refused, failed)
to branch on instead of the prose. `start` and `frame` write to the
record; the rest only read it. An engagement is named as `start` named
it, or by its path; every path must be inside the server's workspace.
Nothing here builds, implements or deploys; those are run by a person on
the command line.
"""


def workspace() -> Path:
    """Where the agent may read and write: FDE_WORKSPACE, else the directory
    the server was started in. Resolved once, symlinks followed."""
    return Path(os.environ.get("FDE_WORKSPACE") or os.getcwd()).resolve()


class Outside(ValueError):
    """A path the agent supplied that does not stay inside the workspace."""


def confine(path: str | None, what: str, root: Path | None = None) -> Path | None:
    """The path as the command will see it, or Outside. Relative paths are
    taken from the workspace; symlinks are resolved before the check, so a
    link inside pointing outside is outside."""
    if path is None or path == "":
        return None
    root = root or workspace()
    candidate = Path(path)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        raise Outside(f"{what} {path!r} is outside the workspace {root}; the agent may only "
                      "read and write inside it (set FDE_WORKSPACE to move it)")
    return resolved


def locate(engagement: str) -> Path:
    """The engagement as the command will see it. `start(name="acme")` puts
    the record at engagements/acme; `status(engagement="acme")` a moment
    later must find it, as `fde status acme` does on the command line. So a
    bare name is looked for at <workspace>/<name> and then where `start`
    puts it; both candidates are confined, so a name that climbs out is
    refused before anything is looked for. A path is taken as given."""
    path = confine(engagement, "engagement")
    if path is not None and not (path / "facts").is_dir() and not Path(engagement).is_absolute():
        under = confine(str(Path("engagements") / engagement), "engagement")
        if under is not None and (under / "facts").is_dir():
            return under
    return path


def fingerprint(root: Path | None) -> dict[str, str]:
    """The record, file by file, hashed -- so `mutated` is what happened on
    the disk and not what the exit code implied. An engagement's record
    is small; the hashing is milliseconds."""
    if root is None or not root.is_dir():
        return {}
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}


def plain_name(name: str) -> str:
    if not NAME.match(name or ""):
        raise Outside(f"an engagement name is a plain name (letters, digits, '.', '_', '-'), "
                      f"not {name!r}")
    return name


def _registry() -> str:
    from fde.registry import default_root

    return os.environ.get("FDE_REGISTRY") or str(default_root())


# One command at a time. The server runs each tool on a worker thread, and
# a coding agent will issue `status` and `next` in the same breath; the
# runner that captures a command's output does so by swapping the
# process's stdout, and two swaps interleaved left one command printing
# straight onto the JSON-RPC channel. The protocol broke, the client saw
# "Connection closed", and the record was not at fault. Commands take
# milliseconds; the record has one writer at a time, as it should.
_ONE_AT_A_TIME = threading.Lock()


def run_command(args: list[str], registry: bool = True) -> tuple[str, str]:
    """One command, in-process, as the terminal would run it: the text it
    printed, and a status an agent can branch on without parsing prose --
    ok, blocked (the command refused or a condition triggered: exit 1),
    or failed (an exception, which is a bug to report)."""
    from typer.testing import CliRunner

    from fde.cli import app

    argv = [*args, "--registry", _registry()] if registry else list(args)
    with _ONE_AT_A_TIME:
        result = CliRunner().invoke(app, argv)
    text = (result.output or "").strip()
    if result.exception and not isinstance(result.exception, SystemExit):
        return (f"{text}\n\nfde: {type(result.exception).__name__}: {result.exception}".strip(),
                "failed")
    if result.exit_code not in (0, None):
        return f"{text}\n\n[fde exited {result.exit_code}]".strip(), "blocked"
    return text or "(no output)", "ok"


def reply(tool: str, text: str, status: str, mutated: bool):
    """What a tool returns: the text a person would read as the content, and
    the fields an agent reasons over beside it -- status, whether the
    record changed, which tool. The envelope follows the command's exit,
    not a parse of its prose."""
    from mcp import types

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)],
        structured_content={"schema_version": SCHEMA_VERSION, "tool": tool, "status": status,
                            "mutated": mutated, "workspace": str(workspace()), "text": text},
        is_error=status == "failed",
    )


def build_server():
    """The MCP server with the framework's conversational tools."""
    try:
        from mcp.server.mcpserver import MCPServer
        from mcp.types import ToolAnnotations
    except ImportError as exc:  # pragma: no cover - the extra is optional
        raise ImportError(
            "the MCP server needs the extra: pip install 'fde-framework[mcp]'") from exc

    reads = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True,
                            open_world_hint=False)
    writes = ToolAnnotations(read_only_hint=False, destructive_hint=False,
                             idempotent_hint=False, open_world_hint=False)
    server = MCPServer("fde", instructions=INSTRUCTIONS)

    def guarded(fn, watches=None):
        """A tool whose text comes from the command and whose envelope comes
        from the exit; an Outside refusal is answered in words, status
        `refused`, and nothing has changed. A writing tool names what it
        writes to (`watches`), and `mutated` is whether those files
        changed -- measured, so a command that wrote half a record and
        then failed does not report a clean miss."""
        def wrapped(*args, **kwargs):
            try:
                target = watches(*args, **kwargs) if watches else None
                before = fingerprint(target) if watches else None
                text, status = fn(*args, **kwargs)
            except Outside as exc:
                return reply(fn.__name__, f"refused: {exc}", "refused", False)
            changed = bool(watches) and fingerprint(target) != before
            return reply(fn.__name__, text, status, changed)
        wrapped.__name__ = fn.__name__
        wrapped.__doc__ = fn.__doc__
        wrapped.__annotations__ = {**fn.__annotations__, "return": "CallToolResult"}
        wrapped.__wrapped__ = fn
        return wrapped

    def writing(watches):
        return lambda fn: guarded(fn, watches=watches)

    @server.tool(annotations=reads)
    @guarded
    def triage(statements: list[str]):
        """Rank candidate problem statements by what each already settles about
        the architecture: how many facts it yields, how much of the decision
        space it closes, how many components it puts in scope. Decidability,
        not value: the business case comes from the baseline. Reads nothing."""
        args = ["triage"]
        for statement in statements:
            args += ["--statement", statement]
        return run_command(args)

    @server.tool(annotations=writes)
    @writing(lambda name, statement, base="engagements": confine(base, "base") / plain_name(name))
    def start(name: str, statement: str, base: str = "engagements"):
        """WRITES: opens an engagement at <base>/<name>/ inside the workspace,
        reads the statement into typed facts, and names the questions worth
        asking next. The name is a plain name; the base stays inside the
        workspace."""
        root = confine(base, "base")
        return run_command(["start", plain_name(name), "--base", str(root),
                            "--statement", statement], registry=False)

    @server.tool(annotations=writes)
    @writing(lambda engagement, text: locate(engagement))
    def frame(engagement: str, text: str):
        """WRITES: reads a brief, pasted as text, into typed facts appended to
        the engagement's record, played back for correction with the
        follow-up questions. The engagement must be inside the workspace."""
        return run_command(["frame", str(locate(engagement)), "--text", text])

    @server.tool(annotations=reads)
    @guarded
    def status(engagement: str):
        """The engagement's gates, what is known by scope and who said it, what
        is still missing, and which roles have not been heard."""
        return run_command(["status", str(locate(engagement))])

    @server.tool(annotations=reads)
    @guarded
    def next(engagement: str):
        """The single best next action judged from everything recorded, why,
        and -- when it is a question -- the evidence already on record and
        the decisions that turn on each candidate answer. Reads only; the
        action it names is for a person to run."""
        return run_command(["next", str(locate(engagement))])

    @server.tool(annotations=reads)
    @guarded
    def stage(engagement: str, project: str | None = None):
        """Where the engagement stands, computed off its record: discovery,
        validation, prototype, pilot, production, adoption, retrospective,
        or stopped -- with what would move it to the next stage. Reads only:
        a person runs `fde stage` to append the transition to the record."""
        args = ["stage", str(locate(engagement)), "--no-record"]
        target = confine(project, "project")
        return run_command(args + (["--project", str(target)] if target else []))

    @server.tool(annotations=reads)
    @guarded
    def debt(engagement: str):
        """Decision debt: everything the engagement rests on that nobody has
        settled -- failing gates, standing waivers, guessed or merely stated
        facts, disagreements, unsigned attestations, unheard roles, open
        incidents, undecided components -- each with an owner and an age."""
        return run_command(["debt", str(locate(engagement))])

    @server.tool(annotations=reads)
    @guarded
    def stop_when(engagement: str, project: str | None = None,
                  journal: str | None = None):
        """Judge the engagement's stop conditions against what the record has
        measured: the scorecard, the field journal, the recorded outcomes.
        Reads only; recording a condition is for a person."""
        args = ["stop-when", str(locate(engagement))]
        target = confine(project, "project")
        if target:
            args += ["--project", str(target)]
        log = confine(journal, "journal")
        if log:
            args += ["--journal", str(log)]
        return run_command(args, registry=False)

    @server.tool(annotations=reads)
    @guarded
    def history(engagement: str):
        """Every dated entry on the engagement's record, in order, the undated
        ones above it, one line each."""
        return run_command(["history", str(locate(engagement))],
                           registry=False)

    @server.resource("fde://thirty-seconds", name="fde in thirty seconds",
                     mime_type="text/plain")
    def thirty_seconds() -> str:
        return THIRTY_SECONDS

    return server


def describe() -> str:
    """What the server would serve, for `fde mcp --check`."""
    import asyncio

    server = build_server()
    tools = asyncio.run(server.list_tools())
    lines = [f"fde mcp: workspace {workspace()}", f"  registry {_registry()}", "  tools:"]
    for tool in tools:
        hint = "writes" if tool.annotations and tool.annotations.read_only_hint is False \
            else "reads"
        lines.append(f"    {tool.name:10} {hint}")
    lines.append("  resources: fde://thirty-seconds")
    lines.append(f"  envelope: schema_version {SCHEMA_VERSION} (`fde mcp --schema`)")
    return "\n".join(lines)


def serve() -> None:
    build_server().run("stdio")
