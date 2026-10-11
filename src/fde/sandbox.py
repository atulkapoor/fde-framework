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
import re
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
# Ceilings on what any policy may ask for. Above them the default applies
# and the policy's note says so: a limit is not a limit if the file it
# bounds can raise it without end.
MAX_MEMORY_BYTES = 64 * 1024 ** 3
MAX_CPUS = 64.0
MAX_PIDS = 8192
# A forwarded name is a name: letters, digits, underscores. Names that
# change what any process loads are refused whoever asks.
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,255}$")
ENV_DENIED_PREFIXES = ("LD_", "DYLD_")
WORKDIR = "/work"
SCRATCH_HOME = "/tmp/home"
CONTAINER_OWN = {"PATH", "HOME"}  # the image's, never the host's


@dataclass
class Policy:
    """What the project's ops/agent-policy.yaml may say. The file lives
    inside the directory the agent writes to, so it can only narrow: the
    image and the resource limits (within ceilings) are read from it; a
    network, or a name beyond the default allowlist, is a request it
    records and only the person at the terminal grants, with
    --allow-network and --env-allow. Before this rule an agent could set
    `network: host` with a reason of its own and add a credential to
    `env_allow`, and the next run would have honoured both."""
    image: str = DEFAULT_IMAGE
    network: str = "none"  # none | host: the project's request, not a grant
    network_reason: str = ""  # the request's reason, for the log
    env_allow: list[str] = field(default_factory=lambda: list(DEFAULT_ENV_ALLOW))
    requested_env: list[str] = field(default_factory=list)  # beyond the defaults; not granted
    memory: str = DEFAULT_MEMORY
    cpus: str = DEFAULT_CPUS
    pids: int = DEFAULT_PIDS
    notes: list[str] = field(default_factory=list)

    @property
    def network_requested(self) -> bool:
        return self.network == "host"


def valid_env_name(name: str) -> bool:
    return bool(ENV_NAME.match(name)) and not name.upper().startswith(ENV_DENIED_PREFIXES)


def memory_bytes(value: str) -> int | None:
    """Docker's memory syntax -- 512m, 4g, 1024k, or bytes -- as a number;
    None when it is not one."""
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([bkmgBKMG]?)\s*", str(value))
    if not match:
        return None
    scale = {"": 1, "b": 1, "k": 1024, "m": 1024 ** 2, "g": 1024 ** 3}[match.group(2).lower()]
    return int(float(match.group(1)) * scale)


def load_policy(project: Path) -> Policy:
    """The project's policy, or the defaults when it has none or it cannot
    be read -- a broken policy file must not widen what the agent gets,
    and neither may a well-formed one: see Policy."""
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
    if policy.network == "host":
        policy.notes.append("network: host is the policy's request, not a grant; the network "
                            "opens only with --allow-network \"who: why\" at the terminal")
    if isinstance(raw.get("env_allow"), list):
        asked = [str(x).strip() for x in raw["env_allow"] if str(x).strip()]
        policy.env_allow = [n for n in asked if n in DEFAULT_ENV_ALLOW]
        beyond = [n for n in asked if n not in DEFAULT_ENV_ALLOW]
        policy.requested_env = [n for n in beyond if valid_env_name(n)]
        if policy.requested_env:
            policy.notes.append(f"env_allow asks for {', '.join(policy.requested_env)} beyond "
                                "the defaults; forwarded only with --env-allow at the terminal")
        refused = [n for n in beyond if not valid_env_name(n)]
        if refused:
            policy.notes.append(f"env_allow names refused: {', '.join(refused)}")
    if isinstance(raw.get("memory"), str) and raw["memory"].strip():
        asked_bytes = memory_bytes(raw["memory"])
        if asked_bytes is None or asked_bytes <= 0 or asked_bytes > MAX_MEMORY_BYTES:
            policy.notes.append(f"memory {raw['memory'].strip()!r} is not within "
                                f"(0, {MAX_MEMORY_BYTES // 1024 ** 3}g]: default applied")
        else:
            policy.memory = raw["memory"].strip()
    if isinstance(raw.get("cpus"), (str, int, float)) and str(raw["cpus"]).strip():
        try:
            asked_cpus = float(raw["cpus"])
        except (TypeError, ValueError):
            asked_cpus = None
        if asked_cpus is None or asked_cpus <= 0 or asked_cpus > MAX_CPUS:
            policy.notes.append(f"cpus {raw['cpus']!r} is not within (0, {MAX_CPUS:g}]: "
                                "default applied")
        else:
            policy.cpus = str(raw["cpus"]).strip()
    if isinstance(raw.get("pids"), int) and not isinstance(raw.get("pids"), bool):
        if 0 < raw["pids"] <= MAX_PIDS:
            policy.pids = raw["pids"]
        else:
            policy.notes.append(f"pids {raw['pids']} is not within (0, {MAX_PIDS}]: "
                                "default applied")
    return policy


def environment(policy: Policy, extra: Iterable[str] = ()) -> dict[str, str]:
    """The host environment reduced to the allowlist: what the docker
    client runs with, and the only names forwarded into the container.
    `extra` is what the person at the terminal granted with --env-allow;
    a name that is not a name, or that changes what a process loads, is
    not forwarded whoever asks."""
    names = list(policy.env_allow) + [n for n in extra if n]
    return {name: os.environ[name] for name in names
            if valid_env_name(name) and name in os.environ}


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
    if not says_something(allow_network):
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


def lock_image(project: Path, policy: Policy) -> str | None:
    """Pin the image the agent just ran on into the policy by digest, so
    every later run uses the same bytes. Returns the digest written, or
    None when the policy is already pinned or docker cannot name one."""
    if "@sha256:" in policy.image:
        return None
    digest = image_digest(policy.image)
    if not digest:
        return None
    path = Path(project) / "ops" / "agent-policy.yaml"
    if not path.exists():
        return None
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("image:"):
            lines[i] = f"image: {digest}   # pinned by fde implement from {policy.image}"
            path.write_text("\n".join(lines) + "\n")
            return digest
    return None


def describe(project: Path, sandbox: str | None, extra_env: Iterable[str] = (),
             allow_network: str = "") -> str:
    if sandbox != "docker":
        return "the host, unsandboxed: the fence restores protected files, nothing else is kept out"
    policy = load_policy(project)
    if says_something(allow_network):
        network = f"host, allowed by: {allow_network.strip()}"
    elif policy.network_requested:
        network = "none (the policy asks for host; grant it with --allow-network)"
    else:
        network = "none"
    names = sorted(environment(policy, extra_env))
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
