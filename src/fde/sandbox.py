"""Where the coding agent runs.

The implement loop's fence catches what the agent changed: protected
files are hashed first, restored and reported if touched, planted files
removed. A fence cannot stop the agent reading the rest of the machine,
its secrets or its network. A container can, by construction: only the
project is mounted, the root filesystem is read-only with a scratch
/tmp, every capability is dropped and none can be gained, the process
runs as the caller rather than root, memory, CPU and process counts are
bounded, the environment is an allowlist, and the network is off unless
somebody with a name and a reason turned it on. The policy is data in
the emitted project (`ops/agent-policy.yaml`) and lists only what is
enforced. The image the agent actually ran on is recorded by digest, so
the run can be repeated on the same bytes; a policy may pin one.
Without `--sandbox` the fence still applies and the agent has the host,
which the implementation log says.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from fde.models.base import says_something

DEFAULT_IMAGE = "python:3.12-slim"
DEFAULT_ENV_ALLOW = ("PATH", "HOME", "LANG", "LC_ALL", "TERM", "USER")
DEFAULT_MEMORY = "4g"
DEFAULT_CPUS = "2"
DEFAULT_PIDS = 512
WORKDIR = "/work"
SCRATCH_HOME = "/tmp/home"
CONTAINER_OWN = {"PATH", "HOME"}  # the image's, never the host's


@dataclass
class Policy:
    image: str = DEFAULT_IMAGE
    network: str = "none"  # none | host
    network_reason: str = ""  # who allowed it and why; without one, host is read as none
    env_allow: list[str] = field(default_factory=lambda: list(DEFAULT_ENV_ALLOW))
    memory: str = DEFAULT_MEMORY
    cpus: str = DEFAULT_CPUS
    pids: int = DEFAULT_PIDS
    notes: list[str] = field(default_factory=list)

    @property
    def network_open(self) -> bool:
        return self.network == "host" and says_something(self.network_reason)


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
        policy.notes.append("agent-policy.yaml unreadable: defaults applied")
        return policy
    if not isinstance(raw, dict):
        return policy
    if isinstance(raw.get("image"), str) and raw["image"].strip():
        policy.image = raw["image"].strip()
    if raw.get("network") in ("none", "host"):
        policy.network = raw["network"]
    policy.network_reason = str(raw.get("network_reason") or "")
    if policy.network == "host" and not says_something(policy.network_reason):
        policy.notes.append("network: host without a network_reason -- read as none")
    if isinstance(raw.get("env_allow"), list):
        policy.env_allow = [str(x) for x in raw["env_allow"] if str(x).strip()]
    if isinstance(raw.get("memory"), str) and raw["memory"].strip():
        policy.memory = raw["memory"].strip()
    if isinstance(raw.get("cpus"), (str, int, float)) and str(raw["cpus"]).strip():
        policy.cpus = str(raw["cpus"]).strip()
    if isinstance(raw.get("pids"), int) and raw["pids"] > 0:
        policy.pids = raw["pids"]
    return policy


def environment(policy: Policy, extra: Iterable[str] = ()) -> dict[str, str]:
    """The host environment reduced to the allowlist: what the docker
    client runs with, and the only names forwarded into the container."""
    names = list(policy.env_allow) + [n for n in extra if n]
    return {name: os.environ[name] for name in names if name in os.environ}


def caller() -> str | None:
    """uid:gid of the person running the loop, so the container writes
    the project as them and never as root. None where the platform has
    no notion of it."""
    try:
        return f"{os.getuid()}:{os.getgid()}"
    except AttributeError:  # pragma: no cover - Windows
        return None


def docker_command(project: Path, agent_cmd: str, policy: Policy, env: dict[str, str],
                   allow_network: str = "", user: str | None = None) -> list[str]:
    """The container run. Only the project mounted, at /work; root
    read-only with a scratch /tmp; no capabilities and no way to gain
    one; the caller's user; bounded memory, CPU and processes; the
    network off unless allowed with a reason; values forwarded by name
    from the client's own reduced environment, never on the command line."""
    command = ["docker", "run", "--rm", "-i",
               "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "--read-only", "--tmpfs", "/tmp:rw,size=256m",
               "--pids-limit", str(policy.pids), "--memory", policy.memory,
               "--cpus", policy.cpus,
               "-v", f"{Path(project).resolve()}:{WORKDIR}", "-w", WORKDIR,
               "-e", f"HOME={SCRATCH_HOME}"]
    user = caller() if user is None else user
    if user:
        command += ["--user", user]
    if not (policy.network_open or says_something(allow_network)):
        command += ["--network", "none"]
    for name in env:
        if name not in CONTAINER_OWN:
            command += ["-e", name]
    command += [policy.image, "sh", "-lc", f"mkdir -p {SCRATCH_HOME} && {agent_cmd}"]
    return command


def image_digest(image: str) -> str | None:
    """The digest of the image as it is on this machine, so the log can
    name the bytes the agent ran on; None when docker cannot say."""
    try:
        result = subprocess.run(  # noqa: S603 - a fixed docker query
            ["docker", "image", "inspect", "--format", "{{index .RepoDigests 0}}", image],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    digest = result.stdout.strip()
    return digest if result.returncode == 0 and "@sha256:" in digest else None


def describe(project: Path, sandbox: str | None, extra_env: Iterable[str] = (),
             allow_network: str = "") -> str:
    if sandbox != "docker":
        return "the host, unsandboxed: the fence restores protected files, nothing else is kept out"
    policy = load_policy(project)
    if policy.network_open:
        network = f"host, allowed by the policy: {policy.network_reason.strip()}"
    elif says_something(allow_network):
        network = f"host, allowed by: {allow_network.strip()}"
    else:
        network = "none"
    names = [n for n in list(policy.env_allow) + list(extra_env) if n in os.environ]
    digest = image_digest(policy.image)
    image = f"{policy.image} ({digest})" if digest and "@" not in policy.image else policy.image
    return (f"docker, image {image}, network {network}, only the project mounted at {WORKDIR}, "
            f"root read-only, no capabilities, user {caller() or 'the image default'}, "
            f"memory {policy.memory}, cpus {policy.cpus}, pids {policy.pids}, environment "
            f"{', '.join(names) or 'empty'}"
            + (f"; notes: {'; '.join(policy.notes)}" if policy.notes else ""))


def run_agent_in_sandbox(project: Path, agent_cmd: str, stdin: str, timeout: float,
                         policy: Policy, extra_env: Iterable[str] = (),
                         allow_network: str = "") -> subprocess.CompletedProcess:
    env = environment(policy, extra_env)
    command = docker_command(project, agent_cmd, policy, env, allow_network)
    client_env = {**env, "PATH": os.environ.get("PATH", "/usr/bin"),
                  "HOME": os.environ.get("HOME", "/")}
    return subprocess.run(  # noqa: S603 - the agent is the caller's own command
        command, input=stdin, capture_output=True, text=True, timeout=timeout, env=client_env,
    )
