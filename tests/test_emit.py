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
