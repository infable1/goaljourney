"""Human reviews of revision-ledger entries (`gj revisions review`, schema 0.1.2 `review` block)."""
import copy
import shutil

import pytest

from gjcore import schemas
from gjcore.io import load_yaml
from generation.pipelines import review_store, revisions

LEDGER = revisions.load_ledger("0.1.1")
HASH = "0" * 64


def _all_pending(ledger):
    """A copy of the ledger with every entry back at pending_human_review, independent of recorded decisions."""
    out = copy.deepcopy(ledger)
    for e in out["revisions"]:
        e["reviewer_status"] = "pending_human_review"
        e.pop("review", None)
    return out


PENDING = _all_pending(LEDGER)


@pytest.fixture
def ledger_copy(tmp_path, monkeypatch):
    """Point the ledger at a temporary all-pending copy, so tests never touch the committed file."""
    path = tmp_path / "v0.1.1.yaml"
    shutil.copy(revisions.ledger_path("0.1.1"), path)
    monkeypatch.setattr(revisions, "ledger_path", lambda version=None: path)
    revisions._write(copy.deepcopy(PENDING))
    assert load_yaml(path) == PENDING
    return path


def _entry(ledger, rev_id):
    return next(e for e in ledger["revisions"] if e["id"] == rev_id)


def _review(content_hash, **kw):
    return {"reviewer_id": "po-reviewer", "timestamp": "2026-09-30T12:00:00Z", "content_hash": content_hash,
            "independent_rating": True, "notes": "ok", **kw}


def test_schema_ties_review_block_to_reviewer_status():
    pending = copy.deepcopy(PENDING)
    e = pending["revisions"][0]
    assert e["reviewer_status"] == "pending_human_review" and "review" not in e
    assert schemas.validate("revision_ledger", pending) == []

    e["review"] = _review(e["content_hash"])
    assert schemas.validate("revision_ledger", pending), "a pending entry must not carry a review"

    decided = copy.deepcopy(PENDING)
    decided["revisions"][0]["reviewer_status"] = "confirmed"
    assert schemas.validate("revision_ledger", decided), "a confirmed entry needs its review block"
    decided["revisions"][0]["review"] = _review(decided["revisions"][0]["content_hash"])
    assert schemas.validate("revision_ledger", decided) == []
    del decided["revisions"][0]["review"]["independent_rating"]
    assert schemas.validate("revision_ledger", decided), "independent_rating is required"


def test_the_review_block_needs_schema_0_1_2():
    decided = copy.deepcopy(PENDING)
    decided["revisions"][0]["reviewer_status"] = "disputed"
    decided["revisions"][0]["review"] = _review(decided["revisions"][0]["content_hash"])
    assert schemas.validate("revision_ledger", decided) == []
    assert schemas.validate("revision_ledger", decided, version="0.1.1"), "schema 0.1.1 has no review block"


def test_record_review_binds_the_decision_to_the_entry_hash(ledger_copy):
    before = load_yaml(ledger_copy)
    e = revisions.record_review("REV-0.1.1-002", "po-reviewer", "disputed", "  Оспорено: причина.  ", False,
                                version="0.1.1", timestamp="2026-09-30T12:00:00Z")
    after = load_yaml(ledger_copy)
    got = _entry(after, "REV-0.1.1-002")
    assert got == e
    assert got["reviewer_status"] == "disputed"
    assert got["review"] == {"reviewer_id": "po-reviewer", "timestamp": "2026-09-30T12:00:00Z",
                             "content_hash": _entry(before, "REV-0.1.1-002")["content_hash"],
                             "independent_rating": False, "notes": "Оспорено: причина."}
    keys = list(got)
    assert keys[keys.index("reviewer_status") + 1] == "review"
    # every other entry and every authored or computed field is unchanged
    for old, new in zip(before["revisions"], after["revisions"]):
        if old["id"] != "REV-0.1.1-002":
            assert old == new
        else:
            assert {k: v for k, v in new.items() if k not in ("reviewer_status", "review")} == \
                   {k: v for k, v in old.items() if k != "reviewer_status"}
    assert {k: v for k, v in after.items() if k != "revisions"} == {k: v for k, v in before.items() if k != "revisions"}
    errors, summary = revisions.check("0.1.1")
    assert errors == []
    assert summary["reviewer_status"]["disputed"] == 1


def test_record_review_refuses_what_a_human_decision_needs(ledger_copy, monkeypatch):
    with pytest.raises(revisions.RevisionError, match="unknown reviewer"):
        revisions.record_review("REV-0.1.1-001", "nobody", "confirmed", "x", True, version="0.1.1")
    with pytest.raises(revisions.RevisionError, match="status must be"):
        revisions.record_review("REV-0.1.1-001", "po-reviewer", "approved", "x", True, version="0.1.1")
    with pytest.raises(revisions.RevisionError, match="notes are required"):
        revisions.record_review("REV-0.1.1-001", "po-reviewer", "confirmed", "  ", True, version="0.1.1")
    with pytest.raises(revisions.RevisionError, match="independent_rating"):
        revisions.record_review("REV-0.1.1-001", "po-reviewer", "confirmed", "x", None, version="0.1.1")
    with pytest.raises(revisions.RevisionError, match="no ledger entry"):
        revisions.record_review("REV-0.1.1-999", "po-reviewer", "confirmed", "x", True, version="0.1.1")

    real = review_store.load_registry()
    bot = dict(real["po-reviewer"], id="bot", human=False)
    monkeypatch.setattr(review_store, "load_registry", lambda path=None: {**real, "bot": bot})
    with pytest.raises(revisions.RevisionError, match="not marked human"):
        revisions.record_review("REV-0.1.1-001", "bot", "confirmed", "x", True, version="0.1.1")
    assert load_yaml(ledger_copy) == PENDING, "a refused review writes nothing"


def test_a_second_review_needs_replace(ledger_copy):
    revisions.record_review("REV-0.1.1-001", "po-reviewer", "confirmed", "first", True, version="0.1.1")
    with pytest.raises(revisions.RevisionError, match="already has a review"):
        revisions.record_review("REV-0.1.1-001", "po-reviewer", "disputed", "second", False, version="0.1.1")
    e = revisions.record_review("REV-0.1.1-001", "po-reviewer", "disputed", "second", False, version="0.1.1",
                                replace=True)
    assert e["reviewer_status"] == "disputed" and e["review"]["notes"] == "second"
    assert revisions.check("0.1.1")[0] == []


def test_check_rejects_a_stale_or_unregistered_review(ledger_copy):
    revisions.record_review("REV-0.1.1-001", "po-reviewer", "confirmed", "ok", True, version="0.1.1")
    text = ledger_copy.read_text(encoding="utf-8")
    current = _entry(load_yaml(ledger_copy), "REV-0.1.1-001")["content_hash"]
    ledger_copy.write_text(text.replace(f"content_hash: {current}\n    independent_rating",
                                        f"content_hash: {HASH}\n    independent_rating", 1), encoding="utf-8")
    errors = revisions.check("0.1.1")[0]
    assert any("REV-0.1.1-001" in e and "record a new review" in e for e in errors), errors

    ledger_copy.write_text(text.replace("reviewer_id: po-reviewer", "reviewer_id: someone-else", 1), encoding="utf-8")
    errors = revisions.check("0.1.1")[0]
    assert any("not a registered human reviewer" in e for e in errors), errors


def test_committed_ledger_reviews_are_bound_and_registered():
    errors, _ = revisions.check("0.1.1")
    assert errors == []
    registry = review_store.load_registry()
    for e in LEDGER["revisions"]:
        if e["reviewer_status"] == "pending_human_review":
            assert "review" not in e
        else:
            assert e["review"]["content_hash"] == e["content_hash"]
            assert registry[e["review"]["reviewer_id"]]["human"]
