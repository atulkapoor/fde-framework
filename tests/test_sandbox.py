"""The sandbox: only the project mounted, root read-only, no capabilities,
the caller's user, bounded resources, an allowlisted environment, and no
network without a name and a reason -- by construction."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from fde import implement as implement_module
from fde.sandbox import (
    DEFAULT_IMAGE,
    SCRATCH_HOME,
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
        "image: ghcr.io/example/agent@sha256:abc\nnetwork: host\n"
        "network_reason: 'Priya: the agent calls a hosted model'\n"
        "env_allow: [PATH, ANTHROPIC_API_KEY]\nmemory: 8g\ncpus: 4\npids: 1024\n")
    policy = load_policy(tmp_path)
    assert policy.image == "ghcr.io/example/agent@sha256:abc" and policy.network_open
    assert policy.env_allow == ["PATH", "ANTHROPIC_API_KEY"]
    assert (policy.memory, policy.cpus, policy.pids) == ("8g", "4", 1024)
    (tmp_path / "ops" / "agent-policy.yaml").write_text("network: [everything\n")
    assert load_policy(tmp_path).network == "none"  # unreadable never widens


def test_a_network_without_a_reason_is_read_as_none(tmp_path):
    (tmp_path / "ops").mkdir()
    (tmp_path / "ops" / "agent-policy.yaml").write_text("network: host\n")
    policy = load_policy(tmp_path)
    assert not policy.network_open and any("network_reason" in n for n in policy.notes)
    assert "--network" in docker_command(tmp_path, "x", policy, {}, user="1:1")


def test_the_environment_is_the_allowlist_and_nothing_else(monkeypatch):
    monkeypatch.setenv("SECRET_TOKEN", "s")
    monkeypatch.setenv("LANG", "en_GB.UTF-8")
    env = environment(Policy(), extra=("NOT_SET",))
    assert "SECRET_TOKEN" not in env and env["LANG"] == "en_GB.UTF-8"
    assert "NOT_SET" not in env
    assert environment(Policy(), extra=("SECRET_TOKEN",))["SECRET_TOKEN"] == "s"


def test_the_container_is_closed_by_construction(tmp_path):
    command = docker_command(tmp_path, "aider --yes", Policy(),
                             {"PATH": "/x", "HOME": "/h", "LANG": "C", "KEY": "k"},
                             user="501:20")
    assert command[:4] == ["docker", "run", "--rm", "-i"]
    for flag, value in (("--cap-drop", "ALL"), ("--security-opt", "no-new-privileges"),
                        ("--tmpfs", "/tmp:rw,size=256m"), ("--pids-limit", "512"),
                        ("--memory", "4g"), ("--cpus", "2"), ("-w", WORKDIR),
                        ("--user", "501:20"), ("--network", "none")):
        assert command[command.index(flag) + 1] == value, flag
    assert "--read-only" in command
    assert f"{tmp_path.resolve()}:{WORKDIR}" in command
    assert f"HOME={SCRATCH_HOME}" in command
    forwarded = [command[i + 1] for i, part in enumerate(command) if part == "-e"]
    assert forwarded == [f"HOME={SCRATCH_HOME}", "LANG", "KEY"]  # the image keeps its PATH
    assert "k" not in command  # values never on the command line
    assert command[-4:-1] == [DEFAULT_IMAGE, "sh", "-lc"]
    assert command[-1].endswith("&& aider --yes")


def test_the_network_opens_only_with_a_name_and_a_reason(tmp_path):
    assert "--network" in docker_command(tmp_path, "x", Policy(), {}, allow_network="   ",
                                         user="1:1")
    opened = docker_command(tmp_path, "x", Policy(), {},
                            allow_network="Priya: hosted model", user="1:1")
    assert "--network" not in opened
    by_policy = docker_command(tmp_path, "x", Policy(network="host",
                                                     network_reason="Dev: package index"),
                               {}, user="1:1")
    assert "--network" not in by_policy


def test_the_loop_runs_the_agent_through_docker_when_asked(tmp_path, monkeypatch):
    project = tmp_path / "p"
    (project / ".implement").mkdir(parents=True)
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["env"] = kwargs.get("env")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("fde.sandbox.subprocess.run", fake_run)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "never")
    ok = implement_module._run_agent(project, "agent --message-file {prompt_file}", "the brief",
                                     10, sandbox="docker", env_allow=("ANTHROPIC_API_KEY",))
    assert ok and seen["command"][0] == "docker"
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
    monkeypatch.setattr("fde.sandbox.image_digest", lambda image: None)
    unsandboxed = describe(tmp_path, None)
    assert "unsandboxed" in unsandboxed and "fence" in unsandboxed
    boxed = describe(tmp_path, "docker", extra_env=("LANG",))
    for expected in ("network none", WORKDIR, "LANG", "root read-only", "no capabilities",
                     "memory 4g", "pids 512"):
        assert expected in boxed, expected
    opened = describe(tmp_path, "docker", allow_network="Priya: hosted model")
    assert "network host, allowed by: Priya: hosted model" in opened


def test_the_digest_of_the_image_is_on_the_log_when_docker_knows_it(tmp_path, monkeypatch):
    monkeypatch.setattr("fde.sandbox.image_digest",
                        lambda image: "python@sha256:deadbeef" if image == DEFAULT_IMAGE else None)
    assert "python:3.12-slim (python@sha256:deadbeef)" in describe(tmp_path, "docker")


@pytest.mark.skipif(not docker_up(), reason="docker is not running here")
def test_a_real_container_is_closed(tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    (tmp_path / "outside.txt").write_text("host")
    result = run_agent_in_sandbox(
        project,
        "cat > out.txt; test -e /work/../outside.txt && echo LEAK; "
        "touch /etc/probe 2>/dev/null && echo RW_ROOT || echo RO_ROOT; "
        "touch $HOME/probe && echo HOME_OK; "
        "wget -q -T 3 -O /dev/null http://example.com && echo NET || echo NONET; "
        "id -u",
        "hello from stdin", 120, Policy(image="alpine:3.20"))
    assert result.returncode == 0, result.stderr
    assert (project / "out.txt").read_text() == "hello from stdin"
    out = result.stdout
    assert "LEAK" not in out and "RO_ROOT" in out and "HOME_OK" in out and "NONET" in out
    assert out.strip().splitlines()[-1] != "0"  # not root
