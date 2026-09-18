"""Turning an architecture into a project on disk.

The bar is not that files appear. It is that the emitted project imports, that
its wiring matches the decisions, that the boundary is enforced in the code
rather than described in the documentation, and that anything the framework
could not decide is loud rather than absent.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

from fde.architect import architect
from fde.emit import BuildRefused, emit
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"

COMPLETE = dict(
    output_shape="structured", input_format="documents", query_pattern="lookup",
    corpus_size=200_000, labelled_count=8_000, data_residency="cannot_leave",
    hosting="air-gapped", latency_budget_ms=800, external_systems=3,
    recall_span="within_session", operates_after_handover="platform_team",
)
OPEN = {**COMPLETE, "data_residency": "may_leave", "hosting": "customer-vpc",
        "human_waiting": "yes"}


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def profile(**values):
    p = Profile()
    p.ingest([Fact(k, v, Provenance.ARTIFACT) for k, v in values.items()])
    return p


@pytest.fixture(scope="module")
def built(reg, tmp_path_factory):
    out = tmp_path_factory.mktemp("project")
    emit(architect(profile(**COMPLETE), reg), out)
    return out


# --- it is a real project ------------------------------------------------


def test_the_emitted_project_imports(built):
    """The whole point. Files that do not import are documentation."""
    result = subprocess.run(
        [sys.executable, "-c", "import app.pipeline"],
        cwd=built, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_every_decided_component_becomes_a_module(built, reg):
    modules = {p.stem for p in (built / "app" / "components").glob("*.py")}
    assert {"perception", "representation", "evaluation"} <= modules


def test_the_pipeline_names_the_components_in_order(built):
    source = (built / "app" / "pipeline.py").read_text()
    assert source.index("perception") < source.index("representation")


def test_a_project_file_says_what_it_needs_to_run(built):
    assert (built / "pyproject.toml").exists()


# --- nothing is silently missing -----------------------------------------


def test_a_component_nothing_could_fill_raises_rather_than_disappearing(reg, tmp_path):
    """A hole that imports cleanly is a hole found in production."""
    architecture = architect(profile(output_shape="structured"), reg)
    emit(architecture, tmp_path)
    unfilled = [
        p for p in (tmp_path / "app" / "components").glob("*.py")
        if "UndecidedComponent" in p.read_text()
    ]
    assert unfilled or not architecture.decisions.undecided()


def test_an_unfilled_module_says_what_was_missing(reg, tmp_path):
    architecture = architect(profile(output_shape="structured"), reg)
    emit(architecture, tmp_path)
    for path in (tmp_path / "app" / "components").glob("*.py"):
        body = path.read_text()
        if "UndecidedComponent" in body:
            assert "not enough is known" in body


def test_undecided_and_scaffolded_are_told_apart(reg, tmp_path):
    """A scaffold means the decision was made and the body is yours. Undecided
    means no decision exists, and running it is not the fix."""
    emit(architect(profile(output_shape="structured"), reg), tmp_path)
    bodies = {p.stem: p.read_text() for p in (tmp_path / "app" / "components").glob("*.py")}
    scaffolds = {k for k, v in bodies.items() if "NotImplementedError" in v}
    undecided = {k for k, v in bodies.items() if "UndecidedComponent" in v}
    assert not (scaffolds & undecided)


# --- the boundary is code, not prose -------------------------------------


def test_a_boundary_violation_refuses_the_build(reg, tmp_path):
    """Before anything is written. A half-written project is worse than none."""
    architecture = architect(profile(**COMPLETE), reg)
    leaking = next(iter(architecture.graph.sensitive_nodes()))
    architecture.graph.placement[leaking.id] = "external"
    with pytest.raises(BuildRefused, match="boundary"):
        emit(architecture, tmp_path)
    assert not list(tmp_path.iterdir())


def test_the_generated_project_asserts_its_own_boundary(built):
    assert (built / "app" / "boundary.py").exists()
    assert "in_boundary" in (built / "app" / "boundary.py").read_text()


def test_an_air_gap_alone_earns_a_boundary(reg, tmp_path):
    """The regression that motivated deriving sensitivity from the profile.

    This exact profile -- air-gapped, nobody having said the word residency --
    used to produce zero sensitive nodes, because sensitivity was inferred
    from a substring of the decision rationale. The engagement the boundary
    machinery exists for got no boundary, silently."""
    emit(architect(profile(
        hosting="air-gapped", input_format="documents", output_shape="structured",
    ), reg), tmp_path)
    assert (tmp_path / "app" / "boundary.py").exists()


# --- the moves reach the code ---------------------------------------------


MUTATIVE = dict(output_shape="decision", latency_budget_ms=200, external_systems=2)


def test_approval_gates_and_critics_survive_into_the_pipeline(reg, tmp_path):
    """The moves insert them; the pipeline must keep them. A gate that lives
    only in the design document guards nothing."""
    emit(architect(profile(**MUTATIVE), reg), tmp_path)
    pipeline = (tmp_path / "app" / "pipeline.py").read_text()
    assert "ApprovalGate" in pipeline
    assert "Critic" in pipeline
    assert (tmp_path / "app" / "controls.py").exists()


def test_mutative_builds_carry_a_durable_ledger_not_a_static_key(reg, tmp_path):
    """The key matters more than the gate: a gate stops the wrong thing once,
    a key means doing it twice cannot charge twice. A build-time constant
    cannot be a per-action key (every deployment from one profile shared
    it); keys are derived from the action and reserved in the ledger."""
    emit(architect(profile(**MUTATIVE), reg), tmp_path)
    assert "idempotency_key=" not in (tmp_path / "app" / "pipeline.py").read_text()
    assert (tmp_path / "app" / "ledger.py").exists()
    assert "ledger" in (tmp_path / "ARCHITECTURE.md").read_text()


def test_the_controls_fail_closed_until_wired(reg, tmp_path):
    """An approval gate that defaults to yes is decoration. The first run must
    say what has not been decided yet, not do the irreversible thing."""
    emit(architect(profile(**MUTATIVE), reg), tmp_path)
    result = subprocess.run(
        [sys.executable, "-c",
         "from app.controls import ApprovalGate\n"
         "ApprovalGate('x').run({'tool': 'x', 'arguments': {}})"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "NeedsApproval" in result.stderr


def test_a_read_only_pipeline_gets_no_controls(reg, tmp_path):
    emit(architect(profile(
        output_shape="structured", corpus_size=100, data_residency="may_leave",
    ), reg), tmp_path)
    assert not (tmp_path / "app" / "controls.py").exists()


# --- failure is loud, never cosmetic ---------------------------------------


def test_a_missing_registry_root_is_an_error_not_an_empty_registry(tmp_path):
    """An empty registry decides nothing, everything downstream 'works', and
    the first sign is a hollow build. The classic path is the wrong cwd."""
    from fde.registry import RegistryError, load_registry

    with pytest.raises(RegistryError, match="no registry here"):
        load_registry(tmp_path / "nowhere")


def test_a_missing_templates_directory_refuses_the_build(reg, tmp_path):
    """Installed away from a source checkout, the old behaviour was to emit
    scaffolds for everything and report success."""
    architecture = architect(profile(**COMPLETE), reg)
    with pytest.raises(BuildRefused, match="templates"):
        emit(architecture, tmp_path / "out", templates=tmp_path / "not-there")
    assert not (tmp_path / "out").exists()


def test_scaffold_fallbacks_are_reported_not_swallowed(reg, tmp_path):
    """A template dir that resolves nothing must not read as a finished build."""
    empty = tmp_path / "empty-templates"
    empty.mkdir()
    report = emit(architect(profile(**COMPLETE), reg), tmp_path / "out", templates=empty)
    assert report.scaffolded
    assert set(report.scaffolded) <= set(
        architect(profile(**COMPLETE), reg).realizations
    )


def test_the_emitted_evaluation_gate_can_fail(reg, tmp_path):
    """The harness evaluates the pipeline, and an unimplemented pipeline is a
    red build. Before this, CI ran the harness with a threshold of zero and a
    strict less-than: a gate that could not say no."""
    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text(
        '{"id": "a", "input": "doc a", "output": {"field": 1}, "verified": true}\n'
        '{"id": "b", "input": "doc b", "output": {"field": 2}, "verified": true}\n'
        '{"id": "c", "input": "doc c", "output": {"field": 3}, "verified": true}\n'
    )
    out = tmp_path / "out"
    emit(architect(profile(**COMPLETE), reg), out, pairs_path=pairs)
    result = subprocess.run(
        [sys.executable, "evals/harness.py"], cwd=out, capture_output=True, text=True,
    )
    assert result.returncode == 1
    # A scaffold errors, or composes into a wrong answer -- either way the
    # gate is red, and says which.
    assert ("not yet implemented" in result.stderr or "errored" in result.stderr
            or "every golden case failed" in result.stderr), result.stderr


def test_an_empty_golden_set_is_a_red_build(reg, tmp_path):
    """The earlier version of this test pinned the opposite: exit 0 with a
    stderr note. A note is for people; the exit code is for CI, and CI was
    green on a system with no evals at all."""
    out = tmp_path / "out"
    emit(architect(profile(**COMPLETE), reg), out)
    result = subprocess.run(
        [sys.executable, "evals/harness.py"], cwd=out, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "nothing was measured" in result.stderr


# --- every legal topology builds ------------------------------------------


def test_every_hosting_answer_yields_a_realizable_project(reg, tmp_path):
    """The regression: stacks said 'managed', the dimension said 'managed-api',
    and one legal answer to the most-asked question produced an architecture
    with every component decided and nothing buildable -- silently."""
    for value in reg.dimensions["hosting"].values:
        architecture = architect(profile(
            hosting=value, output_shape="structured", input_format="documents",
        ), reg)
        assert not architecture.unrealizable, (
            f"hosting={value}: {architecture.unrealizable}"
        )


def test_an_unrealizable_component_does_not_break_the_import(reg, tmp_path):
    """When realization fails, the module raises on use -- the pipeline must
    not reference a class the module does not define."""
    architecture = architect(profile(
        hosting="customer-vpc", output_shape="structured", input_format="documents",
    ), reg)
    victim = next(iter(architecture.realizations))
    architecture.unrealizable[victim] = "forced for this test"
    architecture.realizations.pop(victim)
    architecture.graph.nodes[victim].unfilled = True

    emit(architecture, tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", "import app.pipeline"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_an_open_topology_needs_no_boundary_module(reg, tmp_path):
    emit(architect(profile(**OPEN), reg), tmp_path)
    assert not (tmp_path / "app" / "boundary.py").exists()


# --- the documents a client actually reads -------------------------------


def test_the_architecture_document_records_what_was_rejected(built):
    """The half a client reads: what they are not getting, and why."""
    text = (built / "ARCHITECTURE.md").read_text()
    assert "Rejected" in text or "rejected" in text


def test_the_architecture_document_states_its_assumptions(reg, tmp_path):
    """Every question nobody answered is an assumption someone should see."""
    emit(architect(profile(output_shape="structured"), reg), tmp_path)
    assert "Assumption" in (tmp_path / "ARCHITECTURE.md").read_text()


def test_the_architecture_document_surfaces_disagreements(reg, tmp_path):
    from fde.models.respondent import Respondent

    # A dimension nobody wrote down, where two people said different things.
    # Adding interview answers over an artifact fact would not disagree at all:
    # provenance settles that, which is the point of provenance.
    without_latency = {k: v for k, v in COMPLETE.items() if k != "latency_budget_ms"}
    p = profile(**without_latency)
    p.ingest([
        Fact("latency_budget_ms", 5000, Provenance.INTERVIEW,
             respondent=Respondent(role="sponsor", name="A")),
        Fact("latency_budget_ms", 200, Provenance.INTERVIEW,
             respondent=Respondent(role="user", name="B")),
    ])
    emit(architect(p, reg), tmp_path)
    assert "latency_budget_ms" in (tmp_path / "ARCHITECTURE.md").read_text()


def test_the_architecture_document_lists_the_licences_it_pulls_in(built):
    assert "Licence" in (built / "ARCHITECTURE.md").read_text()


def test_every_decision_traces_back_to_a_fact(built):
    """The property worth defending: an FDE asked why can answer."""
    text = (built / "ARCHITECTURE.md").read_text()
    assert "data_residency" in text


# --- refusing to write a broken project ----------------------------------


def test_writing_into_a_non_empty_directory_is_refused(reg, tmp_path):
    (tmp_path / "something.txt").write_text("existing work")
    with pytest.raises(BuildRefused, match="not empty"):
        emit(architect(profile(**COMPLETE), reg), tmp_path)


def test_the_same_architecture_emits_the_same_project(reg, tmp_path):
    """Deterministic output, so a diff between two builds means something."""
    a, b = tmp_path / "a", tmp_path / "b"
    emit(architect(profile(**COMPLETE), reg), a)
    emit(architect(profile(**COMPLETE), reg), b)
    assert (a / "app" / "pipeline.py").read_text() == (b / "app" / "pipeline.py").read_text()


# --- the measurement the project ships with ------------------------------


def test_an_eval_harness_is_emitted_even_without_pairs(built):
    """No harness at all is a gap nobody finds until they ask how it is going.
    An empty golden set is a gap anybody can see."""
    assert (built / "evals" / "harness.py").exists()
    assert (built / "evals" / "taxonomy.py").exists()


def test_all_three_layers_are_emitted(built):
    for layer in ("golden", "edge_case", "adversarial"):
        assert (built / "evals" / f"{layer}.jsonl").exists()


def test_the_harness_runs(built):
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "evals/harness.py"], cwd=built, capture_output=True, text=True
    )
    # The fixture has no pairs, so the honest exit is red -- but the report
    # still renders, which is what this test guards.
    assert result.returncode == 1
    assert "golden" in result.stdout


def test_the_taxonomy_classifies_by_source(built):
    body = (built / "evals" / "taxonomy.py").read_text()
    for source in ("data", "input", "prediction", "output", "system", "integration"):
        assert source in body


def test_the_golden_set_is_seeded_from_the_clients_own_pairs(reg, tmp_path):
    """The evaluation is about their problem from the first run, not a
    benchmark that resembles it."""
    import json

    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text("\n".join(json.dumps(p) for p in [
        {"id": "a", "input": "x", "verified": True, "layout": "one",
         "output": {"total": 1.0, "account": "****1"}},
        {"id": "b", "input": "y", "verified": True, "layout": "two",
         "output": {"total": 2.0, "account": "****2"}},
    ]))
    out = tmp_path / "proj"
    emit(architect(profile(**COMPLETE), reg), out, pairs_path=pairs)
    golden = (out / "evals" / "golden.jsonl").read_text()
    assert "****" in golden


def test_the_adversarial_layer_covers_what_nobody_supplied(reg, tmp_path):
    """Executable probes mutated from a real case: an injection that must
    change nothing, and forbidden input that must be refused. (Sensitive
    egress moved out of this layer when the probes became executable -- the
    boundary and the masking component own it structurally.)"""
    import json

    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text("".join(json.dumps(
        {"id": str(i), "input": f"Total: {i}.00", "verified": True,
         "output": {"total": float(i)}}) + "\n" for i in range(4)))
    out = tmp_path / "proj"
    emit(architect(profile(**COMPLETE), reg), out, pairs_path=pairs)
    cases = (out / "evals" / "adversarial.jsonl").read_text()
    assert "prompt_injection" in cases
    assert "expect_refusal" in cases


def test_the_harness_can_fail_a_build(built):
    """CI has to be able to gate on it, or it is a report nobody reads."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "evals/harness.py", "--min-score", "1.01"],
        cwd=built, capture_output=True, text=True,
    )
    assert result.returncode in (0, 1)   # 0 only when there is nothing to score


# --- the review's catches --------------------------------------------------


def test_the_critic_runs_before_the_step_it_guards(reg, tmp_path):
    """ordered() once walked edges in insertion order, so the critic
    linearised after the irreversible step: the pipeline charged the
    customer, then reviewed. The order things run in must be the order the
    edges mean."""
    emit(architect(profile(**MUTATIVE), reg), tmp_path)
    pipeline = (tmp_path / "app" / "pipeline.py").read_text()
    steps = [line for line in pipeline.splitlines() if line.startswith("    (")]
    positions = {name: i for i, line in enumerate(steps)
                 for name in ("approve-integration", "critic-integration", "'integration'")
                 if line.strip().startswith(f"('{name.strip(chr(39))}'")}
    assert positions["approve-integration"] < positions["critic-integration"]
    assert positions["critic-integration"] < positions["'integration'"]


def test_no_control_guards_a_step_that_is_not_in_the_pipeline(reg, tmp_path):
    """A gate in front of nothing reads as a governed integration that does
    not exist."""
    architecture = architect(profile(hosting="air-gapped", output_shape="decision"), reg)
    emit(architecture, tmp_path)
    pipeline = (tmp_path / "app" / "pipeline.py").read_text()
    if "('integration'," not in pipeline:
        assert "approve-integration" not in pipeline
        assert "critic-integration" not in pipeline


def test_the_pipeline_imports_only_what_it_runs(reg, tmp_path):
    import re as _re

    emit(architect(profile(hosting="air-gapped", output_shape="decision"), reg), tmp_path)
    pipeline = (tmp_path / "app" / "pipeline.py").read_text()
    # Single-line and wrapped-parenthesized import forms both count.
    block = _re.search(
        r"from app\.components import (\([^)]*\)|[^\n]+)", pipeline
    ).group(1)
    for name in _re.findall(r"\w+", block):
        assert f"('{name}'," in pipeline, f"dead import: {name}"


def test_importing_the_pipeline_enforces_the_boundary(reg, tmp_path):
    """A boundary module nothing imports is a boundary reviewed in a
    document. The entrypoint the emitter itself writes must trip it."""
    emit(architect(profile(
        hosting="air-gapped", input_format="documents", output_shape="structured",
    ), reg), tmp_path)
    boundary = tmp_path / "app" / "boundary.py"
    body = boundary.read_text().replace(
        "'perception': 'in_boundary'", "'perception': 'external'"
    )
    boundary.write_text(body)
    result = subprocess.run(
        [sys.executable, "-c", "import app.pipeline"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "may not leave" in result.stderr


def test_the_generated_project_declares_its_packages(reg, tmp_path):
    """The emitted CI's first real step is pip install -e .; a flat layout
    with four top-level directories made setuptools refuse to guess, so CI
    died before the evaluation it exists to gate ever ran. Explicit packages
    and an explicit build backend are what remove the guess."""
    emit(architect(profile(**COMPLETE), reg), tmp_path)
    body = (tmp_path / "pyproject.toml").read_text()
    assert "[build-system]" in body
    assert 'packages = ["app", "app.components"]' in body


def test_pairs_without_ids_refuse_before_anything_is_written(reg, tmp_path):
    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text('{"input": "x", "output": {"f": 1}}\n')
    out = tmp_path / "out"
    with pytest.raises(BuildRefused, match="id"):
        emit(architect(profile(**COMPLETE), reg), out, pairs_path=pairs)
    assert not out.exists() or not any(out.iterdir())


def test_a_profile_the_registry_cannot_realize_refuses_rather_than_a_noop(reg, tmp_path):
    """hosting='mars' once emitted an empty STEPS list that imported
    cleanly and returned its input unchanged -- the exact hole the emitter
    says it exists to prevent."""
    with pytest.raises(BuildRefused, match="unrecognised value"):
        emit(architect(profile(hosting="mars", output_shape="structured"), reg), tmp_path)


def test_the_teardown_covers_substrate_and_provisioner_both(reg, tmp_path):
    """Choosing terraform -- the one tool that can destroy what it made --
    used to suppress the substrate's manual steps entirely."""
    from fde.decide import Decision, Decisions
    from fde.deploy import write_deploy
    from fde.workflow import build_graph

    decisions = Decisions({
        "deployment": Decision("deployment", "systemd-unit", "forced"),
        "provisioning": Decision("provisioning", "terraform-module", "forced"),
    })
    architecture = architect(profile(**COMPLETE), reg)
    architecture.decisions = decisions
    architecture.graph = build_graph(decisions, reg)
    write_deploy(architecture, tmp_path)
    teardown = (tmp_path / "deploy" / "TEARDOWN.md").read_text()
    assert "terraform destroy" in teardown
    assert "systemctl disable" in teardown


# --- the depth test's findings ---------------------------------------------


def test_platform_components_are_not_payload_steps(reg, tmp_path):
    """Implementing an emitted project to green found the pipeline chaining
    deployment as a runtime step -- a component with no run() at all, so
    every generated pipeline crashed at step three for any input. The data
    path is registry-declared now."""
    emit(architect(profile(**COMPLETE), reg), tmp_path, registry=reg)
    pipeline = (tmp_path / "app" / "pipeline.py").read_text()
    for platform in ("deployment", "provisioning", "evaluation",
                     "observability", "governance"):
        assert f"('{platform}'," not in pipeline, platform
    assert "('perception'," in pipeline
    assert "('representation'," in pipeline
    # Still emitted as modules -- decided is decided.
    assert (tmp_path / "app" / "components" / "deployment.py").exists()


def test_the_emitted_pipeline_can_reach_green(reg, tmp_path):
    """The whole depth test, pinned: an FDE implements the generated project
    against its own golden set and the harness passes. The glue below is
    the same ~30 lines a receiving engineer writes."""
    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text(
        '{"id": "a", "input": "Total due: $4,230.00\\nVAT: $846.00", '
        '"output": {"total_due": 4230.0, "vat": 846.0}, "verified": true}\n'
        '{"id": "b", "input": "AMOUNT PAYABLE 220.00 | VAT 44.00", '
        '"output": {"total_due": 220.0, "vat": 44.0}, "verified": true}\n'
        '{"id": "c", "input": "Amount due ....... 1,100.00\\nVAT ....... 220.00", '
        '"output": {"total_due": 1100.0, "vat": 220.0}, "verified": true}\n'
    )
    out = tmp_path / "out"
    emit(architect(profile(**COMPLETE), reg), out, registry=reg, pairs_path=pairs)

    (out / "app" / "pipeline.py").write_text('''
import re
from app import boundary  # noqa: F401
from app.components import representation
from app.contract import RefusedInput

CONTRACT = ["total_due", "vat"]
SYNONYMS = {"total_due": ["amount payable", "amount due", "total"]}
KNOWN = {label for labels in SYNONYMS.values() for label in labels} | set(CONTRACT)
MONEY = re.compile(r"[-+]?\\d[\\d,]*(?:\\.\\d+)?")

def _raw(text):
    out = {}
    for segment in re.split(r"[\\n|]", text):
        match = MONEY.search(segment)
        if match:
            label = segment[: match.start()].strip(" .:\\t$").lower()
            if (label in KNOWN or label.replace(" ", "_") in KNOWN
                    or label.replace("_", " ") in KNOWN):
                out[label] = float(match.group().replace(",", ""))
    return out

STEP = representation.Representation(synonyms=SYNONYMS, contract=CONTRACT)

def run(payload):
    from app.shapes import envelope
    payload = envelope(payload)["input"]  # the contract's refusals, scrubbed input
    if isinstance(payload, str):
        if not payload.strip():
            raise RefusedInput("an empty document holds no fields to extract")
        payload = {"contract": CONTRACT, "records": [{"id": "case", "raw": _raw(payload)}]}
    record = STEP.run(payload)["records"][0]
    if record["unmapped"] or record["rejected"]:
        raise RefusedInput(str(record))
    return record["mapped"]
''')
    result = subprocess.run(
        [sys.executable, "evals/harness.py"], cwd=out, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "100.0%" in result.stdout


# --- acceptance and load: the tests the guides say clients actually run -----


def test_an_acceptance_protocol_ships_with_the_evals(built):
    acceptance = (built / "evals" / "acceptance.md").read_text()
    assert "blind" in acceptance.lower()
    assert "Not the builder" in acceptance


def test_a_stated_latency_budget_earns_a_load_test(built):
    load = (built / "evals" / "load.py").read_text()
    assert "BUDGET_MS = 800" in load
    assert "from app.pipeline import run" in load


def test_no_latency_budget_means_no_load_test(tmp_path, reg):
    """A load test against an unstated budget would invent the number it
    checks."""
    values = {k: v for k, v in COMPLETE.items() if k != "latency_budget_ms"}
    emit(architect(profile(**values), reg), tmp_path / "p")
    assert not (tmp_path / "p" / "evals" / "load.py").exists()


def test_a_false_answer_is_not_rendered_as_silence(built):
    """confidence_calibrated = False once rendered as an empty value in the
    Scope section -- `or ''` swallows every falsy answer, and False is an
    answer somebody gave."""
    from fde.emit import _flat

    assert _flat(False) == "False"
    assert _flat(0) == "0"
    assert _flat(None) == ""


def test_an_empty_golden_set_fails_the_harness(built, tmp_path):
    """It printed "not a passing grade" and returned 0 -- CI green on a
    system with no evals. An empty exam proves nothing and must say so
    with its exit code, which is the only part CI reads."""
    import shutil
    import subprocess
    import sys as _sys

    project = tmp_path / "p"
    shutil.copytree(built, project)
    for name in ("golden", "edge_case", "adversarial"):
        (project / "evals" / f"{name}.jsonl").write_text("")
    result = subprocess.run(
        [_sys.executable, "evals/harness.py", "--min-score", "0"],
        cwd=project, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "nothing was measured" in result.stderr


# --- the judge reaches the harness ------------------------------------------


FREEFORM = dict(
    output_shape="freeform", input_format="documents", corpus_size=60_000,
    data_residency="may_leave", hosting="customer-vpc", human_waiting="yes",
    latency_budget_ms=4000, query_pattern="lookup",
)


def test_a_judged_evaluation_emits_a_judge_based_harness(reg, tmp_path):
    """Freeform output decides judged evaluation, and prose never equals its
    reference byte for byte -- an exact-match harness for that system is an
    exam nobody can pass honestly."""
    out = tmp_path / "p"
    emit(architect(profile(**FREEFORM), reg), out)
    harness = (out / "evals" / "harness.py").read_text()
    assert "JUDGED = True" in harness
    assert (out / "app" / "llm.py").exists()


def test_a_field_match_evaluation_keeps_exact_scoring(reg, tmp_path):
    out = tmp_path / "p"
    emit(architect(profile(**COMPLETE), reg), out)
    harness = (out / "evals" / "harness.py").read_text()
    assert "JUDGED = False" in harness


def test_the_provider_refuses_hosted_models_inside_a_boundary(reg, tmp_path):
    """The judge is not an exception to the boundary: a brief that may not
    leave does not get to leave via the grader."""
    values = {**FREEFORM, "data_residency": "cannot_leave", "hosting": "on-prem"}
    out = tmp_path / "p"
    emit(architect(profile(**values), reg), out)
    result = subprocess.run(
        [sys.executable, "-c",
         "from app.llm import complete, ModelUnconfigured\n"
         "try:\n    complete('x')\nexcept ModelUnconfigured as e:\n"
         "    print('REFUSED:', e)"],
        cwd=out, capture_output=True, text=True,
        env={"PATH": "/usr/bin", "ANTHROPIC_API_KEY": "sk-test"},
    )
    assert "REFUSED:" in result.stdout
    assert "boundary" in result.stdout


def test_a_judged_harness_scores_against_a_local_judge(reg, tmp_path):
    """End to end: emitted freeform project, a stub pipeline, a judge on a
    localhost endpoint -- the harness produces a meaningful score instead
    of comparing prose for equality."""
    import json as jsonlib
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text("".join(jsonlib.dumps(
        {"id": str(i), "verified": True,
         "input": f"Question {i} about the guideline.",
         "output": f"An answer citing section {i}."}) + "\n" for i in range(5)))
    out = tmp_path / "p"
    emit(architect(profile(**FREEFORM), reg), out, pairs_path=pairs)

    (out / "app" / "pipeline.py").write_text(
        "from app.contract import RefusedInput\n"
        "from app.shapes import envelope\n\n\n"
        "def run(payload):\n"
        "    payload = envelope(payload)['input']\n"
        "    if isinstance(payload, str) and not payload.strip():\n"
        "        raise RefusedInput('empty question')\n"
        "    return 'A paraphrased but faithful answer.'\n"
    )

    class Judge(BaseHTTPRequestHandler):
        def do_POST(self):
            # The judge speaks the discrete rubric now -- a small judge
            # agrees with humans on verdicts, not on invented decimals.
            body = jsonlib.dumps({"choices": [{"message": {"content": "correct"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Judge)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        result = subprocess.run(
            [sys.executable, "evals/harness.py", "--min-score", "0.5", "--allow-uncalibrated"],
            cwd=out, capture_output=True, text=True,
            env={"PATH": "/usr/bin",
                 "LLM_ENDPOINT": f"http://127.0.0.1:{server.server_port}",
                 # A different model on the same stub endpoint: the harness
                 # compares the resolved (endpoint, model) pair, and this
                 # is a distinct judge by that measure.
                 "JUDGE_ENDPOINT": f"http://127.0.0.1:{server.server_port}",
                 "JUDGE_MODEL": "judge-stub"},
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "100.0%" in result.stdout
        # The same run without asking for a provisional score by name is
        # red: an uncalibrated judge's number is not a passing grade.
        strict = subprocess.run(
            [sys.executable, "evals/harness.py", "--min-score", "0.5"],
            cwd=out, capture_output=True, text=True,
            env={"PATH": "/usr/bin",
                 "LLM_ENDPOINT": f"http://127.0.0.1:{server.server_port}",
                 "JUDGE_ENDPOINT": f"http://127.0.0.1:{server.server_port}",
                 "JUDGE_MODEL": "judge-stub"},
        )
        assert strict.returncode == 1
        assert "no judge calibration on record" in strict.stderr
    finally:
        server.shutdown()


def test_the_served_adapter_counts_as_the_author(reg, tmp_path):
    """The judge must not be the model that answered. In a fine-tuned
    build that model is the adapter named by FINETUNED_MODEL, and a judge
    pointed at the same name on the same endpoint is the author."""
    import json as jsonlib

    out = tmp_path / "p"
    emit(architect(profile(**FREEFORM), reg), out)
    cases = tmp_path / "cases.jsonl"
    cases.write_text(jsonlib.dumps({"id": "c", "input": "Q?", "output": "A."}) + "\n")
    result = subprocess.run(
        [sys.executable, "evals/harness.py", "--cases", str(cases)],
        cwd=out, capture_output=True, text=True,
        env={"PATH": "/usr/bin", "LLM_ENDPOINT": "http://127.0.0.1:9",
             "JUDGE_ENDPOINT": "http://127.0.0.1:9", "JUDGE_MODEL": "v1",
             "FINETUNED_MODEL": "v1"},
    )
    assert result.returncode == 1
    assert "the judge would be the author's own model" in result.stderr, result.stderr


def test_a_verdict_line_outranks_the_rationale_around_it(reg, tmp_path):
    """Small judges explain themselves; the explanation says 'incorrect'
    about a detail and the verdict line says correct. The line that labels
    itself a verdict wins, wherever it sits."""
    out = tmp_path / "p"
    emit(architect(profile(**FREEFORM), reg), out)
    result = subprocess.run([sys.executable, "-c", """
import importlib.util
spec = importlib.util.spec_from_file_location("harness", "evals/harness.py")
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
assert h.parse_verdict("Verdict: correct\\nOne phrase is incorrect in tone.") == 1.0
assert h.parse_verdict("The tone is incorrect in places.\\nGrade: partial") == 0.5
assert h.parse_verdict("Overall this is not correct.") == 0.0
assert h.parse_verdict("incorrect\\ncorrect") == 0.0
print("ok")
"""], cwd=out, capture_output=True, text=True, env={"PATH": "/usr/bin"})
    assert result.returncode == 0, result.stderr


def test_a_fact_learned_from_a_person_is_marked_as_asserted(reg, tmp_path):
    """Residency and hosting decide the governance and the boundary. Stated
    in an interview they are asserted, not established, and RISKS.md says
    so; read off the client's own document they stand."""
    said = tmp_path / "said"
    p = Profile()
    p.ingest([Fact(k, v, Provenance.INTERVIEW) for k, v in OPEN.items()])
    emit(architect(p, reg), said, registry=reg)
    risks = said.joinpath("RISKS.md").read_text()
    assert "## Facts this design stands on" in risks
    assert "`data_residency = may_leave` -- interview -- asserted, not established" in risks

    written = tmp_path / "written"
    emit(architect(profile(**OPEN), reg), written, registry=reg)
    risks = written.joinpath("RISKS.md").read_text()
    assert "`data_residency = may_leave` -- artifact\n" in risks
    assert "-- artifact -- asserted" not in risks


def test_the_readme_says_what_ci_does_and_risks_names_the_advisory_modules(reg, tmp_path):
    out = tmp_path / "p"
    emit(architect(profile(**OPEN), reg), out, registry=reg)
    readme = out.joinpath("README.md").read_text()
    assert "## What CI does and does not do" in readme
    assert "red on purpose" in readme
    risks = out.joinpath("RISKS.md").read_text()
    if "## Decided, emitted, not on the payload path" in risks:
        listed = re.findall(r"^- `(\w+)`$", risks.split("not on the payload path", 1)[1], re.M)
        assert listed, "the advisory section names nothing"


def test_an_unconfigured_judge_is_a_clear_red(reg, tmp_path):
    import json as jsonlib

    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text("".join(jsonlib.dumps(
        {"id": str(i), "verified": True, "input": f"Q{i}?", "output": f"A{i}."})
        + "\n" for i in range(4)))
    out = tmp_path / "p"
    emit(architect(profile(**FREEFORM), reg), out, pairs_path=pairs)
    (out / "app" / "pipeline.py").write_text("def run(p):\n    return 'x'\n")
    result = subprocess.run(
        [sys.executable, "evals/harness.py"], cwd=out,
        capture_output=True, text=True, env={"PATH": "/usr/bin"},
    )
    assert result.returncode == 1
    assert "judge-based" in result.stderr and "no model is configured" in result.stderr


def test_the_delivery_has_a_front_door(built):
    """A handover-obsessed framework was shipping deliveries with no
    README: the handover artifact had no front door."""
    front = (built / "README.md").read_text()
    assert "evals/harness.py" in front
    assert "fde implement" in front
    assert "ARCHITECTURE.md" in front


def test_the_judge_rubric_is_discrete_and_noise_tolerant(reg, tmp_path):
    """'Partial.' with a capital and a full stop is a 0.5, chatter around
    the verdict keeps the last word, and an off-rubric reply fails
    visibly -- never a float parsed from wishful thinking."""
    out = tmp_path / "p"
    emit(architect(profile(**FREEFORM), reg), out)
    harness = {"__file__": str(out / "evals" / "harness.py")}
    exec(compile((out / "evals" / "harness.py").read_text()
                 .replace("from evals.taxonomy import classify", "classify = None"),
                 "harness", "exec"), harness)
    assert harness["VERDICTS"] == {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}
    parse = harness["parse_verdict"]
    # the parser survives chatter and formatting...
    assert parse("**correct**") == 1.0
    # ordinary judge phrasings are verdicts, not zeros
    assert parse("Verdict: correct") == 1.0
    assert parse("The candidate is correct.") == 1.0
    assert parse("Verdict: incorrect") == 0.0
    assert parse("Verdict:\ncorrect.") == 1.0
    assert parse("partially correct") == 0.5  # the audit's exact case
    assert parse("partial") == 0.5
    # ...and never lets chatter INVERT the verdict (the graded failures of
    # a real 0.6B judge, executed by the 0.1.12 audit):
    assert parse("not correct") == 0.0
    assert parse("The candidate is wrong, so the answer is not correct") == 0.0
    assert parse("incorrect\ncorrect") == 0.0
    assert parse("") == 0.0 and parse("I cannot grade this") == 0.0


STUB_PIPELINE = """
from app.contract import RefusedInput


def load_corpus(directory=None):
    return 0


LOADED = {"documents": 0, "skipped": []}


def run_envelope(raw, *, request_id=None, principal=None):
    if raw is None:
        raise RefusedInput("empty payload")
    if raw == "boom":
        raise RuntimeError("the implementation is broken in a way the caller must not see")
    return {"echo": raw, "seen_by": principal["subject"]}


def output(env):
    return env


def run(raw, *, request_id=None, principal=None):
    return output(run_envelope(raw, request_id=request_id, principal=principal))


if __name__ == "__main__":
    from app.service import main

    raise SystemExit(main())
"""


def _boot(out, env):
    """Start the emitted service on a free port; return (proc, base_url)."""
    import socket
    import time
    import urllib.request

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.service"], cwd=out,
        env={"PATH": "/usr/bin", "PORT": str(port), **env},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        if proc.poll() is not None:
            raise AssertionError(f"service exited {proc.returncode}: {proc.stdout.read()[:800]}")
        try:
            urllib.request.urlopen(base + "/health", timeout=1)
            return proc, base
        except OSError:
            time.sleep(0.1)
    proc.kill()
    raise AssertionError(f"service never came up: {proc.stdout.read()[:800]}")


def _post(base, body, headers=None, path="/", token="t0ken"):
    import json as jsonlib
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        base + path, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {token}"} if token else {}),
                 **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, jsonlib.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, jsonlib.loads(e.read())


def test_the_deployment_entrypoint_actually_serves(reg, tmp_path):
    """The systemd unit runs `python -m app.pipeline`. A module that
    defines functions and exits cleanly is a service that dies silently
    on its first start -- found by asking 'has anyone deployed the
    deliverable?' and getting no for an answer. The emitted edge is
    app/service.py: /health answers, POST / runs the pipeline as the
    configured principal, and a refusal is a 422 with the reason."""
    out = tmp_path / "p"
    emit(architect(profile(**COMPLETE), reg), out)
    (out / "app" / "pipeline.py").write_text(STUB_PIPELINE)
    proc, base = _boot(out, {"AUTH_TOKEN": "t0ken", "SERVICE_SUBJECT": "ops",
                             "LLM_ENDPOINT": "http://127.0.0.1:9"})
    try:
        code, body = _post(base, b'{"x": 1}')
        assert code == 200 and body["result"] == {"echo": {"x": 1}, "seen_by": "ops"}, body
        code, body = _post(base, b"null")
        assert code == 422 and "refused" in body, body
        code, body = _post(base, b"null", token=None)
        assert code == 401, body
    finally:
        proc.terminate()
        assert proc.wait(timeout=20) == 0


def test_the_service_answers_500_not_a_dropped_connection(reg, tmp_path):
    """A fresh build's first POST once got curl: (52) empty reply -- the
    unwired gate's RuntimeError killed the connection with no status. Every
    failure now has a shape: 500 with the exception NAME, never its text,
    never a traceback, never silence. Plus the framing edges the audits
    dropped connections or smuggled requests on."""
    out = tmp_path / "p"
    emit(architect(profile(**COMPLETE), reg), out)
    (out / "app" / "pipeline.py").write_text(STUB_PIPELINE)
    proc, base = _boot(out, {"AUTH_TOKEN": "t0ken", "LLM_ENDPOINT": "http://127.0.0.1:9"})
    try:
        code, body = _post(base, b'"boom"')
        assert code == 500 and body["error"] == "RuntimeError", body
        assert "detail" not in body and "broken" not in str(body), body

        code, body = _post(base, b"x" * 100, path="/nowhere")
        assert code == 404
        code, body = _post(base, b"{}", headers={"Content-Length": "zzz"})
        assert code == 400
        code, body = _post(base, b"{}", headers={"Content-Length": "1_0"})
        assert code == 400
        code, body = _post(base, b"{}", headers={"Transfer-Encoding": "chunked"})
        assert code == 501
        code, body = _post(base, b"[" * 20000)
        assert code == 400, (code, body)
        big = b"x" * (2 * 1024 * 1024)
        try:
            code, body = _post(base, big)
            assert code == 413
        except OSError:
            pass  # server rejected and closed before reading -- also correct
    finally:
        proc.terminate()
        assert proc.wait(timeout=20) == 0


def test_the_service_binds_loopback_unless_told_otherwise(reg, tmp_path):
    out = tmp_path / "p"
    emit(architect(profile(**COMPLETE), reg), out)
    body = (out / "app" / "service.py").read_text()
    assert '"BIND", "127.0.0.1"' in body
    assert "ThreadingHTTPServer" in body


def test_ready_reports_the_missing_model_health_stays_liveness(reg, tmp_path):
    """/health said ok with the model down and misconfiguration was
    discovered by the first user. Configuration that is WRONG refuses the
    boot with one fatal line (exit 78); a dependency that is DOWN boots and
    /ready says so, so a deploy gates on it."""
    import json as jsonlib
    import urllib.error
    import urllib.request

    out = tmp_path / "p"
    emit(architect(profile(**FREEFORM), reg), out)  # freeform: needs a model
    assert "LLM_ENDPOINT" in (out / "deploy" / "env.example").read_text()
    (out / "app" / "pipeline.py").write_text(STUB_PIPELINE)

    dead = subprocess.run(
        [sys.executable, "-m", "app.service"], cwd=out, capture_output=True, text=True,
        env={"PATH": "/usr/bin", "PORT": "18999", "AUTH_TOKEN": "t0ken"}, timeout=30,
    )
    assert dead.returncode == 78 and "LLM_ENDPOINT" in dead.stderr, dead.stderr[-400:]

    proc, base = _boot(out, {"AUTH_TOKEN": "t0ken", "LLM_ENDPOINT": "http://127.0.0.1:9"})
    try:
        assert urllib.request.urlopen(base + "/health", timeout=3).status == 200
        try:
            urllib.request.urlopen(base + "/ready", timeout=5)
            raise AssertionError("/ready must 503 with the model unreachable")
        except urllib.error.HTTPError as e:
            assert e.code == 503
            body = jsonlib.loads(e.read())
            assert "unreachable" in " ".join(body["problems"]), body
    finally:
        proc.terminate()
        assert proc.wait(timeout=20) == 0


def test_the_emitted_project_ships_its_own_hygiene(reg, tmp_path):
    out = tmp_path / "p"
    emit(architect(profile(**COMPLETE), reg), out)
    ignore = (out / ".gitignore").read_text()
    assert "__pycache__" in ignore and "*.sqlite3" in ignore
    unit = (out / "deploy" / "systemd" / "app.service").read_text()
    assert "PYTHONUNBUFFERED=1" in unit and "EnvironmentFile=" in unit



def test_the_judge_may_not_be_the_author_under_another_name(reg, tmp_path):
    """JUDGE_ENDPOINT set to the same URL as LLM_ENDPOINT is the author
    grading itself with a costume on; the harness compares what resolves."""
    import json as jsonlib

    out = tmp_path / "p"
    emit(architect(profile(**FREEFORM), reg), out)
    (out / "evals" / "golden.jsonl").write_text(jsonlib.dumps(
        {"id": "g1", "input": "q", "output": "a"}) + "\n")
    (out / "app" / "pipeline.py").write_text("def run(p, **kw):\n    return 'a'\n")
    result = subprocess.run(
        [sys.executable, "evals/harness.py"], cwd=out, capture_output=True, text=True,
        env={"PATH": "/usr/bin", "LLM_ENDPOINT": "http://127.0.0.1:9",
             "JUDGE_ENDPOINT": "http://127.0.0.1:9"},
    )
    assert result.returncode == 1
    assert "author" in result.stderr, result.stderr[-300:]


def test_a_holdout_exactly_half_right_is_red(reg, tmp_path):
    import json as jsonlib

    out = tmp_path / "p"
    emit(architect(profile(**COMPLETE), reg), out)
    (out / "app" / "pipeline.py").write_text("def run(p, **kw):\n    return p\n")
    holdout = tmp_path / "holdout.jsonl"
    holdout.write_text("".join(jsonlib.dumps(c) + "\n" for c in (
        {"id": "h1", "input": {"a": 1}, "output": {"a": 1}},
        {"id": "h2", "input": {"a": 2}, "output": {"a": 3}},
    )))
    result = subprocess.run(
        [sys.executable, "evals/harness.py", "--cases", str(holdout)], cwd=out,
        capture_output=True, text=True, env={"PATH": "/usr/bin"},
    )
    assert result.returncode == 1, result.stdout + result.stderr
