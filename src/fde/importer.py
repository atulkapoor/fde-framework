"""Client exports into pairs.

The pairs a build is exam'd on come out of a ticketing system, a CRM, a
spreadsheet -- as an export with the client's column names, not as the
`input`/`output` JSONL the intake reads. This maps one to the other and
reports what it did: rows read, rows kept, rows skipped for an empty
side, exact duplicates dropped, and how many are verified. Nothing is
verified because the file says so; a row is verified when the caller
names the column and value that means a person checked it, or attests
that every label was.

Live connectors to those systems are not here. An export is the interface
a client can hand over inside their own boundary, and it is the one that
can be tested without their credentials.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class ExportError(ValueError):
    """The export cannot be read as asked, with the reason."""


def read_rows(path: Path, delimiter: str | None = None) -> list[dict[str, Any]]:
    """Rows as dicts from .csv/.tsv (header row), .jsonl or .json (a list)."""
    path = Path(path)
    if not path.exists():
        raise ExportError(f"{path}: no such file")
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8-sig")
    if suffix == ".jsonl":
        rows = []
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError as exc:
                raise ExportError(f"{path}:{number}: not JSON -- {exc}") from exc
            if not isinstance(row, dict):
                raise ExportError(f"{path}:{number}: a line must be an object")
            rows.append(row)
        return rows
    if suffix == ".json":
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise ExportError(f"{path}: not JSON -- {exc}") from exc
        if isinstance(data, dict):
            for key in ("rows", "data", "items", "records"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
        if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
            raise ExportError(f"{path}: expected a list of objects")
        return data
    if suffix in (".csv", ".tsv", ".txt"):
        if delimiter is None:
            delimiter = "\t" if suffix == ".tsv" else ","
            sample = text[:4096]
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
            except csv.Error:
                pass
        reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
        if not reader.fieldnames:
            raise ExportError(f"{path}: no header row")
        return [dict(row) for row in reader]
    raise ExportError(f"{path}: {suffix or 'no extension'} is not an export this reads "
                      "(.csv, .tsv, .jsonl, .json)")


def _cell(row: dict, column: str) -> Any:
    value = row.get(column)
    if isinstance(value, str):
        return value.strip()
    return value


def _empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value)


def to_pairs(rows: list[dict[str, Any]], *, input_cols: list[str], output_cols: list[str],
             id_col: str | None = None, verified_when: str | None = None,
             all_verified: bool = False, output_text: bool = False,
             ) -> tuple[list[dict], dict[str, Any]]:
    """Map rows to pairs. One input column becomes a string input, several a
    dict keyed by column; output columns always become a dict keyed by
    column unless `output_text` asks for the single column as prose."""
    if not rows:
        raise ExportError("the export has no rows")
    columns = set(rows[0])
    wanted = list(input_cols) + list(output_cols) + ([id_col] if id_col else [])
    if verified_when:
        if "=" not in verified_when:
            raise ExportError("--verified-when takes column=value")
        wanted.append(verified_when.split("=", 1)[0])
    missing = [c for c in wanted if c not in columns]
    if missing:
        raise ExportError(f"columns not in the export: {', '.join(missing)}; "
                          f"it has: {', '.join(sorted(columns))}")
    if output_text and len(output_cols) != 1:
        raise ExportError("--output-text needs exactly one output column")
    verified_col, verified_val = (verified_when.split("=", 1) if verified_when
                                  else (None, None))
    pairs: list[dict] = []
    seen_inputs: set[str] = set()
    report = {"rows": len(rows), "kept": 0, "skipped_empty": 0, "duplicates": 0,
              "verified": 0}
    for number, row in enumerate(rows, 1):
        inputs = {c: _cell(row, c) for c in input_cols}
        outputs = {c: _cell(row, c) for c in output_cols}
        if any(_empty(v) for v in inputs.values()) or any(_empty(v) for v in outputs.values()):
            report["skipped_empty"] += 1
            continue
        input_value: Any = inputs[input_cols[0]] if len(input_cols) == 1 else inputs
        key = json.dumps(input_value, sort_keys=True)
        if key in seen_inputs:
            report["duplicates"] += 1
            continue
        seen_inputs.add(key)
        output_value: Any = outputs[output_cols[0]] if output_text else outputs
        if all_verified:
            verified = True
        elif verified_col is not None:
            verified = str(_cell(row, verified_col)) == verified_val
        else:
            verified = False
        identifier = str(_cell(row, id_col)) if id_col and not _empty(_cell(row, id_col)) \
            else f"row-{number:05d}"
        pairs.append({"id": identifier, "input": input_value, "output": output_value,
                      "verified": verified})
        report["kept"] += 1
        report["verified"] += int(verified)
    if not pairs:
        raise ExportError("no row had both an input and an output")
    return pairs, report


def write_pairs(pairs: list[dict], out: Path) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pairs))
    return out
