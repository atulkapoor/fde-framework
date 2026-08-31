"""The implement loop: harness as stop condition, doctrine as fence."""

from pathlib import Path

from typer.testing import CliRunner

from fde.cli import app
from fde.implement import run_loop

runner = CliRunner()


def toy_project(tmp_path: Path) -> Path:
    """A minimal emitted-project shape whose harness fails until app/impl.py
    exists -- the same contract the real harness has with the pipeline."""
    project = tmp_path / "project"
    (project / "evals").mkdir(parents=True)
    (project / "app").mkdir()
    (project / "app" / "boundary.py").write_text("BOUNDARY = True\n")
    (project / "ARCHITECTURE.md").write_text("# Architecture\n")
    (project / "evals" / "harness.py").write_text(
        "import sys\n"
        "from pathlib import Path\n\n"
        "ok = (Path(__file__).parents[1] / 'app' / 'impl.py').exists()\n"
        "print('green' if ok else 'red: app/impl.py missing')\n"
        "sys.exit(0 if ok else 1)\n"
    )
    return project


def implementing_agent(project):
    def invoke(prompt):
        assert "ARCHITECTURE.md" in prompt  # the brief points at the decisions
        (project / "app" / "impl.py").write_text("DONE = True\n")
        return True
    return invoke


def test_the_loop_stops_when_the_harness_goes_green(tmp_path):
    project = toy_project(tmp_path)
    report = run_loop(project, invoke_agent=implementing_agent(project),
                      max_rounds=3)
    assert report.done
    assert report.stopped_by == "harness green"
    assert len(report.rounds) == 2  # one red round, one green


def test_an_idle_agent_hits_the_round_cap_or_stops_early(tmp_path):
    project = toy_project(tmp_path)
    report = run_loop(project, invoke_agent=lambda prompt: True, max_rounds=2)
    assert not report.done
    assert report.stopped_by == "round cap"


def test_a_failing_agent_that_changes_nothing_stops_the_loop(tmp_path):
    project = toy_project(tmp_path)
    report = run_loop(project, invoke_agent=lambda prompt: False, max_rounds=5)
    assert not report.done
    assert report.stopped_by == "agent failed"
    assert len(report.rounds) == 1  # no point burning four more rounds


def test_editing_the_exam_is_detected_restored_and_fatal(tmp_path):
    """An agent that rewrites the harness to always pass has not implemented
    anything; it has graded its own homework."""
    project = toy_project(tmp_path)
    original = (project / "evals" / "harness.py").read_text()

    def cheat(prompt):
        (project / "evals" / "harness.py").write_text("import sys; sys.exit(0)\n")
        return True

    report = run_loop(project, invoke_agent=cheat, max_rounds=5)
    assert not report.done
    assert report.stopped_by == "guardrail"
    assert "edited the exam" in report.rounds[-1].violation
    assert (project / "evals" / "harness.py").read_text() == original


def test_the_boundary_is_part_of_the_fence(tmp_path):
    project = toy_project(tmp_path)

    def cheat(prompt):
        (project / "app" / "boundary.py").write_text("BOUNDARY = False\n")
        return True

    report = run_loop(project, invoke_agent=cheat, max_rounds=5)
    assert report.stopped_by == "guardrail"
    assert (project / "app" / "boundary.py").read_text() == "BOUNDARY = True\n"


def test_the_cli_writes_the_log_and_reports_rounds(tmp_path):
    project = toy_project(tmp_path)
    fake_agent = tmp_path / "agent.py"
    fake_agent.write_text(
        "import pathlib, sys\n"
        "sys.stdin.read()\n"
        "pathlib.Path('app/impl.py').write_text('DONE = True\\n')\n"
    )
    import sys as _sys

    result = runner.invoke(app, [
        "implement", str(project),
        "--agent-cmd", f"{_sys.executable} {fake_agent}",
        "--max-rounds", "3",
    ])
    assert result.exit_code == 0, result.output
    assert "stopped by: harness green" in result.output
    log = (project / "ops" / "implement-log.md").read_text()
    assert "## Round 1" in log and "check: red" in log


def test_a_directory_that_is_not_a_project_is_refused(tmp_path):
    result = runner.invoke(app, ["implement", str(tmp_path)])
    assert result.exit_code == 1
    assert "not an emitted project" in result.output


def test_an_agent_that_takes_a_brief_file_gets_one(tmp_path):
    """aider-shaped agents read --message-file, not stdin; {prompt_file}
    substitutes the written brief's path."""
    import sys as _sys

    project = toy_project(tmp_path)
    fake_agent = tmp_path / "agent.py"
    fake_agent.write_text(
        "import pathlib, sys\n"
        "brief = pathlib.Path(sys.argv[1]).read_text()\n"
        "assert 'ARCHITECTURE.md' in brief\n"
        "pathlib.Path('app/impl.py').write_text('DONE = True\\n')\n"
    )
    result = runner.invoke(app, [
        "implement", str(project),
        "--agent-cmd", f"{_sys.executable} {fake_agent} {{prompt_file}}",
        "--max-rounds", "3",
    ])
    assert result.exit_code == 0, result.output
    assert "harness green" in result.output


def test_the_brief_path_survives_a_relative_project_path(tmp_path, monkeypatch):
    """The agent runs with cwd=project; a relative project path substituted
    into {prompt_file} once double-counted itself and the agent died
    reading its own brief."""
    import sys as _sys

    toy_project(tmp_path)
    fake_agent = tmp_path / "agent.py"
    fake_agent.write_text(
        "import pathlib, sys\n"
        "brief = pathlib.Path(sys.argv[1]).read_text()\n"
        "pathlib.Path('app/impl.py').write_text('DONE = True\\n')\n"
    )
    monkeypatch.chdir(tmp_path)
    report = run_loop(Path("project"),
                      agent_cmd=f"{_sys.executable} {fake_agent} {{prompt_file}}",
                      max_rounds=3)
    assert report.done, report.rounds[-1]
