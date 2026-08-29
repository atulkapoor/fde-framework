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
        app, ["ask", str(root), "--role", "admin"], input="cannot_leave\n\n" * 20
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
    # Offered to every question, legal for exactly one. See the note above.
    runner.invoke(
        app, ["ask", str(root), "--role", "admin"], input="cannot_leave\n\n" * 20
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
        input="cannot_leave\n\n" * 20,
    )
    assert load_engagement(root).profile.fact("data_residency").respondent.name == "R. Iyer"


def test_ask_reports_when_the_role_has_nothing_left(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(app, ["frame", str(root), "--text", BRIEF])
    result = runner.invoke(app, ["ask", str(root), "--role", "skeptic"], input="\n")
    assert "nothing" in result.output.lower()


def test_a_contest_becomes_a_disagreement_and_undecides_what_leaned_on_it(tmp_path):
    """The campaign's scenario, end to end: sponsor says may_leave, admin
    contests with cannot_leave, and serving -- which had quietly sided with
    the sponsor -- goes honestly undecided while status names both voices."""
    root = engagement(tmp_path)
    runner.invoke(app, ["ask", str(root), "--role", "sponsor", "--name", "V. Rao"],
                  input="may_leave\n\n" * 25)
    result = runner.invoke(app, ["ask", str(root), "--role", "admin",
                                 "--name", "P. Iyer"],
                           input="cannot_leave\n\n" * 40)
    assert "said may_leave" in result.output

    status = runner.invoke(app, ["status", str(root)])
    assert "respondents disagree" in status.output
    assert "V. Rao" in status.output and "P. Iyer" in status.output

    architect = runner.invoke(app, ["architect", str(root)])
    assert "data_residency" in architect.output.split("unresolved:")[-1]


def test_nobody_is_offered_their_own_in_session_answer(tmp_path):
    """Live-profile facts once carried no speaker, so the contest logic
    offered a respondent's fresh answer back to them as 'system said X'."""
    root = engagement(tmp_path)
    result = runner.invoke(app, ["ask", str(root), "--role", "admin"],
                           input="cannot_leave\n\n" * 40)
    assert "said cannot_leave" not in result.output


def test_ask_can_run_a_dedicated_scope_pass(tmp_path):
    """An FDE running an NFR review wants only that axis on the table --
    a --scope pass asks nothing outside it."""
    root = engagement(tmp_path)
    result = runner.invoke(app, ["ask", str(root), "--role", "sponsor",
                                 "--scope", "non_functional"],
                           input="\n" * 12)
    assert "person waiting" in result.output.lower() or "explainable" in result.output.lower()
    assert "How many items in total?" not in result.output


def test_an_unknown_scope_axis_lists_the_real_ones(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["ask", str(root), "--role", "admin",
                                 "--scope", "vibes"], input="\n")
    assert result.exit_code == 1
    assert "non_functional" in result.output


# --- the contest loop terminates and tells the truth ------------------------


def _contest_setup(tmp_path):
    root = engagement(tmp_path)
    runner.invoke(app, ["ask", str(root), "--role", "sponsor", "--name", "Sam"],
                  input="cannot_leave\n\n" * 25)
    return root


def test_confirming_a_contested_answer_retires_the_question(tmp_path):
    """Five confirmations of one value once recorded five duplicate facts,
    with the same prompt re-offered each time -- the holder never changed,
    so nothing ever retired it."""
    root = _contest_setup(tmp_path)
    result = runner.invoke(app, ["ask", str(root), "--role", "admin",
                                 "--name", "Ada", "--scope", "data"],
                          input="cannot_leave\n\n" * 10)
    assert result.output.count("confirm, correct, or skip") == 1
    assert "Recorded 1 answer(s)" in result.output


def test_a_settled_contest_is_not_reoffered_next_session(tmp_path):
    root = _contest_setup(tmp_path)
    runner.invoke(app, ["ask", str(root), "--role", "admin", "--name", "Ada",
                        "--scope", "data"], input="cannot_leave\n\n" * 10)
    again = runner.invoke(app, ["ask", str(root), "--role", "admin",
                                "--name", "Ada", "--scope", "data"],
                          input="\n" * 10)
    assert "confirm, correct, or skip" not in again.output


def test_an_impossible_contest_value_is_named_a_contradiction(tmp_path):
    """Disagreement stays a finding, but a contesting value the contester's
    own other answers rule out is a contradiction wearing one."""
    root = _contest_setup(tmp_path)
    runner.invoke(app, ["ask", str(root), "--role", "admin", "--name", "Ada",
                        "--scope", "environment"], input="air-gapped\n\n" * 10)
    result = runner.invoke(app, ["ask", str(root), "--role", "admin",
                                 "--name", "Ada", "--scope", "data"],
                          input="may_leave\n\n" * 10)
    assert "one side of this disagreement is a contradiction" in result.output
