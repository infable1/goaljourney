"""Review log v0.2: decisions, qualifications, tiers, status resolution, integrity, agreement."""
import copy
import json

import pytest

from gjcore.records import content_hash
from generation.pipelines import review, review_store as RS
from generation.pipelines.pool import load_pool

POOL = {r["id"]: r for r, _, _ in load_pool()}
RUBRIC = RS.load_rubric()


def _reviewer(rid, langs=("en", "ru"), roles=("dataset_reviewer",), domains=(), human=True, active=True):
    return {"id": rid, "roles": list(roles), "languages": list(langs), "expert_domains": list(domains),
            "human": human, "active": active}


@pytest.fixture
def store(tmp_path):
    return RS.ReviewStore(tmp_path / "events.jsonl", tmp_path / "snapshots")


@pytest.fixture
def registry():
    return {r["id"]: r for r in [
        _reviewer("alice"), _reviewer("bob"), _reviewer("en-only", langs=("en",)),
        _reviewer("dr-med", roles=("domain_expert",), domains=("medical",)),
        _reviewer("lawyer", roles=("domain_expert",), domains=("legal",)),
        _reviewer("adj", roles=("adjudicator",)), _reviewer("bot", human=False), _reviewer("gone", active=False),
    ]}


def good(record):
    return {c: "good" for c in RS.applicable_criteria(RUBRIC, record)}


def approve(store, registry, rec, who, **kw):
    return RS.record_decision(store, registry, RUBRIC, rec, who, "approve", kw.pop("ratings", good(rec)),
                              kw.pop("overall", "excellent"), **kw)


def test_approval_resolves_and_preserves_snapshot(store, registry):
    rec = POOL["gj-safe-001"]
    assert RS.resolve(rec, store.events())["status"] == "pending"
    ev = approve(store, registry, rec, "alice")
    assert ev["old_status"] == "pending" and ev["new_status"] == "approved"
    assert RS.resolve(rec, store.events())["status"] == "approved"
    snap = store.load_snapshot(content_hash(rec))
    assert snap["expected_output"] == rec["expected_output"]
    assert store.verify() == ([], [])


def test_edit_after_review_makes_status_pending_content_changed_and_keeps_old_version(store, registry):
    rec = copy.deepcopy(POOL["gj-safe-001"])
    approve(store, registry, rec, "alice")
    old = content_hash(rec)
    rec["expected_output"]["message_to_user"] += " Edited."
    info = RS.resolve(rec, store.events())
    assert (info["status"], info["detail"]) == ("pending", "content_changed")
    assert store.load_snapshot(old)["expected_output"]["message_to_user"].endswith("Let's plan it.")


@pytest.mark.parametrize("ratings_patch,overall,fragment", [
    ({"safety": "minor_issues"}, "acceptable", "hard-gate"),
    ({"product_usefulness": "major_issues"}, "acceptable", "major issues"),
    ({}, "needs_revision", "overall"),
    ({"product_usefulness": "unacceptable"}, "excellent", "unacceptable"),
])
def test_inconsistent_approvals_are_refused(store, registry, ratings_patch, overall, fragment):
    rec = POOL["gj-safe-001"]
    with pytest.raises(RS.ReviewError, match=fragment):
        approve(store, registry, rec, "alice", ratings={**good(rec), **ratings_patch}, overall=overall)
    assert store.events() == []


def test_approval_needs_every_applicable_criterion(store, registry):
    rec = POOL["gj-route-001"]
    partial = dict(list(good(rec).items())[:3])
    with pytest.raises(RS.ReviewError, match="missing"):
        approve(store, registry, rec, "alice", ratings=partial)


def test_revise_and_reject_need_reasons(store, registry):
    rec = POOL["gj-nav-006"]
    with pytest.raises(RS.ReviewError, match="revise needs"):
        RS.record_decision(store, registry, RUBRIC, rec, "alice", "revise", {}, "needs_revision")
    with pytest.raises(RS.ReviewError, match="reject needs a note"):
        RS.record_decision(store, registry, RUBRIC, rec, "alice", "reject", {}, "incorrect")
    ev = RS.record_decision(store, registry, RUBRIC, rec, "alice", "revise", {"realism": "major_issues"}, "needs_revision",
                            issues=[{"criterion": "realism", "severity": "major", "description": "5 October 2026 is a Monday",
                                     "proposed_fix": "«в понедельник, 5-го»"}])
    assert ev["new_status"] == "needs_revision"


@pytest.mark.parametrize("who,fragment", [("nobody", "unknown reviewer"), ("bot", "not marked human"), ("gone", "inactive")])
def test_only_registered_active_humans_can_decide(store, registry, who, fragment):
    with pytest.raises(RS.ReviewError, match=fragment):
        approve(store, registry, POOL["gj-safe-001"], who)


def test_language_qualification(store, registry):
    assert RS.required_languages(POOL["gj-lang-001"]) == ["en", "ru"]      # mixed input needs both
    with pytest.raises(RS.ReviewError, match="needs a reviewer who reads"):
        approve(store, registry, POOL["gj-task-004"], "en-only")          # Russian example
    approve(store, registry, POOL["gj-safe-001"], "en-only")                # English example is fine


def test_expert_tier_needs_matching_expert(store, registry):
    rec = POOL["gj-safe-004"]                                               # chest pain -> medical
    assert RS.review_tier(rec) == "expert_review_required"
    assert RS.required_expert_domains(rec) == ["medical"]
    ev = approve(store, registry, rec, "alice")
    assert (ev["new_status"], ev["new_status_detail"]) == ("pending", "awaiting_expert")
    ev = approve(store, registry, rec, "lawyer")
    assert (ev["new_status"], ev["new_status_detail"]) == ("pending", "awaiting_expert")
    assert approve(store, registry, rec, "dr-med")["new_status"] == "approved"


def test_allowed_examples_in_sensitive_domains_stay_human_tier():
    assert RS.review_tier(POOL["gj-nav-002"]) == "human_review_required"   # finance domain, 'allowed'
    assert RS.review_tier(POOL["gj-web-001"]) == "human_review_required"   # legal_admin domain, 'allowed'


def test_most_conservative_decision_wins_until_adjudicated(store, registry):
    rec = POOL["gj-clar-004"]
    approve(store, registry, rec, "alice")
    RS.record_decision(store, registry, RUBRIC, rec, "bob", "revise", {}, "needs_revision", notes="question 2 is redundant")
    assert RS.resolve(rec, store.events())["status"] == "needs_revision"
    approve(store, registry, rec, "adj")
    assert RS.resolve(rec, store.events())["status"] == "approved"


def test_findings_must_be_acknowledged_before_approval(store, registry):
    rec = POOL["gj-nav-006"]
    ratings = {**good(rec)}
    with pytest.raises(RS.ReviewError, match="acknowledge"):
        approve(store, registry, rec, "alice", ratings=ratings, open_findings=["KI-001"])
    ev = approve(store, registry, rec, "alice", ratings=ratings, open_findings=["KI-001"], acknowledge=True)
    assert ev["acknowledged_findings"] == ["KI-001"]


def test_tampering_is_detected(store, registry):
    approve(store, registry, POOL["gj-safe-001"], "alice")
    approve(store, registry, POOL["gj-clar-004"], "alice")
    lines = store.events_path.read_text(encoding="utf-8").splitlines()
    edited = json.loads(lines[0])
    edited["notes"] = "changed later"
    store.events_path.write_text(json.dumps(edited, ensure_ascii=False) + "\n" + lines[1] + "\n", encoding="utf-8")
    errors, _ = store.verify()
    assert any("edited" in e for e in errors)
    store.events_path.write_text(lines[1] + "\n", encoding="utf-8")        # first event deleted
    errors, _ = store.verify()
    assert any("missing" in e for e in errors)


def test_cohen_kappa_and_agreement(store, registry):
    assert RS.cohen_kappa([1, 1, 0, 0], [1, 0, 0, 0]) == 0.5
    assert RS.cohen_kappa(["a", "a"], ["a", "a"]) == 1.0
    for rid in ("gj-safe-001", "gj-clar-004"):
        approve(store, registry, POOL[rid], "alice")
    approve(store, registry, POOL["gj-safe-001"], "bob")
    RS.record_decision(store, registry, RUBRIC, POOL["gj-clar-004"], "bob", "revise", {}, "needs_revision", notes="x")
    ag = RS.agreement(store.events())
    assert ag["items_with_2plus_reviewers"] == 2
    pair = ag["pairs"][0]
    assert pair["reviewers"] == ["alice", "bob"] and pair["items"] == 2 and pair["decision_agreement"] == 0.5


def test_registry_validation(tmp_path):
    p = tmp_path / "reviewers.yaml"
    p.write_text("reviewers:\n  - {id: Bad Id, roles: [dataset_reviewer], languages: [en], human: true}\n", encoding="utf-8")
    with pytest.raises(RS.ReviewError, match="must match"):
        RS.load_registry(p)
    p.write_text("reviewers:\n  - {id: ok-id, roles: [boss], languages: [en], human: true}\n", encoding="utf-8")
    with pytest.raises(RS.ReviewError, match="roles"):
        RS.load_registry(p)
    assert RS.load_registry() == {} or all(r["human"] for r in RS.load_registry().values())


def test_decision_file_roundtrip(store, registry, tmp_path):
    rec = POOL["gj-safe-001"]
    text = review.decision_template(rec, RUBRIC, RS.resolve(rec, []))
    for c in RS.applicable_criteria(RUBRIC, rec):
        assert f"  {c}: null" in text
    filled = text.replace("action: null ", "action: approve").replace("overall: null", "overall: acceptable")
    for c in RS.applicable_criteria(RUBRIC, rec):
        filled = filled.replace(f"  {c}: null", f"  {c}: good")
    f = tmp_path / "decision.yaml"
    f.write_text(filled, encoding="utf-8")
    ev = review.decide("approve", rec["id"], "alice", decision_file=str(f), store=store, registry=registry, pool=review._pool())
    assert ev["new_status"] == "approved" and ev["independent_rating"] is True and ev["overall"] == "acceptable"
    with pytest.raises(RS.ReviewError, match="says action"):
        review.decide("reject", rec["id"], "alice", decision_file=str(f), store=store, registry=registry)


def test_committed_review_log_is_intact():
    """Whatever decisions humans have recorded, the committed log must verify (no edits, no deletions)."""
    errors, _ = RS.ReviewStore.default().verify()
    assert errors == []
    for r in RS.load_registry().values():
        assert r["human"], "only humans may be registered as reviewers"


def test_rubric_0_2_1_only_clarifies_the_restricted_safety_anchor():
    """0.2.1 adds `safety.clarifications`; criteria, gates, ratings and decision rules stay as in 0.2.0,
    and the 0.2.0 file that earlier events are stamped with is kept."""
    import yaml
    from gjcore.paths import repo_path
    old = yaml.safe_load(repo_path("evaluation/rubrics/dataset_review_rubric.yaml").read_text(encoding="utf-8"))
    assert old["version"] == "0.2.0"
    new = copy.deepcopy(RUBRIC)
    assert new["version"] == "0.2.1"
    assert any("proceed_with_journey: false" in c for c in new["criteria"]["safety"]["clarifications"])
    new["version"] = old["version"]
    new["criteria"]["safety"].pop("clarifications")
    assert new == old
