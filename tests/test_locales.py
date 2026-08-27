"""Jurisdiction packs: presets and obligations, never new dimensions.

Geography changes what you must produce, not how you decide. A pack that
could add a dimension would be a jurisdiction rewriting the decision
engine, which is the exact thing the design forbids.
"""

from pathlib import Path

from typer.testing import CliRunner

from fde.cli import app
from fde.factlog import load_engagement
from fde.graph import validate_links
from fde.registry import load_registry

runner = CliRunner()
FRAMEWORK = Path(__file__).resolve().parents[1] / "framework"


def engagement(tmp_path):
    runner.invoke(app, ["start", "acme", "--base", str(tmp_path),
                        "--statement", "Extract fields from supplier invoices."])
    return tmp_path / "acme"


def test_the_shipped_packs_load_and_link(tmp_path):
    reg = load_registry(FRAMEWORK)
    assert {"eu-gdpr", "in-dpdp"} <= set(reg.locales)
    assert validate_links(reg) == []
    for locale in reg.locales.values():
        assert locale.as_of, f"{locale.id}: an undated obligation ages into a liability"
        for obligation in locale.obligations:
            assert obligation.produce


def test_a_pack_may_never_introduce_a_dimension(tmp_path):
    """The rule, enforced rather than hoped."""
    (tmp_path / "locales").mkdir(parents=True)
    (tmp_path / "dimensions").mkdir()
    (tmp_path / "dimensions" / "hosting.md").write_text(
        "---\nid: hosting\ntype: enum\nvalues: [on-prem, managed-api]\n---\nbody\n"
    )
    (tmp_path / "locales" / "atlantis.md").write_text(
        "---\nid: atlantis\nname: Atlantis\npresets:\n  sea_level: high\n---\nbody\n"
    )
    errors = validate_links(load_registry(tmp_path))
    assert any("may never introduce" in e.message for e in errors)


def test_a_preset_must_be_a_legal_value(tmp_path):
    (tmp_path / "locales").mkdir(parents=True)
    (tmp_path / "dimensions").mkdir()
    (tmp_path / "dimensions" / "hosting.md").write_text(
        "---\nid: hosting\ntype: enum\nvalues: [on-prem, managed-api]\n---\nbody\n"
    )
    (tmp_path / "locales" / "atlantis.md").write_text(
        "---\nid: atlantis\nname: Atlantis\npresets:\n  hosting: underwater\n---\nbody\n"
    )
    errors = validate_links(load_registry(tmp_path))
    assert any("underwater" in e.message for e in errors)


def test_presets_are_the_weakest_provenance(tmp_path):
    """Geography seeds answers; it never overrides people. A stated fact
    must beat a locale preset regardless of arrival order."""
    root = engagement(tmp_path)
    runner.invoke(app, ["locale", str(root), "eu-gdpr"])
    profile = load_engagement(root).profile
    assert profile.get("data_residency") == "cannot_leave"
    assert str(profile.fact("data_residency").provenance) == "inferred"

    runner.invoke(app, ["frame", str(root),
                        "--text", "Counsel confirms data may leave under SCCs."])
    profile = load_engagement(root).profile
    assert profile.get("data_residency") == "may_leave"


def test_an_unknown_pack_lists_the_real_ones(tmp_path):
    root = engagement(tmp_path)
    result = runner.invoke(app, ["locale", str(root), "mars"])
    assert result.exit_code == 1
    assert "eu-gdpr" in result.output


def test_the_build_carries_the_obligations(tmp_path):
    """The whole point: obligations attach to the deliverable, dated, with
    verification notes -- a checklist the engagement arrives with instead
    of discovers in procurement review."""
    import yaml

    root = engagement(tmp_path)
    runner.invoke(app, ["locale", str(root), "in-dpdp"])
    (tmp_path / "b.yaml").write_text(yaml.safe_dump({
        "volume": 1, "cycle_time_per_unit_seconds": 1, "labour_hours_per_week": 1,
        "rework_rate": 0, "exception_rate": 0, "error_rate": 0,
        "business_metric": "m", "sampled": True, "definitions_recorded": True,
    }))
    runner.invoke(app, ["baseline", str(root), "--file", str(tmp_path / "b.yaml")])
    runner.invoke(app, ["data-access", str(root), "--note", "rows returned"])
    runner.invoke(app, ["waive", str(root), "client_readiness", "--reason", "soon"])
    result = runner.invoke(app, ["build", str(root), "--out", str(tmp_path / "out")])
    assert result.exit_code == 0, result.output

    compliance = (tmp_path / "out" / "COMPLIANCE.md").read_text()
    assert "India (DPDP Act)" in compliance
    assert "erasure-path" in compliance
    assert "Verify:" in compliance
    assert "as of" in compliance.lower()


def test_no_locale_means_no_compliance_page(tmp_path):
    import yaml

    root = engagement(tmp_path)
    (tmp_path / "b.yaml").write_text(yaml.safe_dump({
        "volume": 1, "cycle_time_per_unit_seconds": 1, "labour_hours_per_week": 1,
        "rework_rate": 0, "exception_rate": 0, "error_rate": 0,
        "business_metric": "m", "sampled": True, "definitions_recorded": True,
    }))
    runner.invoke(app, ["baseline", str(root), "--file", str(tmp_path / "b.yaml")])
    runner.invoke(app, ["data-access", str(root), "--note", "rows returned"])
    runner.invoke(app, ["waive", str(root), "client_readiness", "--reason", "soon"])
    runner.invoke(app, ["build", str(root), "--out", str(tmp_path / "out")])
    assert not (tmp_path / "out" / "COMPLIANCE.md").exists()


def test_the_erasure_obligation_names_the_retention_tension(tmp_path):
    """G7's finding: retain the audit trail, erase the personal data --
    unmodeled tension is how engagements get surprised. Both shipped packs
    record the resolution shape."""
    reg = load_registry(FRAMEWORK)
    for locale_id in ("eu-gdpr", "in-dpdp"):
        erasure = next(o for o in reg.locales[locale_id].obligations
                       if o.id == "erasure-path")
        assert "audit" in erasure.produce.lower()
        assert "skeleton" in erasure.produce.lower()
