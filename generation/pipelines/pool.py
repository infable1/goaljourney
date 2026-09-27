"""The example pool = authored examples (data/raw/examples) + generated candidates
(data/generated/<run_id>/candidates.jsonl), with review status resolved from the review log."""
from gjcore.config import load_config
from gjcore.io import read_jsonl
from gjcore.paths import repo_path
from gjcore.records import load_examples


def load_pool(include_generated=True):
    """Return [(record, source_path, origin)] where origin is 'authored' or 'generated'."""
    cfg = load_config("dataset")["paths"]
    pool = [(r, p, "authored") for r, p in load_examples(repo_path(cfg["raw_examples"]))]
    if include_generated:
        gen_dir = repo_path(cfg["generated"])
        for path in sorted(gen_dir.glob("*/candidates.jsonl")):
            pool += [(r, path, "generated") for r in read_jsonl(path)]
    return pool


def load_review_events():
    from .review_store import ReviewStore
    return ReviewStore.default().events()


def review_status(record, events=None) -> str:
    """pending | stale | approved | approved_pending_expert | needs_revision | rejected
    (see generation/pipelines/review_store.py). Only `approved` is eligible for training."""
    from .review_store import resolve
    return resolve(record, load_review_events() if events is None else events)["status"]
