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

import os
import re
from pathlib import Path

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

# The envelope beside every reply. Bump when a field changes meaning or
# goes away; adding a field keeps the version.
SCHEMA_VERSION = 1
STATUSES = ("ok", "blocked", "refused", "failed")
ENVELOPE = {
    "schema_version": "the integer above",
    "tool": "the tool that answered",
    "status": "ok: the command exited 0 | blocked: it refused or a condition triggered "
              "(exit 1) | refused: the path or name was outside what the agent may touch; "
              "nothing ran | failed: an exception, a bug to report",
    "mutated": "true only when a writing tool ran and exited 0",
    "workspace": "the directory every path was confined to",
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
refusals included. `start` and `frame` write to the record; the rest only
read it. Every path must be inside the server's workspace. Nothing here
builds, implements or deploys; those are run by a person on the command
line.
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


def plain_name(name: str) -> str:
    if not NAME.match(name or ""):
        raise Outside(f"an engagement name is a plain name (letters, digits, '.', '_', '-'), "
                      f"not {name!r}")
    return name


def _registry() -> str:
    from fde.registry import default_root

    return os.environ.get("FDE_REGISTRY") or str(default_root())


def run_command(args: list[str], registry: bool = True) -> tuple[str, str]:
    """One command, in-process, as the terminal would run it: the text it
    printed, and a status an agent can branch on without parsing prose --
    ok, blocked (the command refused or a condition triggered: exit 1),
    or failed (an exception, which is a bug to report)."""
    from typer.testing import CliRunner

    from fde.cli import app

    argv = [*args, "--registry", _registry()] if registry else list(args)
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
                            "mutated": mutated, "workspace": str(workspace())},
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

    def guarded(fn, mutates: bool = False):
        """A tool whose text comes from the command and whose envelope comes
        from the exit; an Outside refusal is answered in words, status
        `refused`, and nothing has changed."""
        def wrapped(*args, **kwargs):
            try:
                text, status = fn(*args, **kwargs)
            except Outside as exc:
                return reply(fn.__name__, f"refused: {exc}", "refused", False)
            return reply(fn.__name__, text, status, mutates and status == "ok")
        wrapped.__name__ = fn.__name__
        wrapped.__doc__ = fn.__doc__
        wrapped.__annotations__ = {**fn.__annotations__, "return": "CallToolResult"}
        wrapped.__wrapped__ = fn
        return wrapped

    def writing(fn):
        return guarded(fn, mutates=True)

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
    @writing
    def start(name: str, statement: str, base: str = "engagements"):
        """WRITES: opens an engagement at <base>/<name>/ inside the workspace,
        reads the statement into typed facts, and names the questions worth
        asking next. The name is a plain name; the base stays inside the
        workspace."""
        root = confine(base, "base")
        return run_command(["start", plain_name(name), "--base", str(root),
                            "--statement", statement], registry=False)

    @server.tool(annotations=writes)
    @writing
    def frame(engagement: str, text: str):
        """WRITES: reads a brief, pasted as text, into typed facts appended to
        the engagement's record, played back for correction with the
        follow-up questions. The engagement must be inside the workspace."""
        return run_command(["frame", str(confine(engagement, "engagement")), "--text", text])

    @server.tool(annotations=reads)
    @guarded
    def status(engagement: str):
        """The engagement's gates, what is known by scope and who said it, what
        is still missing, and which roles have not been heard."""
        return run_command(["status", str(confine(engagement, "engagement"))])

    @server.tool(annotations=reads)
    @guarded
    def next(engagement: str):
        """The single best next action judged from everything recorded, why,
        and -- when it is a question -- the evidence already on record and
        the decisions that turn on each candidate answer. Reads only; the
        action it names is for a person to run."""
        return run_command(["next", str(confine(engagement, "engagement"))])

    @server.tool(annotations=reads)
    @guarded
    def stage(engagement: str, project: str | None = None):
        """Where the engagement stands, computed off its record: discovery,
        validation, prototype, pilot, production, adoption, retrospective,
        or stopped -- with what would move it to the next stage. Reads only:
        a person runs `fde stage` to append the transition to the record."""
        args = ["stage", str(confine(engagement, "engagement")), "--no-record"]
        target = confine(project, "project")
        return run_command(args + (["--project", str(target)] if target else []))

    @server.tool(annotations=reads)
    @guarded
    def debt(engagement: str):
        """Decision debt: everything the engagement rests on that nobody has
        settled -- failing gates, standing waivers, guessed or merely stated
        facts, disagreements, unsigned attestations, unheard roles, open
        incidents, undecided components -- each with an owner and an age."""
        return run_command(["debt", str(confine(engagement, "engagement"))])

    @server.tool(annotations=reads)
    @guarded
    def stop_when(engagement: str, project: str | None = None,
                  journal: str | None = None):
        """Judge the engagement's stop conditions against what the record has
        measured: the scorecard, the field journal, the recorded outcomes.
        Reads only; recording a condition is for a person."""
        args = ["stop-when", str(confine(engagement, "engagement"))]
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
        return run_command(["history", str(confine(engagement, "engagement"))],
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
    return "\n".join(lines)


def serve() -> None:
    build_server().run("stdio")
