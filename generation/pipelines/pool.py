"""The example pool = authored examples (data/raw/examples) + generated candidates
(data/generated/<run_id>/candidates.jsonl), with review status resolved from the review log."""
from gjcore.config import load_config
from gjcore.io import read_jsonl
from gjcore.paths import repo_path
from gjcore.records import content_hash, load_examples


def load_pool(include_generated=True):
    """Return [(record, source_path, origin)] where origin is 'authored' or 'generated'."""
    cfg = load_config("dataset")["paths"]
    pool = [(r, p, "authored") for r, p in load_examples(repo_path(cfg["raw_examples"]))]
    if include_generated:
        gen_dir = repo_path(cfg["generated"])
        for path in sorted(gen_dir.glob("*/candidates.jsonl")):
            pool += [(r, path, "generated") for r in read_jsonl(path)]
    return pool


def load_review_log():
    path = repo_path(load_config("dataset")["paths"]["review_log"])
    return read_jsonl(path) if path.exists() else []


def review_status(record, log=None) -> str:
    """pending | approved | rejected | needs_revision | stale (reviewed, but content changed since)."""
    log = load_review_log() if log is None else log
    h = content_hash(record)
    entries = [e for e in log if e.get("example_id") == record.get("id")]
    if not entries:
        return "pending"
    matching = [e for e in entries if e.get("content_hash") == h]
    if not matching:
        return "stale"
    return matching[-1]["decision"]
