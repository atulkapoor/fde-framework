"""The sandbox: only the project mounted, the environment reduced to the
policy's allowlist, no network unless allowed -- by construction."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from fde import implement as implement_module
from fde.sandbox import (
    DEFAULT_IMAGE,
    WORKDIR,
    Policy,
    describe,
    docker_command,
    environment,
    load_policy,
    run_agent_in_sandbox,
)


def docker_up() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=20).returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def test_the_policy_is_data_in_the_project_with_safe_defaults(tmp_path):
    assert load_policy(tmp_path) == Policy()
    (tmp_path / "ops").mkdir()
    (tmp_path / "ops" / "agent-policy.yaml").write_text(
        "image: ghcr.io/example/agent:1\nnetwork: host\nenv_allow: [PATH, ANTHROPIC_API_KEY]\n")
    policy = load_policy(tmp_path)
    assert policy.image == "ghcr.io/example/agent:1" and policy.network == "host"
    assert policy.env_allow == ["PATH", "ANTHROPIC_API_KEY"]
    (tmp_path / "ops" / "agent-policy.yaml").write_text("network: [everything\n")
    assert load_policy(tmp_path) == Policy()  # unreadable never widens


def test_the_environment_is_the_allowlist_and_nothing_else(monkeypatch):
    monkeypatch.setenv("SECRET_TOKEN", "s")
    monkeypatch.setenv("LANG", "en_GB.UTF-8")
    env = environment(Policy(), extra=("NOT_SET",))
    assert "SECRET_TOKEN" not in env and env["LANG"] == "en_GB.UTF-8"
    assert "NOT_SET" not in env
    env = environment(Policy(), extra=("SECRET_TOKEN",))
    assert env["SECRET_TOKEN"] == "s"


def test_the_container_gets_only_the_project_and_no_network(tmp_path):
    command = docker_command(tmp_path, "aider --yes", Policy(),
                             {"PATH": "/x", "HOME": "/h", "LANG": "C", "KEY": "k"})
    assert command[:4] == ["docker", "run", "--rm", "-i"]
    assert f"{tmp_path.resolve()}:{WORKDIR}" in command and command[command.index("-w") + 1] == WORKDIR
    assert "--network" in command and command[command.index("--network") + 1] == "none"
    forwarded = [command[i + 1] for i, part in enumerate(command) if part == "-e"]
    assert forwarded == ["LANG", "KEY"]  # the container keeps its own PATH and HOME
    assert "k" not in command  # values never on the command line
    assert command[-4:] == [DEFAULT_IMAGE, "sh", "-lc", "aider --yes"]
    opened = docker_command(tmp_path, "x", Policy(), {}, allow_network=True)
    assert "--network" not in opened
    host = docker_command(tmp_path, "x", Policy(network="host"), {})
    assert "--network" not in host


def test_the_loop_runs_the_agent_through_docker_when_asked(tmp_path, monkeypatch):
    project = tmp_path / "p"
    (project / ".implement").mkdir(parents=True)
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["input"] = kwargs.get("input")
        seen["env"] = kwargs.get("env")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("fde.sandbox.subprocess.run", fake_run)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "never")
    ok = implement_module._run_agent(project, "agent --message-file {prompt_file}", "the brief",
                                     10, sandbox="docker", env_allow=("ANTHROPIC_API_KEY",))
    assert ok
    assert seen["command"][0] == "docker"
    assert f"{WORKDIR}/.implement/brief.md" in seen["command"][-1]
    assert (project / ".implement" / "brief.md").read_text() == "the brief"
    assert "ANTHROPIC_API_KEY" in seen["env"] and "AWS_SECRET_ACCESS_KEY" not in seen["env"]


def test_a_missing_docker_is_named_not_a_traceback(tmp_path, monkeypatch):
    def gone(*a, **k):
        raise FileNotFoundError("docker")

    monkeypatch.setattr("fde.sandbox.subprocess.run", gone)
    with pytest.raises(implement_module.AgentMissing, match="docker is not on this machine"):
        implement_module._run_agent(tmp_path, "agent", "brief", 10, sandbox="docker")


def test_the_log_says_where_the_agent_ran(tmp_path, monkeypatch):
    monkeypatch.setenv("LANG", "C")
    unsandboxed = describe(tmp_path, None)
    assert "unsandboxed" in unsandboxed and "fence" in unsandboxed
    boxed = describe(tmp_path, "docker", extra_env=("LANG",))
    assert "network none" in boxed and WORKDIR in boxed and "LANG" in boxed
    assert "network host" in describe(tmp_path, "docker", allow_network=True)


@pytest.mark.skipif(not docker_up(), reason="docker is not running here")
def test_a_real_container_sees_only_the_project(tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    (tmp_path / "outside.txt").write_text("host")
    result = run_agent_in_sandbox(
        project, "cat > out.txt; ls /work; test -e /work/../outside.txt && echo LEAK; "
                 "wget -q -T 3 -O /dev/null http://example.com && echo NET || echo NONET",
        "hello from stdin", 120, Policy(image="alpine:3.20"))
    assert result.returncode == 0, result.stderr
    assert (project / "out.txt").read_text() == "hello from stdin"
    assert "LEAK" not in result.stdout and "NONET" in result.stdout
