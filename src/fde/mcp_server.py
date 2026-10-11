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

Run it with `fde mcp`; add it to a coding agent as a stdio server, for
example `claude mcp add fde -- fde mcp`. The registry resolves the way
the command line resolves it, or from FDE_REGISTRY.
"""

from __future__ import annotations

import os

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
problems by what their statements already settle; `start` to open an
engagement on a statement; `frame` to read a brief into typed facts;
`status` for the gates and what is still unknown; `next` for the one thing
to learn or do next and what turns on it; `stage` for where the engagement
stands on its record; `debt` for what nobody has settled; `stop_when` for
whether the evidence says stop; `history` for the whole record in order.
Every tool returns the command's own output, refusals included. Nothing
here builds, implements or deploys; those are run by a person on the
command line.
"""


def _registry() -> str:
    from fde.registry import default_root

    return os.environ.get("FDE_REGISTRY") or str(default_root())


def run_command(args: list[str], registry: bool = True) -> str:
    """One command, in-process, as the terminal would run it."""
    from typer.testing import CliRunner

    from fde.cli import app

    argv = [*args, "--registry", _registry()] if registry else list(args)
    result = CliRunner().invoke(app, argv)
    text = (result.output or "").strip()
    if result.exception and not isinstance(result.exception, SystemExit):
        return f"{text}\n\nfde: {type(result.exception).__name__}: {result.exception}".strip()
    if result.exit_code not in (0, None):
        return f"{text}\n\n[fde exited {result.exit_code}]".strip()
    return text or "(no output)"


def build_server():
    """The MCP server with the framework's conversational tools."""
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as exc:  # pragma: no cover - the extra is optional
        raise ImportError(
            "the MCP server needs the extra: pip install 'fde-framework[mcp]'") from exc

    server = MCPServer("fde", instructions=INSTRUCTIONS)

    @server.tool()
    def triage(statements: list[str]) -> str:
        """Rank candidate problem statements by what each already settles about
        the architecture: how many facts it yields, how much of the decision
        space it closes, how many components it puts in scope. Decidability,
        not value."""
        args = ["triage"]
        for statement in statements:
            args += ["--statement", statement]
        return run_command(args)

    @server.tool()
    def start(name: str, statement: str, base: str = "engagements") -> str:
        """Open an engagement on a problem statement. Writes <base>/<name>/,
        reads the statement into typed facts, and names the questions worth
        asking next."""
        return run_command(["start", name, "--base", base, "--statement", statement],
                           registry=False)

    @server.tool()
    def frame(engagement: str, text: str) -> str:
        """Read a brief, pasted as text, into typed facts on the engagement's
        record, played back for correction, with the follow-up questions."""
        return run_command(["frame", engagement, "--text", text])

    @server.tool()
    def status(engagement: str) -> str:
        """The engagement's gates, what is known by scope and who said it, what
        is still missing, and which roles have not been heard."""
        return run_command(["status", engagement])

    @server.tool()
    def next(engagement: str) -> str:
        """The single best next action judged from everything recorded, why,
        and -- when it is a question -- the evidence already on record and
        the decisions that turn on each candidate answer."""
        return run_command(["next", engagement])

    @server.tool()
    def stage(engagement: str, project: str | None = None) -> str:
        """Where the engagement stands, computed off its record: discovery,
        validation, prototype, pilot, production, adoption, retrospective,
        or stopped -- with what would move it to the next stage."""
        args = ["stage", engagement] + (["--project", project] if project else [])
        return run_command(args)

    @server.tool()
    def debt(engagement: str) -> str:
        """Decision debt: everything the engagement rests on that nobody has
        settled -- failing gates, standing waivers, guessed or merely stated
        facts, disagreements, unsigned attestations, unheard roles, open
        incidents, undecided components -- each with an owner and an age."""
        return run_command(["debt", engagement])

    @server.tool()
    def stop_when(engagement: str, project: str | None = None,
                  journal: str | None = None) -> str:
        """Judge the engagement's stop conditions against what the record has
        measured: the scorecard, the field journal, the recorded outcomes."""
        args = ["stop-when", engagement]
        if project:
            args += ["--project", project]
        if journal:
            args += ["--journal", journal]
        return run_command(args, registry=False)

    @server.tool()
    def history(engagement: str) -> str:
        """Every dated entry on the engagement's record, in order, the undated
        ones above it, one line each."""
        return run_command(["history", engagement], registry=False)

    @server.resource("fde://thirty-seconds", name="fde in thirty seconds",
                     mime_type="text/plain")
    def thirty_seconds() -> str:
        return THIRTY_SECONDS

    return server


def serve() -> None:
    build_server().run("stdio")
