"""The engagement store: append-only sessions, one derived record.

An FDE is interrupted, offline, working across days, and talking to different
people. The storage model has to survive all four, so nothing is ever rewritten
and the resolved view is recomputed rather than maintained.
"""

import pytest
import yaml

from fde.factlog import (
    Engagement,
    Session,
    load_engagement,
    start_engagement,
)
from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.respondent import Respondent

SPONSOR = Respondent(role="sponsor", name="A. Sponsor")
USER = Respondent(role="user", name="B. User")
ADMIN = Respondent(role="admin", name="C. Admin")

STATEMENT = (
    "Extract financial fields from unstructured invoice PDFs into a unified JSON "
    "schema. Data cannot leave the client environment."
)


def sponsor_session():
    return Session(
        session_id="0001-sponsor",
        respondent=SPONSOR,
        facts=[Fact("latency_budget_ms", 5000, Provenance.INTERVIEW)],
    )


def user_session():
    return Session(
        session_id="0002-users",
        respondent=USER,
        facts=[Fact("latency_budget_ms", 1000, Provenance.INTERVIEW)],
    )


# --- starting ------------------------------------------------------------


def test_an_engagement_starts_empty_and_needs_no_statement(tmp_path):
    """An FDE who only answers questions is a supported path."""
    e = start_engagement(tmp_path, "acme")
    assert e.profile.is_empty()
    assert e.statements == []


def test_starting_twice_does_not_clobber_the_first(tmp_path):
    start_engagement(tmp_path, "acme").append(sponsor_session())
    with pytest.raises(FileExistsError):
        start_engagement(tmp_path, "acme")


# --- append-only ---------------------------------------------------------


def test_each_session_writes_its_own_file(tmp_path):
    e = start_engagement(tmp_path, "acme")
    e.append(sponsor_session())
    e.append(user_session())
    assert sorted(p.name for p in e.facts_dir.iterdir()) == [
        "0001-sponsor.yaml",
        "0002-users.yaml",
    ]


def test_appending_never_rewrites_an_earlier_file(tmp_path):
    e = start_engagement(tmp_path, "acme")
    e.append(sponsor_session())
    before = (e.facts_dir / "0001-sponsor.yaml").read_text()
    e.append(user_session())
    assert (e.facts_dir / "0001-sponsor.yaml").read_text() == before


def test_a_session_id_cannot_be_reused(tmp_path):
    e = start_engagement(tmp_path, "acme")
    e.append(sponsor_session())
    with pytest.raises(FileExistsError):
        e.append(sponsor_session())


def test_interrupted_intake_is_a_valid_engagement(tmp_path):
    """Four questions in, the laptop closes. This must still load."""
    e = start_engagement(tmp_path, "acme")
    e.append(sponsor_session())
    reloaded = load_engagement(tmp_path / "acme")
    assert reloaded.profile.get("latency_budget_ms") == 5000


# --- the derived record --------------------------------------------------


def test_the_record_is_recomputed_not_maintained(tmp_path):
    e = start_engagement(tmp_path, "acme")
    e.append(sponsor_session())
    assert e.rebuild() == e.rebuild()


def test_a_hand_written_session_file_is_honoured(tmp_path):
    """The escape hatch stays open. It is just YAML."""
    e = start_engagement(tmp_path, "acme")
    (e.facts_dir / "0009-manual.yaml").write_text(
        "session_id: 0009-manual\n"
        "respondent: {role: admin, name: C. Admin}\n"
        "facts:\n"
        "  - {dimension: peak_qps, value: 40, provenance: interview}\n"
    )
    assert load_engagement(tmp_path / "acme").profile.get("peak_qps") == 40


def test_a_malformed_session_file_names_itself(tmp_path):
    e = start_engagement(tmp_path, "acme")
    (e.facts_dir / "0009-broken.yaml").write_text("facts: [{dimension: x}]\n")
    with pytest.raises(ValueError, match="0009-broken"):
        load_engagement(tmp_path / "acme")


# --- attribution ---------------------------------------------------------


def test_every_fact_carries_the_respondent_who_gave_it(tmp_path):
    e = start_engagement(tmp_path, "acme")
    e.append(sponsor_session())
    fact = load_engagement(tmp_path / "acme").profile.history("latency_budget_ms")[0]
    assert fact.respondent.role == "sponsor"
    assert fact.session_id == "0001-sponsor"


def test_a_session_stamps_its_respondent_onto_facts_that_omit_one(tmp_path):
    """The session already says who is talking; repeating it per fact invites drift."""
    e = start_engagement(tmp_path, "acme")
    bare = Session("0001-sponsor", SPONSOR, [Fact("peak_qps", 40, Provenance.INTERVIEW)])
    assert bare.facts[0].respondent.role == "system"  # unstamped
    e.append(bare)

    stamped = load_engagement(tmp_path / "acme").profile.history("peak_qps")[0]
    assert stamped.respondent == SPONSOR
    assert stamped.session_id == "0001-sponsor"


def test_the_session_file_does_not_repeat_the_respondent_per_fact(tmp_path):
    """Recorded once, at the top. Repetition is what lets it drift."""
    e = start_engagement(tmp_path, "acme")
    e.append(sponsor_session())
    written = yaml.safe_load((e.facts_dir / "0001-sponsor.yaml").read_text())
    assert written["respondent"]["role"] == "sponsor"
    assert all("respondent" not in fact for fact in written["facts"])


def test_two_sessions_disagreeing_surfaces_as_a_disagreement(tmp_path):
    e = start_engagement(tmp_path, "acme")
    e.append(sponsor_session())
    e.append(user_session())
    disagreements = load_engagement(tmp_path / "acme").profile.disagreements()
    assert len(disagreements) == 1
    assert {r.role for r in disagreements[0].respondents} == {"sponsor", "user"}


# --- statements ----------------------------------------------------------


def test_the_original_statement_is_immutable(tmp_path):
    """The scope-drift gate measures against it, so it can never be edited."""
    e = start_engagement(tmp_path, "acme", statement=STATEMENT)
    e.revise_statement("Actually invoices, not receipts.", reason="discovery")
    assert e.original_statement().text.startswith("Extract financial fields")
    assert e.current_statement().text.startswith("Actually invoices")


def test_statement_revisions_record_why(tmp_path):
    e = start_engagement(tmp_path, "acme", statement=STATEMENT)
    e.revise_statement("Invoices, not receipts.", reason="discovery week 2")
    assert e.statements[-1].reason == "discovery week 2"


def test_statements_survive_a_reload(tmp_path):
    e = start_engagement(tmp_path, "acme", statement=STATEMENT)
    e.revise_statement("Invoices.", reason="discovery")
    reloaded = load_engagement(tmp_path / "acme")
    assert len(reloaded.statements) == 2
    assert reloaded.original_statement().version == 1


# --- ordering ------------------------------------------------------------


def test_session_order_on_disk_does_not_change_the_resolved_profile(tmp_path):
    """Provenance decides, not filenames."""
    forward = start_engagement(tmp_path / "a", "acme")
    forward.append(Session("0001", ADMIN, [Fact("peak_qps", 40, Provenance.INTERVIEW)]))
    forward.append(Session("0002", ADMIN, [Fact("peak_qps", 40, Provenance.DETECTED)]))

    backward = start_engagement(tmp_path / "b", "acme")
    backward.append(Session("0001", ADMIN, [Fact("peak_qps", 40, Provenance.DETECTED)]))
    backward.append(Session("0002", ADMIN, [Fact("peak_qps", 40, Provenance.INTERVIEW)]))

    assert forward.rebuild().values() == backward.rebuild().values()


def test_an_engagement_reports_where_it_lives(tmp_path):
    e: Engagement = start_engagement(tmp_path, "acme")
    assert e.root == tmp_path / "acme"
