"""The model reads the brief -- as a proposer, never an authority.

Everything here runs without a network: the completion function is
injectable, and one test stands up a real localhost server to prove the
OpenAI-compatible path end to end.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fde.cli import app
from fde.intake.llm_reader import (
    BoundaryRefusal,
    check_boundary,
    extraction_schema,
    is_local,
    read_with_llm,
)
from fde.models.base import Provenance
from fde.registry import load_registry

FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"
runner = CliRunner()


@pytest.fixture(scope="module")
def reg():
    return load_registry(FRAMEWORK)


# --- the registry is the schema --------------------------------------------


def test_the_schema_is_derived_from_the_registry(reg):
    schema = extraction_schema(reg, ["hosting", "corpus_size", "cheap_path_coverage"])
    assert schema["properties"]["hosting"]["enum"] == list(
        reg.dimensions["hosting"].values
    )
    assert schema["properties"]["corpus_size"]["type"] == "integer"
    assert schema["properties"]["cheap_path_coverage"]["maximum"] == 1


def test_a_new_dimension_extends_the_model_target_automatically(reg):
    """The whole point of deriving: access_model was added yesterday and is
    already in the schema, with its declared values as the only options."""
    schema = extraction_schema(reg, ["access_model"])
    assert set(schema["properties"]["access_model"]["enum"]) == {
        "single_operator", "role_based", "open_internal",
    }


# --- the boundary doctrine governs the tool's own intake --------------------


def test_a_hosted_model_is_refused_when_data_cannot_leave(reg):
    with pytest.raises(BoundaryRefusal, match="may not leave"):
        check_boundary({"data_residency": "cannot_leave"}, reg, endpoint=None)


def test_unknown_is_not_permission(reg):
    with pytest.raises(BoundaryRefusal, match="unknown is not permission"):
        check_boundary({}, reg, endpoint=None)


def test_stated_permission_admits_the_hosted_model(reg):
    check_boundary({"data_residency": "may_leave"}, reg, endpoint=None)


def test_a_local_endpoint_needs_no_permission(reg):
    assert is_local("http://localhost:8000")
    check_boundary({"data_residency": "cannot_leave"}, reg,
                   endpoint="http://127.0.0.1:11434")


def test_a_brief_that_forbids_egress_refuses_its_own_upload(reg):
    """The exact sentence being read is part of the evidence: a brief saying
    'data cannot leave' must not itself be sent to a hosted model."""
    facts_from_this_brief = {"data_residency": "cannot_leave"}
    with pytest.raises(BoundaryRefusal):
        check_boundary(facts_from_this_brief, reg, endpoint=None)


# --- proposals are validated and weak ---------------------------------------


def test_proposals_land_at_inferred_and_illegal_values_are_named(reg):
    reply = json.dumps({
        "hosting": "customer-vpc",          # legal
        "corpus_size": 48000,               # legal
        "query_pattern": "telepathy",       # not a declared value
        "human_waiting": "yes",             # legal enum
        "confidence_calibrated": "maybe",   # not a boolean
    })
    facts, dropped = read_with_llm(
        "brief text", reg, {"data_residency": "may_leave"},
        complete=lambda prompt: reply,
    )
    values = {f.dimension: f.value for f in facts}
    assert values["hosting"] == "customer-vpc"
    assert values["corpus_size"] == 48000
    assert values["human_waiting"] == "yes"
    assert all(f.provenance is Provenance.INFERRED for f in facts)
    assert any("telepathy" in d for d in dropped)
    assert any("confidence_calibrated" in d for d in dropped)


def test_the_model_is_not_asked_about_what_is_already_known(reg):
    seen = {}

    def spy(prompt):
        seen["prompt"] = prompt
        return "{}"

    read_with_llm("brief", reg,
                  {"data_residency": "may_leave", "hosting": "customer-vpc"},
                  complete=spy)
    assert '"hosting"' not in seen["prompt"]
    assert '"corpus_size"' in seen["prompt"]


def test_a_stated_answer_outranks_the_model(reg):
    """INFERRED is the weakest tier: a later interview answer replaces the
    model's guess without ceremony."""
    from fde.models.fact import Fact
    from fde.models.profile import Profile

    p = Profile()
    facts, _ = read_with_llm("brief", reg, {"data_residency": "may_leave"},
                             complete=lambda _: '{"hosting": "on-prem"}')
    p.ingest(facts)
    p.ingest([Fact("hosting", "hybrid", Provenance.INTERVIEW)])
    assert p.values()["hosting"] == "hybrid"


# --- the OpenAI-compatible local path, end to end ---------------------------


class _Server(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.dumps({"choices": [{"message": {"content": json.dumps(
            {"hosting": "on-prem", "corpus_size": 500000}
        )}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def test_frame_reader_llm_against_a_local_server(tmp_path, reg):
    server = HTTPServer(("127.0.0.1", 0), _Server)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        runner.invoke(app, ["start", "eng", "--base", str(tmp_path)])
        result = runner.invoke(app, [
            "frame", str(tmp_path / "eng"), "--registry", str(FRAMEWORK),
            "--text", "Extract fields from the archive.",
            "--reader", "llm",
            "--endpoint", f"http://127.0.0.1:{server.server_port}",
        ])
        assert result.exit_code == 0
        assert "The model also read" in result.output
        assert "hosting = on-prem" in result.output
        assert "weakest provenance" in result.output
    finally:
        server.shutdown()


def test_an_unreachable_local_server_leaves_the_deterministic_reading(tmp_path):
    runner.invoke(app, ["start", "eng", "--base", str(tmp_path)])
    result = runner.invoke(app, [
        "frame", str(tmp_path / "eng"), "--registry", str(FRAMEWORK),
        "--text", "500,000 documents in the archive.",
        "--reader", "llm", "--endpoint", "http://127.0.0.1:1",
    ])
    assert result.exit_code == 0
    assert "How many items in total: 500,000" in result.output
    assert "no model answered" in result.output
