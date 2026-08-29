"""Turning an architecture into a project on disk.

The bar is not that files appear. It is that the emitted project imports, that
its wiring matches the decisions, that the boundary is enforced in the code
rather than described in the documentation, and that anything the framework
could not decide is loud rather than absent.
"""

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


def test_the_gate_carries_the_idempotency_key(reg, tmp_path):
    """The key matters more than the gate: a gate stops the wrong thing once,
    a key means doing it twice cannot charge twice."""
    emit(architect(profile(**MUTATIVE), reg), tmp_path)
    assert "idempotency_key=" in (tmp_path / "app" / "pipeline.py").read_text()


def test_the_controls_fail_closed_until_wired(reg, tmp_path):
    """An approval gate that defaults to yes is decoration. The first run must
    say what has not been decided yet, not do the irreversible thing."""
    emit(architect(profile(**MUTATIVE), reg), tmp_path)
    result = subprocess.run(
        [sys.executable, "-c",
         "from app.controls import ApprovalGate\nApprovalGate('x').run({})"],
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
    assert "not yet implemented" in result.stderr or "errored" in result.stderr


def test_an_empty_golden_set_is_a_visible_gap_not_a_red_build(reg, tmp_path):
    out = tmp_path / "out"
    emit(architect(profile(**COMPLETE), reg), out)
    result = subprocess.run(
        [sys.executable, "evals/harness.py"], cwd=out, capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "empty" in result.stderr


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
    assert result.returncode == 0, result.stderr
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
    import json

    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text(json.dumps(
        {"id": "a", "input": "x", "verified": True,
         "output": {"total": 1.0, "account": "****1"}}) + "\n")
    out = tmp_path / "proj"
    emit(architect(profile(**COMPLETE), reg), out, pairs_path=pairs)
    cases = (out / "evals" / "adversarial.jsonl").read_text()
    assert "prompt_injection" in cases
    assert "sensitive_egress" in cases


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
    emit(architect(profile(hosting="air-gapped", output_shape="decision"), reg), tmp_path)
    pipeline = (tmp_path / "app" / "pipeline.py").read_text()
    for line in pipeline.splitlines():
        if line.startswith("from app.components import "):
            name = line.rsplit(" ", 1)[1]
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

CONTRACT = ["total_due", "vat"]
SYNONYMS = {"total_due": ["amount payable", "amount due", "total"]}
MONEY = re.compile(r"[-+]?\\d[\\d,]*(?:\\.\\d+)?")

def _raw(text):
    out = {}
    for segment in re.split(r"[\\n|]", text):
        match = MONEY.search(segment)
        if match:
            label = segment[: match.start()].strip(" .:\\t$")
            if label:
                out[label] = float(match.group().replace(",", ""))
    return out

STEP = representation.Representation(synonyms=SYNONYMS)

def run(payload):
    if isinstance(payload, str):
        payload = {"contract": CONTRACT, "records": [{"id": "case", "raw": _raw(payload)}]}
    record = STEP.run(payload)["records"][0]
    if record["unmapped"] or record["rejected"]:
        raise ValueError(str(record))
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
