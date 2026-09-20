"""Client exports become pairs, with a report of what was kept, skipped,
deduplicated and verified -- and nothing verified by default."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from fde.cli import app
from fde.factlog import start_engagement
from fde.importer import ExportError, read_rows, to_pairs

runner = CliRunner()

CSV = """ticket_id,body,queue,checked
1,Where is my card,card_arrival,yes
2,,card_arrival,yes
3,My card was stolen,lost_or_stolen_card,no
4,Where is my card,card_arrival,yes
5,Fee charged twice,,yes
6,Change my pin,change_pin,yes
"""


def test_csv_rows_become_pairs_and_the_report_says_what_happened(tmp_path):
    export = tmp_path / "tickets.csv"
    export.write_text(CSV)
    pairs, report = to_pairs(read_rows(export), input_cols=["body"], output_cols=["queue"],
                             id_col="ticket_id", verified_when="checked=yes")
    assert report == {"rows": 6, "kept": 3, "skipped_empty": 2, "duplicates": 1, "verified": 2}
    assert pairs[0] == {"id": "1", "input": "Where is my card",
                        "output": {"queue": "card_arrival"}, "verified": True}
    assert pairs[1]["verified"] is False


def test_nothing_is_verified_unless_the_caller_says_how(tmp_path):
    export = tmp_path / "tickets.csv"
    export.write_text(CSV)
    _, report = to_pairs(read_rows(export), input_cols=["body"], output_cols=["queue"])
    assert report["verified"] == 0
    _, report = to_pairs(read_rows(export), input_cols=["body"], output_cols=["queue"],
                         all_verified=True)
    assert report["verified"] == 3


def test_several_input_columns_make_a_dict_and_prose_output_a_string(tmp_path):
    export = tmp_path / "rows.jsonl"
    export.write_text(json.dumps({"subject": "Card", "body": "Where is it", "reply": "It is"})
                      + "\n")
    pairs, _ = to_pairs(read_rows(export), input_cols=["subject", "body"],
                        output_cols=["reply"], output_text=True)
    assert pairs[0]["input"] == {"subject": "Card", "body": "Where is it"}
    assert pairs[0]["output"] == "It is"


def test_a_missing_column_is_named_with_what_the_export_has(tmp_path):
    export = tmp_path / "tickets.csv"
    export.write_text(CSV)
    try:
        to_pairs(read_rows(export), input_cols=["text"], output_cols=["queue"])
    except ExportError as exc:
        assert "columns not in the export: text" in str(exc) and "body" in str(exc)
    else:
        raise AssertionError("a missing column must refuse")


def test_the_command_writes_pairs_the_intake_can_read(tmp_path):
    start_engagement(tmp_path, "acme", statement="Route each message.")
    export = tmp_path / "tickets.csv"
    export.write_text(CSV)
    root = str(tmp_path / "acme")
    result = runner.invoke(app, ["import", root, "--file", str(export), "--input", "body",
                                 "--output", "queue", "--id", "ticket_id",
                                 "--verified-when", "checked=yes"])
    assert result.exit_code == 0, result.output
    assert "kept 3" in result.output and "2 verified" in result.output
    out = tmp_path / "acme" / "artifacts" / "imported-pairs.jsonl"
    assert out.exists() and "next: fde samples" in result.output
    refused = runner.invoke(app, ["import", root, "--file", str(tmp_path / "x.parquet"),
                                  "--input", "a", "--output", "b"])
    assert refused.exit_code == 1
