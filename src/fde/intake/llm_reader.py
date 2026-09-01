"""A model reads the brief -- as a proposer, never an authority.

The deterministic reader runs first and its facts stand. The model is asked
only about the dimensions still unresolved, its answers are validated against
the registry's own declared types and values, and everything it proposes lands
at INFERRED -- the weakest provenance, below every stated answer -- until a
person confirms the playback.

The registry is the schema. Every dimension added to the corpus automatically
extends what the model is asked for; the recognisers stay as the offline
fallback and as the oracle the tests pin.

And the framework's own boundary doctrine governs its own intake: a brief is
client data, so a hosted model is refused unless the engagement has *stated*
that data may leave. Unknown is not permission. A local endpoint -- something
listening on this machine -- is always allowed, because the data goes nowhere.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

from fde.models.base import Provenance
from fde.models.fact import Fact
from fde.models.schema import ValueType
from fde.registry import Registry

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}  # noqa: S104

# The hosted default. Extraction against a tight schema is exactly the work a
# small fast model does well; anything larger is spend without signal.
HOSTED_MODEL = "claude-haiku-4-5-20251001"


class BoundaryRefusal(RuntimeError):
    """The brief may not be sent where the flag points."""


class ReaderUnavailable(RuntimeError):
    """No model could be reached; the deterministic reading stands alone."""


def is_local(endpoint: str | None) -> bool:
    if not endpoint:
        return False
    host = urlparse(endpoint).hostname or ""
    return host in LOCAL_HOSTS


def check_boundary(values: dict[str, Any], registry: Registry,
                   endpoint: str | None) -> None:
    """Hosted models need stated permission; local ones need none.

    The values checked include what the deterministic reader just took from
    this same brief -- so a brief that itself says "data cannot leave" refuses
    its own upload, which is exactly the behaviour a client would expect from
    a tool wearing this framework's opinions.
    """
    if is_local(endpoint):
        return
    residency = values.get("data_residency")
    if residency == "may_leave":
        return
    inside = any(
        values.get(dimension) in entry.boundary_when
        for dimension, entry in registry.dimensions.items()
        if entry.boundary_when
    )
    why = (
        "this brief says data may not leave"
        if residency is not None or inside
        else "nothing states that data may leave, and unknown is not permission"
    )
    raise BoundaryRefusal(
        f"refusing to send the brief to a hosted model: {why}. "
        f"Point --endpoint at a local model (vLLM or Ollama on this machine) "
        f"or record data_residency = may_leave first."
    )


def extraction_schema(registry: Registry, unresolved: list[str]) -> dict[str, Any]:
    """A JSON schema for exactly the dimensions still worth asking about."""
    properties: dict[str, Any] = {}
    for name in unresolved:
        entry = registry.dimensions[name]
        if entry.type is ValueType.ENUM:
            spec: dict[str, Any] = {"type": "string", "enum": list(entry.values)}
        elif entry.type is ValueType.BOOLEAN:
            spec = {"type": "boolean"}
        elif entry.type in (ValueType.COUNT, ValueType.DURATION_MS, ValueType.MONEY):
            spec = {"type": "integer", "minimum": 0}
        elif entry.type is ValueType.RATIO:
            spec = {"type": "number", "minimum": 0, "maximum": 1}
        else:
            spec = {"type": "string"}
        spec["description"] = entry.asks or name
        properties[name] = spec
    return {"type": "object", "properties": properties, "additionalProperties": False}


def _prompt(text: str, schema: dict[str, Any]) -> str:
    return (
        "Read this engagement brief. Extract a value for a field ONLY when the "
        "brief states it -- never infer, never assume a default, and omit every "
        "field the brief does not answer. Durations are in milliseconds.\n\n"
        f"Fields, as JSON schema:\n{json.dumps(schema, indent=1)}\n\n"
        f"Brief:\n{text}\n\n"
        "Reply with a single JSON object and nothing else."
    )


def _complete_local(endpoint: str, model: str, prompt: str) -> str:
    """One chat completion against an OpenAI-compatible local server.

    vLLM and Ollama both speak this shape on localhost; stdlib only, because
    the offline path must not grow a dependency.
    """
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }).encode()
    request = urllib.request.Request(  # noqa: S310 - localhost only, checked by caller
        endpoint.rstrip("/") + "/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ReaderUnavailable(
            f"no model answered at {endpoint}: {exc}. The deterministic "
            f"reading above stands; start the local server and re-run, or "
            f"drop --reader llm."
        ) from exc
    return payload["choices"][0]["message"]["content"]


def _complete_hosted(model: str, prompt: str) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise ReaderUnavailable(
            "the hosted path needs the anthropic package -- "
            'pip install "fde-framework[llm]" -- or point --endpoint at a '
            "local model instead."
        ) from exc
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(
        block.text for block in response.content if block.type == "text"
    )


def _parse_reply(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.index("{"):] if "{" in text else text
    if "{" in text:
        text = text[text.index("{"): text.rindex("}") + 1]
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _validated(registry: Registry, proposals: dict[str, Any],
               unresolved: set[str]) -> tuple[list[tuple[str, Any]], list[str]]:
    """Keep what the registry itself would accept; name what it would not."""
    kept: list[tuple[str, Any]] = []
    dropped: list[str] = []
    for name, value in proposals.items():
        entry = registry.dimensions.get(name)
        if entry is None or name not in unresolved:
            dropped.append(f"{name} (not asked)")
            continue
        if entry.type is ValueType.ENUM:
            if value in entry.values:
                kept.append((name, value))
            else:
                dropped.append(f"{name}={value!r} (not a declared value)")
        elif entry.type is ValueType.BOOLEAN:
            if isinstance(value, bool):
                kept.append((name, value))
            else:
                dropped.append(f"{name}={value!r} (not a boolean)")
        elif entry.type in (ValueType.COUNT, ValueType.DURATION_MS, ValueType.MONEY):
            if isinstance(value, (int, float)) and not isinstance(value, bool) \
                    and value >= 0:
                kept.append((name, int(value)))
            else:
                dropped.append(f"{name}={value!r} (not a count)")
        elif entry.type is ValueType.RATIO:
            if isinstance(value, (int, float)) and not isinstance(value, bool) \
                    and 0 <= value <= 1:
                kept.append((name, float(value)))
            else:
                dropped.append(f"{name}={value!r} (not a 0..1 ratio)")
        else:
            kept.append((name, str(value)))
    return kept, dropped


def read_with_llm(
    text: str,
    registry: Registry,
    already: dict[str, Any],
    endpoint: str | None = None,
    model: str | None = None,
    source: str | None = None,
    complete=None,
) -> tuple[list[Fact], list[str]]:
    """Model-read facts for the dimensions the deterministic pass left open.

    Returns (facts, dropped): every fact at INFERRED strength, and every
    proposal the registry refused, so the caller can say both out loud.
    `complete` is injectable for tests; nothing here requires a network to be
    exercised.
    """
    check_boundary(already, registry, endpoint)

    unresolved = sorted(
        name for name, entry in registry.dimensions.items()
        if entry.weight > 0 and name not in already
    )
    if not unresolved:
        return [], []

    schema = extraction_schema(registry, unresolved)
    prompt = _prompt(text, schema)
    if complete is not None:
        raw = complete(prompt)
    elif endpoint:
        raw = _complete_local(endpoint, model or "default", prompt)
    else:
        raw = _complete_hosted(model or HOSTED_MODEL, prompt)

    kept, dropped = _validated(registry, _parse_reply(raw), set(unresolved))
    label = f"llm reader ({model or (endpoint and 'local') or HOSTED_MODEL})"
    facts = [
        Fact(name, value, Provenance.INFERRED,
             kind=registry.dimensions[name].kind,
             source=source or label)
        for name, value in kept
    ]
    return facts, dropped


def suggest_recognisers(
    text: str,
    registry: Registry,
    endpoint: str | None = None,
    model: str | None = None,
    complete=None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """The vocabulary treadmill, automated: what the model reads that the
    deterministic reader missed, as recogniser candidates.

    Three battery rounds taught the same lesson by hand -- "photos" was not
    an image workload, "the customer VPC" was nobody's hosting -- and every
    round was a person diffing model-grade reading against the vocabulary.
    This runs that diff. The output is a proposal, never an edit: each
    candidate names its dimension, its declared value, the phrase, and the
    evidence sentence, and a human puts it in the corpus with a test or
    does not.
    """
    from fde.intake.prose import parse_prose

    if complete is None:
        # The brief is the data being mined; the boundary rule is the same
        # as the reader's, with no profile to consult: unknown, so refused
        # for hosted models, always allowed for a local endpoint.
        check_boundary({}, registry, endpoint)

    deterministic = {f.dimension for f in parse_prose(text, registry)}
    unresolved = sorted(
        name for name, entry in registry.dimensions.items()
        if entry.weight > 0 and name not in deterministic
        and (entry.recognises or entry.type is ValueType.ENUM)
    )
    if not unresolved:
        return [], []

    schema = extraction_schema(registry, unresolved)
    prompt = (
        "Read this text. For each field, extract a value ONLY when the text "
        "states it, and quote the EXACT phrase (verbatim substring of the "
        "text) that states it. Omit everything unstated.\n\n"
        f"Fields, as JSON schema:\n{json.dumps(schema, indent=1)}\n\n"
        f"Text:\n{text}\n\n"
        'Reply with a single JSON object mapping field name to '
        '{"value": ..., "phrase": "..."} and nothing else.'
    )
    if complete is not None:
        raw = complete(prompt)
    elif endpoint:
        raw = _complete_local(endpoint, model or "default", prompt)
    else:
        raw = _complete_hosted(model or HOSTED_MODEL, prompt)

    lowered = text.lower()
    suggestions, dropped = [], []
    for name, entry in _parse_reply(raw).items():
        dimension = registry.dimensions.get(name)
        if dimension is None or name not in unresolved:
            dropped.append(f"{name} (not asked)")
            continue
        if not isinstance(entry, dict):
            dropped.append(f"{name} (malformed reply)")
            continue
        value, phrase = entry.get("value"), str(entry.get("phrase") or "")
        if dimension.type is ValueType.ENUM and value not in dimension.values:
            dropped.append(f"{name}={value!r} (not a declared value)")
            continue
        if not phrase or phrase.lower() not in lowered:
            # A phrase the text does not contain is a hallucinated citation.
            dropped.append(f"{name} (phrase not found verbatim in the text)")
            continue
        suggestions.append({
            "dimension": name,
            "value": str(value),
            "phrase": phrase.lower(),
            "evidence": phrase,
        })
    return suggestions, dropped
