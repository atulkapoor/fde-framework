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

    substrate = _approach(architecture, "deployment")
    provisioner = _approach(architecture, "provisioning")
    air_gapped = architecture.topology == "air-gapped"

    if substrate == "systemd-unit":
        _systemd(deploy)
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


def _systemd(deploy: Path) -> None:
    (deploy / "systemd").mkdir(exist_ok=True)
    (deploy / "systemd" / "app.service").write_text(
        "# Rung zero, and frequently the right answer rather than the lesser one.\n"
        "# Understood by anyone who has administered a Linux box, restarts on\n"
        "# failure, starts on boot, and adds nothing anybody has to learn.\n"
        "[Unit]\n"
        "Description=Generated application\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        "User=app\n"
        "WorkingDirectory=/opt/app\n"
        "ExecStart=/opt/app/.venv/bin/python -m app.pipeline\n"
        "Restart=on-failure\n"
        "RestartSec=5\n"
        "# Least privilege costs nothing here and is awkward to add later.\n"
        "NoNewPrivileges=true\n"
        "PrivateTmp=true\n"
        "ProtectSystem=strict\n"
        "ReadWritePaths=/var/lib/app\n\n"
        "[Install]\n"
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
        "  tasks:\n"
        "    - name: Create the service account\n"
        "      ansible.builtin.user:\n"
        "        name: app\n"
        "        system: true\n"
        "    - name: Install the application\n"
        "      ansible.builtin.copy:\n"
        "        src: ../../app\n"
        "        dest: /opt/app/\n"
        "        owner: app\n"
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


def _approach(architecture, component: str) -> str | None:
    decision = architecture.decisions.get(component)
    return decision.approach if decision else None
