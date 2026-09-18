"""The deployment artefacts, chosen rather than defaulted.

What gets written follows the decision. A service-unit deployment gets no
Dockerfile, a cluster deployment gets manifests and no Terraform, and an
Ansible shop gets a playbook whatever the topology.

Two things are written regardless of the choice.

**A README naming the decisions.** Somebody opening deploy/ six months later
should not have to infer why it looks like this from what is in it.

**TEARDOWN.md.** An FDE who cannot cleanly undo a demo has a problem, and only
one provisioning option knows what it created. Where the tool has no destroy,
the manual steps are written out rather than left implied.
"""

from __future__ import annotations

from pathlib import Path

# Buildable as emitted; pin before production. A moving tag means two builds
# of the same commit can differ, which turns a reproducibility question into
# an archaeology one -- but an unresolvable placeholder digest means nothing
# builds at all, which is worse. The Dockerfile carries the instruction.
PYTHON_BASE = "python:3.12-slim"


def write_deploy(architecture, out: Path) -> None:
    deploy = out / "deploy"
    deploy.mkdir(parents=True, exist_ok=True)
    _write_env_example(architecture, deploy)

    substrate = _approach(architecture, "deployment")
    provisioner = _approach(architecture, "provisioning")
    air_gapped = architecture.topology == "air-gapped"

    if substrate == "systemd-unit":
        _systemd(deploy, boundary=bool(architecture.graph.sensitive_nodes()))
    elif substrate == "compose":
        _container(out, deploy, air_gapped)
        _compose(deploy)
    elif substrate == "kubernetes-manifests":
        _container(out, deploy, air_gapped)
        _manifests(deploy)
    elif substrate:
        _unemitted(deploy, "deployment", substrate)

    if provisioner == "terraform-module":
        _terraform(deploy, air_gapped)
    elif provisioner == "ansible-playbook":
        _ansible(deploy, substrate)
    elif provisioner == "gitops":
        _gitops(deploy)
    elif provisioner == "manual-runbook":
        _manual_runbook(deploy)
    elif provisioner:
        _unemitted(deploy, "provisioning", provisioner)

    _readme(deploy, substrate, provisioner, architecture.topology)
    _teardown(deploy, substrate, provisioner)


def _unemitted(deploy: Path, component: str, approach: str) -> None:
    """An approach the registry knows and this emitter does not.

    Written down rather than skipped: the registry can grow a deployment
    approach faster than this module grows a branch for it, and an empty
    deploy directory reads as a finished one.
    """
    (deploy / f"UNEMITTED-{component}.md").write_text(
        f"# {approach}: decided, not emitted\n\n"
        f"The registry decided {approach!r} for {component}, and this version "
        f"of the emitter has no assets for it. The decision stands -- write "
        f"the assets by hand, and consider contributing the emitter branch.\n"
    )


# --- substrate -----------------------------------------------------------


def _systemd(deploy: Path, boundary: bool = False) -> None:
    (deploy / "systemd").mkdir(exist_ok=True)
    # The egress fence the kernel enforces: on a build whose data may not
    # leave, the process can reach loopback and private ranges and nothing
    # else -- app/boundary.py checks the URLs, this checks the packets.
    egress = (
        "# Data may not leave: the kernel allows loopback and private ranges\n"
        "# only. Add the model server's address here if it lives elsewhere.\n"
        "IPAddressDeny=any\n"
        "IPAddressAllow=localhost 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 fc00::/7\n"
        if boundary else ""
    )
    (deploy / "systemd" / "app.service").write_text(
        "# Rung zero, and frequently the right answer rather than the lesser one.\n"
        "# Understood by anyone who has administered a Linux box, restarts on\n"
        "# failure, starts on boot, and adds nothing anybody has to learn.\n"
        "[Unit]\n"
        "Description=Generated application\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n\n"
        "# A crash loop is a signal, not a lifestyle: five restarts in two\n"
        "# minutes stops the unit so the journal can be read in peace.\n"
        "StartLimitIntervalSec=120\n"
        "StartLimitBurst=5\n\n"
        "[Service]\n"
        "Type=simple\n"
        "User=app\n"
        "# Releases live side by side; `current` is a symlink, which is what\n"
        "# makes ops/rollback.md one atomic command instead of a re-install.\n"
        "WorkingDirectory=/opt/app/current\n"
        "# One configuration story: defaults here, overrides in the env\n"
        "# file. Unbuffered stdout so journalctl shows the truth at 3am. The\n"
        "# env file is required: a service that boots without its\n"
        "# configuration is a service serving traffic misconfigured.\n"
        "Environment=PYTHONUNBUFFERED=1\n"
        "Environment=STATE_DIR=/var/lib/app\n"
        "EnvironmentFile=/etc/app/env\n"
        "ExecStart=/opt/app/current/.venv/bin/python -m app.service\n"
        "Restart=on-failure\n"
        "RestartSec=5\n"
        "# Exit 78 is EX_CONFIG: the service refused its configuration with\n"
        "# one clear line. Restarting it would only repeat the line.\n"
        "RestartPreventExitStatus=78\n"
        "# Drain: SIGTERM lets in-flight requests finish; the kill comes later.\n"
        "KillSignal=SIGTERM\n"
        "TimeoutStopSec=45\n"
        "# Least privilege costs nothing here and is awkward to add later.\n"
        "# StateDirectory creates /var/lib/app owned by the service user.\n"
        "StateDirectory=app\n"
        "NoNewPrivileges=true\n"
        "PrivateTmp=true\n"
        "PrivateDevices=true\n"
        "ProtectSystem=strict\n"
        "ProtectHome=true\n"
        "ProtectKernelTunables=true\n"
        "ProtectKernelModules=true\n"
        "ProtectKernelLogs=true\n"
        "ProtectControlGroups=true\n"
        "ProtectClock=true\n"
        "ProtectHostname=true\n"
        "RestrictNamespaces=true\n"
        "RestrictRealtime=true\n"
        "RestrictSUIDSGID=true\n"
        "LockPersonality=true\n"
        "RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX\n"
        "SystemCallFilter=@system-service\n"
        "SystemCallArchitectures=native\n"
        "CapabilityBoundingSet=\n"
        "UMask=0077\n"
        "# Resource ceilings: a thread-per-connection server without them is\n"
        "# a denial of service one slow client away. The memory budget is\n"
        "# the index (about twenty megabytes per megabyte of corpus text,\n"
        "# measured -- CORPUS_MAX_MB in the env file must agree with this)\n"
        "# plus TasksMax x MAX_BODY_BYTES of request bodies in flight.\n"
        "TasksMax=128\n"
        "MemoryMax=2G\n"
        "LimitNOFILE=4096\n"
        f"{egress}"
        "\n[Install]\n"
        "WantedBy=multi-user.target\n"
    )


def _container(out: Path, deploy: Path, air_gapped: bool) -> None:
    registry = (
        "# Air-gapped: this base must already be in the internal registry.\n"
        "# Nothing here reaches a public one, by construction.\n"
        if air_gapped else ""
    )
    (out / "Dockerfile").write_text(
        "# Buildable as emitted. Before production, pin by digest\n"
        "# (FROM python@sha256:...): a moving tag means two builds of the same\n"
        "# commit can differ, which turns a reproducibility question into an\n"
        "# archaeology one.\n"
        f"{registry}"
        f"FROM {PYTHON_BASE}\n\n"
        "WORKDIR /opt/app\n"
        "COPY pyproject.toml ./\n"
        "RUN pip install --no-cache-dir -e .\n"
        "COPY app ./app\n"
        "COPY evals ./evals\n\n"
        "# Not root. The default is root and the default is wrong.\n"
        "RUN useradd --system --uid 10001 app && chown -R app /opt/app\n"
        "USER app\n\n"
        'CMD ["python", "-m", "app.pipeline"]\n'
    )
    # At the context root: compose builds with context .., so a
    # .dockerignore inside deploy/ is a file Docker never reads.
    (out / ".dockerignore").write_text(".venv\n__pycache__\n*.pyc\n.git\n")


def _compose(deploy: Path) -> None:
    (deploy / "compose.yaml").write_text(
        "# One host, declared. Its limit is honest: while this host restarts,\n"
        "# the service is down. If that is unacceptable, the next rung is the\n"
        "# answer rather than a workaround here.\n"
        "services:\n"
        "  app:\n"
        "    build: ..\n"
        "    restart: unless-stopped\n"
        "    read_only: true\n"
        "    tmpfs: [/tmp]\n"
        "    cap_drop: [ALL]\n"
        "    security_opt: [no-new-privileges:true]\n"
        "    healthcheck:\n"
        '      test: ["CMD", "python", "-c", "import app.pipeline"]\n'
        "      interval: 30s\n"
    )


def _manifests(deploy: Path) -> None:
    (deploy / "manifests").mkdir(exist_ok=True)
    (deploy / "manifests" / "deployment.yaml").write_text(
        "# Applied to a cluster that already exists. Cheap because somebody\n"
        "# else patches it -- which is the entire argument for a platform.\n"
        "apiVersion: apps/v1\n"
        "kind: Deployment\n"
        "metadata:\n"
        "  name: app\n"
        "spec:\n"
        "  replicas: 2\n"
        "  selector:\n"
        "    matchLabels: {app: app}\n"
        "  template:\n"
        "    metadata:\n"
        "      labels: {app: app}\n"
        "    spec:\n"
        "      securityContext:\n"
        "        runAsNonRoot: true\n"
        "        runAsUser: 10001\n"
        "      containers:\n"
        "        - name: app\n"
        "          image: app@sha256:REPLACE_WITH_DIGEST\n"
        "          # Both set. A limit without a request is a pod the scheduler\n"
        "          # cannot place sensibly; a request without a limit is a\n"
        "          # neighbour nobody can protect.\n"
        "          resources:\n"
        "            requests: {cpu: 500m, memory: 512Mi}\n"
        "            limits: {cpu: '2', memory: 2Gi}\n"
        "          securityContext:\n"
        "            allowPrivilegeEscalation: false\n"
        "            readOnlyRootFilesystem: true\n"
        "            capabilities: {drop: [ALL]}\n"
    )


# --- provisioning --------------------------------------------------------


def _terraform(deploy: Path, air_gapped: bool) -> None:
    directory = deploy / "terraform"
    directory.mkdir(exist_ok=True)
    mirror = (
        "\n# Air-gapped: providers come from a filesystem mirror, because there\n"
        "# is no registry to reach. Run `terraform providers mirror ./vendor`\n"
        "# somewhere with network access and carry the result in.\n"
        'provider_installation {\n  filesystem_mirror { path = "./vendor" }\n}\n'
        if air_gapped else ""
    )
    (directory / "main.tf").write_text(
        "# Chosen because this environment has to be destroyed cleanly, which is\n"
        "# the one thing a convergence tool cannot do.\n"
        "terraform {\n"
        '  required_version = ">= 1.5"\n'
        "}\n"
        f"{mirror}\n"
        "variable \"environment\" {\n"
        "  type        = string\n"
        "  description = \"Name of this environment. Used in every resource name\"\n"
        "}\n\n"
        "# Resources go here. Keep them in one module per environment so that\n"
        "# `terraform destroy` takes exactly one environment away.\n"
    )
    if air_gapped:
        (directory / "vendor").mkdir(exist_ok=True)
        (directory / "vendor" / ".gitkeep").write_text("")


def _ansible(deploy: Path, substrate: str | None = None) -> None:
    directory = deploy / "ansible"
    directory.mkdir(exist_ok=True)
    # The unit-file tasks exist only when the substrate emitted a unit file:
    # a playbook copying deploy/systemd/ beside a compose substrate fails on
    # its first task, against a file this emitter never wrote.
    unit_tasks = (
        "    - name: Point `current` at this release (what the unit runs; what rollback moves)\n"
        "      ansible.builtin.file:\n"
        "        src: '/opt/app/releases/{{ release }}'\n"
        "        dest: /opt/app/current\n"
        "        state: link\n"
        "    - name: Environment file the unit reads (never overwrites an edited one)\n"
        "      ansible.builtin.copy:\n"
        "        src: ../env.example\n"
        "        dest: /etc/app/env\n"
        "        mode: '0640'\n"
        "        force: false\n"
        "    - name: Install the service unit\n"
        "      ansible.builtin.copy:\n"
        "        src: ../systemd/app.service\n"
        "        dest: /etc/systemd/system/app.service\n"
        "      notify: restart app\n"
        "  handlers:\n"
        "    - name: restart app\n"
        "      ansible.builtin.systemd:\n"
        "        name: app\n"
        "        state: restarted\n"
        "        daemon_reload: true\n"
        "        enabled: true\n"
        if substrate == "systemd-unit" else
        "    # The substrate deploys through its own mechanism; this playbook\n"
        "    # only stages the application onto the host.\n"
    )
    (directory / "site.yml").write_text(
        "# Chosen because this is what the team already operates. They maintain\n"
        "# it after the engagement ends, and the tool they cannot maintain is\n"
        "# the one that rots.\n"
        "- name: Deploy the application\n"
        "  hosts: app\n"
        "  become: true\n"
        "  vars:\n"
        "    release: \"{{ lookup('pipe', 'date +%Y%m%d%H%M%S') }}\"\n"
        "  tasks:\n"
        "    - name: Create the service account\n"
        "      ansible.builtin.user:\n"
        "        name: app\n"
        "        system: true\n"
        "        shell: /usr/sbin/nologin\n"
        "        home: /opt/app\n"
        "    - name: Stage the release (the package, not the working tree)\n"
        "      ansible.builtin.copy:\n"
        "        src: '../../{{ item }}'\n"
        "        dest: '/opt/app/releases/{{ release }}/'\n"
        "        owner: app\n"
        "      loop: [app, evals, pyproject.toml]\n"
        "    - name: Interpreter the unit's ExecStart= names\n"
        "      ansible.builtin.pip:\n"
        "        name: '/opt/app/releases/{{ release }}'\n"
        "        virtualenv: '/opt/app/releases/{{ release }}/.venv'\n"
        "        virtualenv_command: python3 -m venv\n"
        f"{unit_tasks}"
    )
    (directory / "inventory.ini").write_text(
        "# Hosts that already exist. Nothing here creates a machine, because\n"
        "# somebody already did.\n"
        "[app]\n"
        "# app-01.internal\n"
    )


def _manual_runbook(deploy: Path) -> None:
    (deploy / "runbook.md").write_text(
        "# Provisioning runbook\n\n"
        "Chosen because nothing here can be provisioned through an API --\n"
        "somebody files a ticket, somebody racks a machine -- so the honest\n"
        "artefact is the list of steps a person follows, written down once\n"
        "instead of re-derived per environment.\n\n"
        "Fill in each step as it is learned. A runbook nobody updates is a\n"
        "runbook that lies.\n\n"
        "## Request\n\n1. _who to ask, and for what_\n\n"
        "## Verify\n\n1. _what proves the environment is usable_\n\n"
        "## Hand back\n\n1. _how this environment is returned or destroyed_\n"
    )


def _gitops(deploy: Path) -> None:
    (deploy / "gitops.md").write_text(
        "# Reconciled onto an existing cluster\n\n"
        "The infrastructure is somebody else's problem. Adding a provisioner "
        "here would provision nothing and give whoever takes this over a second "
        "thing to maintain.\n\n"
        "What this buys instead is that the deployed state is reviewable and "
        "revertable by whoever already reviews changes -- which is usually the "
        "property people wanted from a provisioning tool in the first place.\n\n"
        "Point the cluster's reconciler at `deploy/manifests`.\n"
    )


# --- always --------------------------------------------------------------


def _readme(deploy: Path, substrate: str | None, provisioner: str | None,
            topology: str) -> None:
    (deploy / "README.md").write_text(
        f"# Deployment\n\n"
        f"Topology: **{topology}**  \n"
        f"Substrate: **{substrate or 'not decided'}**  \n"
        f"Provisioning: **{provisioner or 'not decided'}**\n\n"
        f"Neither of these is a default. The substrate is a ladder and this is "
        f"the rung the profile earned; the provisioner follows what the team "
        f"already operates, whether there is an API to call, and whether this "
        f"environment has to be destroyed cleanly.\n\n"
        f"The reasoning for each is in `ARCHITECTURE.md`, alongside what was "
        f"rejected and why.\n"
        + _install_section(substrate, provisioner)
    )


def _install_section(substrate: str | None, provisioner: str | None) -> str:
    """The install path, derived from the unit that demands it.

    A unit that wants /opt/app/.venv, user `app`, /var/lib/app and
    /etc/app/env, shipped beside nothing that creates any of them, is a
    deliverable the first operator cannot install. Every path below is the
    unit's own; change one there and it changes here.
    """
    if substrate != "systemd-unit":
        return ""
    if provisioner == "ansible-playbook":
        return (
            "\n## Install\n\n"
            "The playbook is the installer -- it creates everything the unit\n"
            "expects (service account, venv, state dir, env file):\n\n"
            "```bash\n"
            "# hosts go in deploy/ansible/inventory.ini first\n"
            "ansible-playbook -i deploy/ansible/inventory.ini deploy/ansible/site.yml\n"
            "```\n\n"
            "Then prove it from the host:\n\n"
            "```bash\n"
            "curl -s localhost:8080/health   # liveness: the process answers\n"
            "curl -s localhost:8080/ready    # readiness: dependencies answer\n"
            "journalctl -u app -n 20 --no-pager\n"
            "```\n"
        )
    return (
        "\n## Install\n\n"
        "Every step below exists because the unit file demands its result --\n"
        "the user, the interpreter path, the writable state dir, the env\n"
        "file. Run as root on the target host, from this project's root:\n\n"
        "```bash\n"
        "useradd --system --shell /usr/sbin/nologin --home /opt/app app   # the unit's User=\n"
        "REL=/opt/app/releases/$(date +%Y%m%d%H%M%S)   # releases side by side\n"
        "mkdir -p \"$REL\"\n"
        "# Stage the package, not the working tree: no tests, no CI, no .env.\n"
        "rsync -a --exclude .git --exclude .venv --exclude tests --exclude .github \\\n"
        "      --exclude '.*' app evals pyproject.toml \"$REL/\"\n"
        "# The documents to answer from (a build with a retrieval layer): the\n"
        "# unit's StateDirectory owns /var/lib/app; corpus/ lives under it.\n"
        "mkdir -p /var/lib/app/corpus && rsync -a corpus/ /var/lib/app/corpus/\n"
        "chown -R app /var/lib/app\n"
        "python3 -m venv \"$REL/.venv\"                  # ExecStart's interpreter\n"
        "\"$REL/.venv/bin/pip\" install \"$REL\"\n"
        "ln -sfn \"$REL\" /opt/app/current               # the unit runs `current`\n"
        "install -D -m 640 -o root -g app deploy/env.example /etc/app/env   # then EDIT it\n"
        "install -m 644 deploy/systemd/app.service /etc/systemd/system/app.service\n"
        "systemctl daemon-reload && systemctl enable --now app\n"
        "```\n\n"
        "Before `enable --now`, edit `/etc/app/env`: set AUTH_TOKEN (the\n"
        "service refuses every outward call without it), point the model\n"
        "endpoint at a host inside the network, and never set\n"
        "ANTHROPIC_API_KEY on a build whose data may not leave -- the boundary\n"
        "refuses to import with it set. The service binds loopback; exposing\n"
        "it means an authenticating, rate-limiting proxy in front, not BIND.\n\n"
        "Then prove it:\n\n"
        "```bash\n"
        "curl -s localhost:8080/health   # liveness: the process answers\n"
        "curl -s localhost:8080/ready    # readiness: dependencies answer\n"
        "journalctl -u app -n 20 --no-pager\n"
        "```\n"
    )


def _teardown(deploy: Path, substrate: str | None, provisioner: str | None) -> None:
    """Written whatever the tools -- both of them.

    The substrate and the provisioner each leave things behind, and a
    teardown that covers only one is how a demo's service unit outlives the
    engagement. An earlier version branched on provisioner *or* substrate:
    choosing Terraform -- the one tool that can destroy what it made --
    was exactly what suppressed the substrate's manual steps.
    """
    substrate_steps = {
        "systemd-unit": "sudo systemctl disable --now app\n"
                        "sudo rm /etc/systemd/system/app.service\n"
                        "sudo systemctl daemon-reload\n"
                        "sudo rm -rf /opt/app /var/lib/app\n"
                        "sudo userdel app\n",
        "compose": "cd deploy && docker compose down --volumes\n"
                   "docker image rm $(docker compose config --images)\n",
        "kubernetes-manifests": "kubectl delete -f deploy/manifests\n"
                                "# check for retained PersistentVolumes\n"
                                "kubectl get pv | grep app\n",
    }.get(substrate or "", "# nothing was deployed\n")

    sections = [
        "## The application\n\n"
        "The substrate has no concept of un-doing, so these are manual and "
        "written out rather than left implied.\n\n"
        f"```bash\n{substrate_steps}```\n"
    ]
    if provisioner == "terraform-module":
        sections.append(
            "## The environment\n\n"
            "```bash\ncd deploy/terraform\nterraform destroy\n```\n\n"
            "This tool tracks what it created, so this takes it away cleanly. "
            "Check that no state remains in a remote backend afterwards.\n"
        )
    else:
        sections.append(
            "## The environment\n\n"
            "This provisioner has no destroy. Whatever it configured -- users, "
            "packages, mounts -- is removed by hand, or by re-running the "
            "provisioning against a clean target.\n"
        )
    sections.append(
        "Then confirm nothing was left behind: data directories, secrets in "
        "a vault, DNS entries, and anything created by hand during the "
        "engagement.\n"
    )
    (deploy / "TEARDOWN.md").write_text("# Taking it away\n\n" + "\n".join(sections))


def _write_env_example(architecture, deploy: Path) -> None:
    """The environment, in one documented place, generated from what was
    actually emitted -- a mandatory variable that appears in no document
    is discovered by the first user instead of the deploy."""
    from fde.emit import _needs_model

    lines = [
        "# Copy to /etc/app/env (the unit reads it via EnvironmentFile).",
        "# Every variable the emitted service reads, with its default.",
        "",
        "PORT=8080",
        "# Loopback by default; exposing the port is a decision made here.",
        "BIND=127.0.0.1",
        "MAX_BODY_BYTES=1048576",
        "# Writable state (ledgers, queues). Must match ReadWritePaths in",
        "# the unit.",
        "STATE_DIR=/var/lib/app",
    ]
    if _needs_model(architecture):
        lines += [
            "",
            "# This build calls a model. A local OpenAI-compatible endpoint",
            "# (fde scan names one sized to the hardware):",
            "LLM_ENDPOINT=http://localhost:11434",
            "LLM_MODEL=set-me",
            "LLM_TIMEOUT=120",
            "LLM_MAX_TOKENS=512",
        ]
    else:
        lines += [
            "",
            "# This build does not call a model. The service's /ready preflight",
            "# reads these only in builds that do; here unset is correct.",
            "# LLM_ENDPOINT=",
            "# LLM_MODEL=",
        ]
    lines += [
        "",
        "# Identity at the edge. With AUTH_TOKEN set, POST / needs",
        "# `Authorization: Bearer <token>`, and every outward call is made",
        "# as SERVICE_SUBJECT holding GRANTED_SCOPES. Unset, the service is",
        "# anonymous and every tool call is refused -- fail closed.",
        "AUTH_TOKEN=",
        "SERVICE_SUBJECT=",
        "GRANTED_SCOPES=",
        "# Concurrent requests in flight; the rest get a 503 and retry.",
        "WORKERS=8",
        "# Exception text in the journal (never in a response). Off by",
        "# default: on a build with a data boundary, the text can carry data.",
        "LOG_DETAIL=0",
        "# Audit records carry argument KEYS and a digest by default; `full`",
        "# writes the values too (sensitive-looking keys redacted).",
        "AUDIT_ARGUMENTS=digest",
        "# A judged evaluation refuses to let the author grade itself unless",
        "# this is 1 -- and says so on every run when it is.",
        "ALLOW_SELF_JUDGE=0",
    ]
    if "retrieval" in architecture.decisions.decided():
        lines += [
            "",
            "# The documents to answer from, ingested at boot: .txt/.md files,",
            "# .json lists of {id, text}, .jsonl of the same. Empty = not ready.",
            "CORPUS_DIR=/var/lib/app/corpus",
            "# Megabytes of corpus TEXT the index may hold. The index costs about",
            "# twenty megabytes of memory per megabyte of text (measured); this",
            "# and MemoryMax in the unit are one decision. Over it, the boot",
            "# refuses with one line instead of dying to the OOM killer.",
            "CORPUS_MAX_MB=80",
        ]
    if architecture.graph.sensitive_nodes():
        lines += [
            "",
            "# Data may not leave. Every endpoint above must resolve to loopback,",
            "# a private range, or a host named here -- app/boundary.py refuses",
            "# to import otherwise. Comma-separated.",
            "BOUNDARY_ALLOWED_HOSTS=",
        ]
    evaluation = architecture.decisions.get("evaluation")
    if evaluation is not None and evaluation.approach == "judged":
        lines += [
            "",
            "# The judge should not be the author. Point these at a different",
            "# model (or endpoint) than the one the system answers with.",
            "JUDGE_ENDPOINT=",
            "JUDGE_MODEL=",
        ]
    else:
        lines += [
            "",
            "# Read by the evaluation harness only when the evaluation is judged;",
            "# this build's is not, so these stay unset.",
            "# JUDGE_ENDPOINT=",
            "# JUDGE_MODEL=",
        ]
    memory = architecture.realizations.get("memory")
    if memory is not None and memory.stack == "supermemory":
        lines += [
            "",
            "# This build keeps memory in the supermemory engine. The local",
            "# binary's default; the hosted host is refused behind a boundary.",
            "SUPERMEMORY_ENDPOINT=http://localhost:6767",
            "# Printed by the binary on first boot (sm_...).",
            "SUPERMEMORY_API_KEY=",
            "SUPERMEMORY_TIMEOUT=10",
        ]
    (deploy / "env.example").write_text("\n".join(lines) + "\n")


def _approach(architecture, component: str) -> str | None:
    decision = architecture.decisions.get(component)
    return decision.approach if decision else None
