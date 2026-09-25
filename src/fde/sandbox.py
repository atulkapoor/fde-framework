"""Where the coding agent runs.

The implement loop's fence catches what the agent changed: protected
files are hashed first, restored and reported if touched, planted files
removed. A fence cannot stop the agent reading the rest of the machine,
its secrets or its network. A sandbox can: the agent runs in a container
with only the project mounted, an environment reduced to an allowlist,
and no network unless the engagement allows it -- by construction, not
by inspection afterwards. The policy is data in the emitted project
(`ops/agent-policy.yaml`) so a reviewer can read what the agent was
given; without `--sandbox` the fence still applies and the agent has the
host, which the implementation log says.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_IMAGE = "python:3.12-slim"
DEFAULT_ENV_ALLOW = ("PATH", "HOME", "LANG", "LC_ALL", "TERM", "USER")
WORKDIR = "/work"
CONTAINER_OWN = {"PATH", "HOME"}  # the image's, never the host's


@dataclass
class Policy:
    image: str = DEFAULT_IMAGE
    network: str = "none"  # none | host
    env_allow: list[str] = field(default_factory=lambda: list(DEFAULT_ENV_ALLOW))
    processes: list[str] = field(default_factory=list)


def load_policy(project: Path) -> Policy:
    """The project's policy, or the defaults when it has none or it cannot
    be read -- a broken policy file must not widen what the agent gets."""
    policy = Policy()
    path = Path(project) / "ops" / "agent-policy.yaml"
    if not path.exists():
        return policy
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError:
        return policy
    if not isinstance(raw, dict):
        return policy
    if raw.get("network") in ("none", "host"):
        policy.network = raw["network"]
    if isinstance(raw.get("env_allow"), list):
        policy.env_allow = [str(x) for x in raw["env_allow"] if str(x).strip()]
    if isinstance(raw.get("image"), str) and raw["image"].strip():
        policy.image = raw["image"].strip()
    if isinstance(raw.get("processes"), list):
        policy.processes = [str(x) for x in raw["processes"]]
    return policy


def environment(policy: Policy, extra: Iterable[str] = ()) -> dict[str, str]:
    """The host environment reduced to the allowlist: what the docker
    client runs with, and the only names forwarded into the container."""
    names = list(policy.env_allow) + [n for n in extra if n]
    return {name: os.environ[name] for name in names if name in os.environ}


def docker_command(project: Path, agent_cmd: str, policy: Policy, env: dict[str, str],
                   allow_network: bool = False) -> list[str]:
    """The container run: only the project mounted, at /work; the network
    off unless allowed; values forwarded by name from the client's own
    reduced environment, never written on the command line."""
    command = ["docker", "run", "--rm", "-i",
               "-v", f"{Path(project).resolve()}:{WORKDIR}", "-w", WORKDIR]
    if policy.network == "none" and not allow_network:
        command += ["--network", "none"]
    for name in env:
        if name not in CONTAINER_OWN:
            command += ["-e", name]
    command += [policy.image, "sh", "-lc", agent_cmd]
    return command


def describe(project: Path, sandbox: str | None, extra_env: Iterable[str] = (),
             allow_network: bool = False) -> str:
    if sandbox != "docker":
        return "the host, unsandboxed: the fence restores protected files, nothing else is kept out"
    policy = load_policy(project)
    network = "host" if (policy.network == "host" or allow_network) else "none"
    names = [n for n in list(policy.env_allow) + list(extra_env) if n in os.environ]
    return (f"docker, image {policy.image}, network {network}, only the project mounted at "
            f"{WORKDIR}, environment {', '.join(names) or 'empty'}")


def run_agent_in_sandbox(project: Path, agent_cmd: str, stdin: str, timeout: float,
                         policy: Policy, extra_env: Iterable[str] = (),
                         allow_network: bool = False) -> subprocess.CompletedProcess:
    env = environment(policy, extra_env)
    command = docker_command(project, agent_cmd, policy, env, allow_network)
    client_env = {**env, "PATH": os.environ.get("PATH", "/usr/bin"),
                  "HOME": os.environ.get("HOME", "/")}
    return subprocess.run(  # noqa: S603 - the agent is the caller's own command
        command, input=stdin, capture_output=True, text=True, timeout=timeout, env=client_env,
    )
