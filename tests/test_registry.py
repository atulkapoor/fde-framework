"""Loading `framework/` into a validated, cross-linked registry.

A registry error found at 3am on a client site must name the file and the field.
Anything less means reading the loader to understand your own typo.
"""

import pytest

from fde.graph import find_gaps, validate_links
from fde.registry import RegistryError, load_registry

STACK = """\
---
id: pgvector
name: pgvector
licence: PostgreSQL
topologies: [customer-vpc, on-prem, air-gapped]
last_verified: 2026-08-21
provides: {vector_search: stable}
---
Postgres extension. Iterative index scans since 0.8.0.
"""

PATTERN = """\
---
id: supervisor-worker
component: orchestration
realizations:
  - {stack: langgraph, template: sup/lg.py.j2, provides: Supervisor}
  - {stack: plain-python, template: sup/plain.py.j2, provides: Supervisor}
evidence:
  case_ids: [doc-extraction]
---
A supervisor routes to workers and owns the boundary.
"""

LANGGRAPH = """\
---
id: langgraph
name: LangGraph
licence: MIT
topologies: [managed, customer-vpc, on-prem, air-gapped]
last_verified: 2026-08-21
provides: {graph_execution: stable}
---
Graph execution with checkpointing.
"""

# "No framework at all" is a stack like any other. Modelling it this way is what
# lets the decision engine recommend restraint on the same footing as a library.
PLAIN = """\
---
id: plain-python
name: No framework
licence: PSF
topologies: [managed, customer-vpc, on-prem, air-gapped, hybrid]
last_verified: 2026-08-21
---
Functions and a loop. The default until something earns more.
"""

CASE = """\
---
id: doc-extraction
sanitization: reviewed
---
Structured extraction from varied layouts.
"""


def write(root, kind, name, body):
    d = root / kind
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.md").write_text(body)


@pytest.fixture
def framework(tmp_path):
    write(tmp_path, "stacks", "pgvector", STACK)
    write(tmp_path, "stacks", "langgraph", LANGGRAPH)
    write(tmp_path, "stacks", "plain-python", PLAIN)
    write(tmp_path, "patterns", "supervisor-worker", PATTERN)
    write(tmp_path, "cases", "doc-extraction", CASE)
    return tmp_path


# --- loading -------------------------------------------------------------


def test_loads_typed_entries(framework):
    reg = load_registry(framework)
    assert reg.stacks["pgvector"].licence == "PostgreSQL"
    assert reg.patterns["supervisor-worker"].component == "orchestration"


def test_body_text_is_kept_not_discarded(framework):
    """The prose under the front matter is the rationale a human reads."""
    assert "Iterative index scans" in reg_body(load_registry(framework), "stacks", "pgvector")


def reg_body(reg, kind, entry_id):
    return reg.bodies[(kind, entry_id)]


def test_an_empty_registry_loads_rather_than_crashing(tmp_path):
    assert load_registry(tmp_path).stacks == {}


def test_nested_directories_are_walked(tmp_path):
    write(tmp_path, "patterns/orchestration", "supervisor-worker", PATTERN)
    write(tmp_path, "stacks", "pgvector", STACK)
    write(tmp_path, "stacks", "langgraph", LANGGRAPH)
    write(tmp_path, "stacks", "plain-python", PLAIN)
    write(tmp_path, "cases", "doc-extraction", CASE)
    assert "supervisor-worker" in load_registry(tmp_path).patterns


def test_unknown_top_level_directory_is_reported_not_ignored(tmp_path):
    """A typo'd directory name silently loading nothing is how content goes missing."""
    write(tmp_path, "stackz", "pgvector", STACK)
    with pytest.raises(RegistryError, match="stackz"):
        load_registry(tmp_path)


# --- error quality -------------------------------------------------------


def test_validation_error_names_the_file(tmp_path):
    write(tmp_path, "stacks", "broken", "---\nid: broken\n---\n")
    with pytest.raises(RegistryError) as e:
        load_registry(tmp_path)
    assert "broken.md" in str(e.value)


def test_validation_error_names_the_missing_field(tmp_path):
    write(tmp_path, "stacks", "broken", "---\nid: broken\nname: X\n---\n")
    with pytest.raises(RegistryError) as e:
        load_registry(tmp_path)
    assert "licence" in str(e.value)


def test_a_file_whose_id_disagrees_with_its_name_is_rejected(tmp_path):
    """Silent drift between filename and id makes cross-links unfindable."""
    write(tmp_path, "stacks", "postgres", STACK)  # id inside is pgvector
    with pytest.raises(RegistryError, match="filename"):
        load_registry(tmp_path)


def test_duplicate_ids_across_files_are_rejected(tmp_path):
    write(tmp_path, "stacks", "pgvector", STACK)
    write(tmp_path, "stacks/legacy", "pgvector", STACK)
    with pytest.raises(RegistryError, match="duplicate"):
        load_registry(tmp_path)


def test_a_file_with_no_front_matter_is_reported(tmp_path):
    write(tmp_path, "stacks", "prose", "Just some prose, no front matter.\n")
    with pytest.raises(RegistryError, match="front matter"):
        load_registry(tmp_path)


# --- cross-links ---------------------------------------------------------


def test_a_clean_registry_has_no_link_errors(framework):
    assert validate_links(load_registry(framework)) == []


def test_evidence_pointing_at_a_missing_case_is_an_error(tmp_path):
    write(tmp_path, "stacks", "pgvector", STACK)
    write(tmp_path, "patterns", "supervisor-worker", PATTERN)  # cites doc-extraction
    errs = validate_links(load_registry(tmp_path))
    assert any("doc-extraction" in e.message for e in errs)


def test_a_realization_naming_an_unknown_stack_is_an_error(tmp_path):
    write(tmp_path, "cases", "doc-extraction", CASE)
    write(tmp_path, "patterns", "supervisor-worker", PATTERN)  # cites langgraph
    errs = validate_links(load_registry(tmp_path))
    assert any("langgraph" in e.message for e in errs)


def test_link_errors_name_the_file_that_holds_the_bad_reference(tmp_path):
    write(tmp_path, "cases", "doc-extraction", CASE)
    write(tmp_path, "patterns", "supervisor-worker", PATTERN)
    errs = validate_links(load_registry(tmp_path))
    assert errs and "supervisor-worker" in errs[0].source


# --- gaps ----------------------------------------------------------------


def test_a_pattern_without_evidence_is_reported_as_a_gap(tmp_path):
    write(tmp_path, "stacks", "pgvector", STACK)
    write(
        tmp_path,
        "patterns",
        "bare",
        "---\nid: bare\ncomponent: retrieval\n"
        "realizations: [{stack: plain-python, template: a.j2, provides: Retriever}]\n---\n",
    )
    gaps = find_gaps(load_registry(tmp_path))
    assert any(g.kind == "pattern_without_evidence" for g in gaps)


def test_a_stale_stack_is_reported_as_a_gap(framework):
    """Tools churn in months. A stack nobody has checked in a year is a liability."""
    gaps = find_gaps(load_registry(framework), today="2027-10-01")
    assert any(g.kind == "stale_stack" and "pgvector" in g.detail for g in gaps)


def test_a_fresh_stack_is_not_reported_as_stale(framework):
    gaps = find_gaps(load_registry(framework), today="2026-08-22")
    assert not any(g.kind == "stale_stack" for g in gaps)
