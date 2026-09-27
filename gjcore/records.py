"""Loading dataset records and computing their content hashes.

Raw examples are authored as YAML files under data/raw/examples/, each holding a top-level
`examples:` list. Evaluation cases live under evaluation/cases/v<ver>/ with a `cases:` list.
"""
from pathlib import Path

import yaml

from .io import canonical_json, load_yaml, read_jsonl, sha256_text


class RecordFileError(ValueError):
    """A dataset file could not be parsed; the message names the file and position."""

# Fields that make up the trainable content of an example. Metadata edits (tags, notes)
# do not invalidate a review; edits to these fields do.
HASHED_FIELDS = ("task_type", "input", "expected_output", "contrastive")


def content_hash(record: dict) -> str:
    return sha256_text(canonical_json({k: record.get(k) for k in HASHED_FIELDS}))


def _load_list_file(path: Path, key: str):
    if path.suffix == ".jsonl":
        return read_jsonl(path)
    try:
        data = load_yaml(path)
    except yaml.YAMLError as e:
        raise RecordFileError(f"{path}: YAML parse error: {e}") from None
    if data is None:
        return []
    if not isinstance(data, dict) or key not in data or not isinstance(data[key], list):
        raise ValueError(f"{path}: expected a top-level '{key}:' list")
    return data[key]


def load_records(directory, key: str):
    """Return [(record, source_path)] for every *.yaml / *.yml / *.jsonl file under directory."""
    directory = Path(directory)
    out = []
    files = sorted(p for p in directory.rglob("*") if p.suffix in {".yaml", ".yml", ".jsonl"})
    for path in files:
        for rec in _load_list_file(path, key):
            out.append((rec, path))
    return out


def load_examples(directory):
    return load_records(directory, "examples")


def load_eval_cases(directory):
    return load_records(directory, "cases")


# ---- YAML authoring guard ---------------------------------------------------------------
# In YAML flow collections ("[a, b]" / "{k: v}") a comma always separates items and "?" is an
# indicator, so natural-language text with commas is silently split into several items. This
# guard flags prose that looks mis-split; the fix is to quote the item or use a block list.

import re as _re

_FLOW_SEQ = _re.compile(r":\s*\[([^\[\]{}]*)\]\s*$")
_FLOW_MAP = _re.compile(r"^\s*-?\s*\{(.*)\}\s*$")


def _suspicious_seq_items(content: str):
    if '"' in content or "'" in content:
        return []
    items = [i.strip() for i in content.split(",")]
    bad = []
    for n, item in enumerate(items):
        if "?" in item or ": " in item:
            bad.append(item)
        elif n > 0 and " " in item and item[:1].islower():
            bad.append(item)
        elif n > 0 and item[:1].isdigit() and items[n - 1][-1:].isdigit():
            bad.append(items[n - 1] + "," + item)
    return bad


def flow_style_issues(path):
    """Return [(line_no, message)] for flow collections whose prose was probably mis-split."""
    issues = []
    for no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        m = _FLOW_SEQ.search(line)
        if m and not _FLOW_MAP.match(line):
            bad = _suspicious_seq_items(m.group(1))
            if bad:
                issues.append((no, f"prose in a flow list looks mis-split near {bad[0]!r}; quote items or use a block list"))
            continue
        fm = _FLOW_MAP.match(line)
        if fm:
            body = _re.sub(r"\"[^\"]*\"|'[^']*'", "X", fm.group(1))
            prev = None
            while prev != body:  # collapse nested collections from the inside out
                prev, body = body, _re.sub(r"\[[^\[\]]*\]|\{[^{}]*\}", "X", body)
            for part in body.split(","):
                if part.strip() and ":" not in part:
                    issues.append((no, f"flow mapping item without a key near {part.strip()!r}; quote the value"))
                    break
            for seq in _re.findall(r"\[([^\[\]]*)\]", fm.group(1)):
                bad = _suspicious_seq_items(seq)
                if bad:
                    issues.append((no, f"prose in a flow list looks mis-split near {bad[0]!r}; quote items"))
    return issues
