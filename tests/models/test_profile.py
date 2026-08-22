"""The profile's load-bearing property: arrival order never decides anything.

Provenance does, and it is dimension-dependent. Environment facts prefer what was
detected; requirements prefer what was stated in an artifact.
"""

import pytest
from pydantic import ValidationError

from fde.models.base import DimensionKind, Provenance, wins
from fde.models.fact import Fact
from fde.models.profile import Disagreement, Profile
from fde.models.respondent import Respondent

SPONSOR = Respondent(role="sponsor", name="A. Sponsor")
USER = Respondent(role="user", name="B. User")
ADMIN = Respondent(role="admin", name="C. Admin")

VRAM = "available_vram_gb"
LATENCY = "latency_budget_ms"
QPS = "peak_qps"


# --- provenance ordering -------------------------------------------------


def test_detected_beats_interview_for_environment_facts():
    assert wins(Provenance.DETECTED, Provenance.INTERVIEW, DimensionKind.ENVIRONMENT)


def test_artifact_beats_detected_for_requirements():
    assert wins(Provenance.ARTIFACT, Provenance.DETECTED, DimensionKind.REQUIREMENT)


def test_inferred_never_wins():
    for kind in DimensionKind:
        assert not wins(Provenance.INFERRED, Provenance.OBSERVATION, kind)


def test_a_provenance_does_not_beat_itself():
    for kind in DimensionKind:
        assert not wins(Provenance.DETECTED, Provenance.DETECTED, kind)


# --- order independence --------------------------------------------------


def test_conflicts_resolve_by_provenance_not_arrival_order():
    p = Profile()
    p.ingest([Fact(VRAM, 40, Provenance.INTERVIEW, kind=DimensionKind.ENVIRONMENT)])
    p.ingest([Fact(VRAM, 80, Provenance.DETECTED, kind=DimensionKind.ENVIRONMENT)])
    assert p.get(VRAM) == 80

    # A later, weaker fact must not dislodge the stronger one.
    p.ingest([Fact(VRAM, 24, Provenance.INTERVIEW, kind=DimensionKind.ENVIRONMENT)])
    assert p.get(VRAM) == 80


def test_superseded_facts_are_retained_for_audit():
    p = Profile()
    p.ingest([Fact(VRAM, 40, Provenance.INTERVIEW, kind=DimensionKind.ENVIRONMENT)])
    p.ingest([Fact(VRAM, 80, Provenance.DETECTED, kind=DimensionKind.ENVIRONMENT)])
    assert len(p.history(VRAM)) == 2


def test_equal_provenance_takes_the_later_fact_as_a_correction():
    p = Profile()
    p.ingest([Fact(LATENCY, 500, Provenance.INTERVIEW, respondent=SPONSOR)])
    p.ingest([Fact(LATENCY, 200, Provenance.INTERVIEW, respondent=SPONSOR)])
    assert p.get(LATENCY) == 200


def test_ingest_order_does_not_change_the_resolved_profile():
    facts = [
        Fact(VRAM, 80, Provenance.DETECTED, kind=DimensionKind.ENVIRONMENT),
        Fact(LATENCY, 800, Provenance.ARTIFACT),
        Fact(QPS, 40, Provenance.INTERVIEW, respondent=ADMIN),
    ]
    forward, backward = Profile(), Profile()
    forward.ingest(facts)
    backward.ingest(list(reversed(facts)))
    assert forward.values() == backward.values()


# --- disagreement --------------------------------------------------------


def test_two_respondents_disagreeing_raises_a_disagreement():
    """The sponsor says five seconds is fine; the user says anything over one
    sends them back to the spreadsheet. That gap is the most valuable thing
    discovery produces, and last-write-wins destroys it."""
    p = Profile()
    p.ingest([Fact(LATENCY, 5000, Provenance.INTERVIEW, respondent=SPONSOR)])
    p.ingest([Fact(LATENCY, 1000, Provenance.INTERVIEW, respondent=USER)])

    assert len(p.disagreements()) == 1
    d = p.disagreements()[0]
    assert isinstance(d, Disagreement)
    assert {r.role for r in d.respondents} == {"sponsor", "user"}


def test_a_disagreed_dimension_is_left_unresolved():
    p = Profile()
    p.ingest([Fact(LATENCY, 5000, Provenance.INTERVIEW, respondent=SPONSOR)])
    p.ingest([Fact(LATENCY, 1000, Provenance.INTERVIEW, respondent=USER)])
    assert not p.resolved(LATENCY)
    assert p.get(LATENCY) is None


def test_disagreement_is_never_averaged():
    p = Profile()
    p.ingest([Fact(LATENCY, 5000, Provenance.INTERVIEW, respondent=SPONSOR)])
    p.ingest([Fact(LATENCY, 1000, Provenance.INTERVIEW, respondent=USER)])
    assert p.get(LATENCY) not in (3000, 3000.0)


def test_same_respondent_correcting_themselves_is_not_a_disagreement():
    p = Profile()
    p.ingest([Fact(QPS, 40, Provenance.INTERVIEW, respondent=ADMIN)])
    p.ingest([Fact(QPS, 120, Provenance.INTERVIEW, respondent=ADMIN)])
    assert p.disagreements() == []
    assert p.get(QPS) == 120


def test_stronger_provenance_settles_what_respondents_disagreed_about():
    """A measurement ends an argument between two people."""
    p = Profile()
    env = DimensionKind.ENVIRONMENT
    p.ingest([Fact(VRAM, 40, Provenance.INTERVIEW, respondent=SPONSOR, kind=env)])
    p.ingest([Fact(VRAM, 24, Provenance.INTERVIEW, respondent=ADMIN, kind=env)])
    assert p.disagreements()

    p.ingest([Fact(VRAM, 80, Provenance.DETECTED, kind=DimensionKind.ENVIRONMENT)])
    assert p.disagreements() == []
    assert p.get(VRAM) == 80


def test_agreement_between_respondents_is_not_a_disagreement():
    p = Profile()
    p.ingest([Fact(LATENCY, 800, Provenance.INTERVIEW, respondent=SPONSOR)])
    p.ingest([Fact(LATENCY, 800, Provenance.INTERVIEW, respondent=USER)])
    assert p.disagreements() == []
    assert p.get(LATENCY) == 800


# --- shape ---------------------------------------------------------------


def test_empty_profile_reports_itself_empty():
    assert Profile().is_empty()


def test_unknown_dimension_returns_none_rather_than_raising():
    assert Profile().get("no_such_dimension") is None


def test_facts_may_carry_a_traceable_span_into_their_source():
    text = "Data cannot leave the client environment."
    f = Fact("data_residency", "cannot_leave", Provenance.ARTIFACT, span=(0, 25), source="brief")
    assert text[f.span[0] : f.span[1]] == "Data cannot leave the cli"


def test_fact_is_immutable():
    f = Fact(QPS, 40, Provenance.INTERVIEW)
    with pytest.raises(ValidationError):
        f.value = 99
