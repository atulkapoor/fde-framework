import pytest

from tests.test_registry import CASE, LANGGRAPH, PATTERN, PLAIN, STACK, write


@pytest.fixture
def framework(tmp_path):
    write(tmp_path, "stacks", "pgvector", STACK)
    write(tmp_path, "stacks", "langgraph", LANGGRAPH)
    write(tmp_path, "stacks", "plain-python", PLAIN)
    write(tmp_path, "patterns", "supervisor-worker", PATTERN)
    write(tmp_path, "cases", "doc-extraction", CASE)
    return tmp_path
