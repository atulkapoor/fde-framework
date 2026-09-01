"""Multi-modality as the normaliser's property.

A claims system takes photos AND the policy document AND repair history; a
factory system takes camera feed AND manuals AND telemetry. One input_format
value could not carry that, and the decline was the ten-industry battery's
loudest finding. The design: input_format is multi_valued (peers, not a
disagreement), perception declares fan_out_on and gets one instance per
modality, and downstream -- which never reads modality -- decides once.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fde.architect import architect
from fde.cli import app
from fde.decide import decide_all
from fde.emit import emit
from fde.intake.prose import parse_prose
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.profile import Profile
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"
runner = CliRunner()

MULTI = ("It inspects the camera feed from the line, reads the equipment "
         "manuals, and watches sensor telemetry.")


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


def multimodal_profile(reg):
    p = Profile()
    p.ingest(parse_prose(MULTI, reg))
    p.ingest([Fact("output_shape", "decision", Provenance.INTERVIEW),
              Fact("corpus_size", 50_000, Provenance.INTERVIEW),
              Fact("latency_budget_ms", 2000, Provenance.INTERVIEW)])
    return p


# --- peers, not disagreements ------------------------------------------------


def test_three_modalities_in_one_sentence_are_three_answers(reg):
    profile = Profile()
    profile.ingest(parse_prose(MULTI, reg))
    assert profile.values()["input_format"] == ("documents", "images", "streams")
    assert profile.disagreements() == []


def test_a_single_modality_stays_a_scalar(reg):
    profile = Profile()
    profile.ingest(parse_prose("Invoices arrive as PDFs.", reg))
    assert profile.values()["input_format"] == "documents"


def test_single_valued_dimensions_still_disagree(reg):
    """Peer semantics must not leak: two hosting answers from two people is
    still a finding, not a union."""
    from fde.models.respondent import Respondent

    profile = Profile()
    profile.ingest([
        Fact("hosting", "on-prem", Provenance.INTERVIEW,
             respondent=Respondent(role="sponsor", name="A")),
        Fact("hosting", "customer-vpc", Provenance.INTERVIEW,
             respondent=Respondent(role="admin", name="B")),
    ])
    assert not profile.resolved("hosting")
    assert profile.disagreements()


# --- the fan-out -------------------------------------------------------------


def test_perception_fans_one_instance_per_modality(reg):
    values = multimodal_profile(reg).values()
    decisions = decide_all(values, reg, components=["perception", "reasoning"])
    assert "perception:documents" in decisions
    assert "perception:images" in decisions
    assert "perception:streams" in decisions
    assert "perception" not in decisions
    assert "reasoning" in decisions  # downstream decides once


def test_each_instance_gets_its_own_modality_rules(reg):
    values = multimodal_profile(reg).values()
    decisions = decide_all(values, reg, components=["perception"])
    assert decisions["perception:streams"].approach == "windowed-ingestion"
    assert decisions["perception:documents"].approach == "text-extraction"
    assert decisions["perception:images"].approach == "ocr-pipeline"


def test_the_emitted_pipeline_runs_every_modality_before_downstream(reg, tmp_path):
    arch = architect(multimodal_profile(reg), reg)
    emit(arch, tmp_path / "p")
    pipeline = (tmp_path / "p" / "app" / "pipeline.py").read_text()
    assert "perception_images" in pipeline
    assert "perception_streams" in pipeline
    for modality in ("images", "streams", "documents"):
        assert (tmp_path / "p" / "app" / "components"
                / f"perception_{modality}.py").exists()
    order = [line for line in pipeline.splitlines() if "('" in line]
    perception_rows = [i for i, line in enumerate(order) if "perception" in line]
    downstream = [i for i, line in enumerate(order) if "reasoning" in line]
    assert downstream and max(perception_rows) < min(downstream)


# --- the interview speaks it -------------------------------------------------


def test_an_interview_answer_may_list_modalities(tmp_path):
    root = tmp_path / "eng"
    runner.invoke(app, ["start", "eng", "--base", str(tmp_path)])
    result = runner.invoke(app, ["ask", str(root), "--registry", str(FRAMEWORK),
                                 "--role", "admin", "--name", "Ana"],
                          input="photos, manuals and telemetry\n\n" * 12)
    assert "Recorded" in result.output
    status = runner.invoke(app, ["status", str(root), "--registry", str(FRAMEWORK)])
    assert "input_format += images" in status.output
    assert "input_format += streams" in status.output


def test_one_noun_phrase_stated_precisely_is_still_one_answer(reg):
    """"Scanned supplier invoices" matches scanned_documents and documents in
    the same breath -- that is refinement, not multi-modality, and the
    proximity rule keeps them one answer."""
    profile = Profile()
    profile.ingest(parse_prose("Scanned supplier invoices arrive daily.", reg))
    assert profile.values()["input_format"] == "scanned_documents"


# --- overrides reach fanned instances ----------------------------------------


def test_an_override_of_a_fanned_component_applies_to_every_instance(reg):
    from fde.architect import architect as build_architecture

    profile = multimodal_profile(reg)
    arch = build_architecture(profile, reg, overrides={
        "perception": {"chosen": "passthrough", "because": "client insists"},
    })
    instances = {k: d.approach for k, d in arch.decisions.items()
                 if k.startswith("perception:")}
    assert instances and all(a == "passthrough" for a in instances.values())


def test_an_instance_override_targets_exactly_one_modality(reg):
    from fde.architect import architect as build_architecture

    profile = multimodal_profile(reg)
    arch = build_architecture(profile, reg, overrides={
        "perception:images": {"chosen": "passthrough", "because": "camera feed is pre-parsed"},
    })
    assert arch.decisions["perception:images"].approach == "passthrough"
    assert arch.decisions["perception:streams"].approach == "windowed-ingestion"
