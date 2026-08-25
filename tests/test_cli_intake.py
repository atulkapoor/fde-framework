"""`fde frame` and `fde ask` -- the two ways facts get in.

Both write one append-only session file. Neither is a prerequisite for the
other: prose then questions, questions then prose, or either alone.
"""

from typer.testing import CliRunner

from fde.cli import app
from fde.factlog import load_engagement

runner = CliRunner()

BRIEF = (
    "Extract fields from invoice PDFs. Data cannot leave the client environment. "
    "200,000 documents, 8,000 verified."
)


def engagement(tmp_path, name="acme"):
    runner.invoke(app, ["start", name, "--base", str(tmp_path)])
    return tmp_path / name


# --- fde frame -----------------------------------------------------------


def test_frame_reads_prose_into_a_session(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["frame", str(root), "--text", BRIEF])
    assert result.exit_code == 0
    assert load_engagement(root).profile.get("data_residency") == "cannot_leave"


def test_frame_plays_back_what_it_understood(tmp_path):
    """Said before anything is designed. It is how an FDE finds out they misread."""
    root = engagement(tmp_path)
    result = runner.invoke(app, ["frame", str(root), "--text", BRIEF])
    assert "cannot leave" in result.output.lower()
    assert "200,000" in result.output


def test_frame_says_so_when_it_understood_nothing(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["frame", str(root), "--text", "We want to explore AI."])
    assert "nothing" in result.output.lower()


def test_frame_writes_nothing_when_it_extracted_nothing(tmp_path):
    """An empty session file is noise in an append-only log."""
    root = engagement(tmp_path)
    runner.invoke(app, ["frame", str(root), "--text", "We want to explore AI."])
    assert list((root / "facts").iterdir()) == []


def test_framing_twice_appends_rather_than_overwrites(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(app, ["frame", str(root), "--text", BRIEF])
    runner.invoke(app, ["frame", str(root), "--text", "The environment is air-gapped."])
    assert len(list((root / "facts").iterdir())) == 2
    assert load_engagement(root).profile.get("hosting") == "air-gapped"


def test_frame_reads_from_a_file(tmp_path):
    root = engagement(tmp_path)
    brief = tmp_path / "rfp.txt"
    brief.write_text(BRIEF)
    runner.invoke(app, ["frame", str(root), "--file", str(brief)])
    facts = load_engagement(root).profile
    assert facts.get("corpus_size") == 200_000
    assert facts.fact("corpus_size").source == "rfp.txt"


# --- fde ask -------------------------------------------------------------


def test_ask_records_answers_against_the_role(tmp_path):
    """Independent of which question comes first: the residency answer is
    valid only for that dimension, so whatever else is asked skips."""
    root = engagement(tmp_path)
    result = runner.invoke(
        app, ["ask", str(root), "--role", "admin"], input="cannot_leave\n" + "\n" * 20
    )
    assert result.exit_code == 0
    fact = load_engagement(root).profile.fact("data_residency")
    assert fact.value == "cannot_leave"
    assert fact.respondent.role == "admin"


def test_ask_only_puts_questions_the_role_can_answer(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["ask", str(root), "--role", "user"], input="\n\n")
    assert "embeddings" not in result.output


def test_an_answer_narrows_what_is_asked_next(tmp_path):
    """Say data cannot leave, and nobody asks where the model runs."""
    root = engagement(tmp_path)
    result = runner.invoke(
        app, ["ask", str(root), "--role", "admin"], input="cannot_leave\n\nair-gapped\n"
    )
    assert "Where does the model run?" not in result.output


def test_skipping_is_legal_and_does_not_stall(tmp_path):
    """An intake that cannot get past an unknown is an intake that stops."""
    root = engagement(tmp_path)
    result = runner.invoke(app, ["ask", str(root), "--role", "admin"], input="\n\n\n\n\n\n")
    assert result.exit_code == 0
    assert load_engagement(root).profile.is_empty()


def test_an_unusable_answer_is_challenged_and_nothing_is_stored(tmp_path):
    """Storing it would put a wrong fact at artifact strength ahead of the
    answer that would have corrected it.

    Deliberately independent of which question comes first: "fast" parses as
    nothing at all, so whatever is asked, it earns a probe. Tying this to a
    position made it break every time a dimension was added.
    """
    root = engagement(tmp_path)
    result = runner.invoke(
        app, ["ask", str(root), "--role", "user"], input="fast\n" + "\n" * 12
    )
    assert "I need" in result.output
    assert load_engagement(root).profile.is_empty()


def test_a_corrected_answer_is_stored(tmp_path):
    """The probe is a prompt for precision, not a refusal."""
    root = engagement(tmp_path)
    runner.invoke(app, ["frame", str(root), "--text", "Responses must return in under 800ms."])
    assert load_engagement(root).profile.get("latency_budget_ms") == 800


def test_an_answer_that_contradicts_an_earlier_one_says_which(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(app, ["frame", str(root), "--text", "Data cannot leave the client environment."])
    # Offer public-saas to every question and skip when it is rejected. It is a
    # legal value for exactly one dimension, so this finds that dimension
    # wherever the order happens to put it -- which is what stops this test
    # breaking every time one is added.
    result = runner.invoke(
        app, ["ask", str(root), "--role", "admin"], input="public-saas\n\n" * 20
    )
    assert "data_residency" in result.output
    assert "cannot_leave" in result.output


def test_ask_writes_one_session_not_one_file_per_answer(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(
        app, ["ask", str(root), "--role", "admin"], input="cannot_leave\n" + "\n" * 20
    )
    assert len(list((root / "facts").iterdir())) == 1


def test_answering_nothing_writes_no_session(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(app, ["ask", str(root), "--role", "admin"], input="\n\n\n\n\n\n")
    assert list((root / "facts").iterdir()) == []


def test_the_respondents_name_is_recorded_when_given(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(
        app,
        ["ask", str(root), "--role", "admin", "--name", "R. Iyer"],
        input="cannot_leave\n" + "\n" * 20,
    )
    assert load_engagement(root).profile.fact("data_residency").respondent.name == "R. Iyer"


def test_ask_reports_when_the_role_has_nothing_left(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(app, ["frame", str(root), "--text", BRIEF])
    result = runner.invoke(app, ["ask", str(root), "--role", "skeptic"], input="\n")
    assert "nothing" in result.output.lower()
