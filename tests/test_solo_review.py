"""Solo-owner review governance (D-026, D-030): one accountable human decides, an AI copilot never does, the owner's
approval of the exact content suffices in every risk tier (no expert gate), and inter-reviewer gates are N/A — never
"passed" — without independent reviewers."""
import copy
import json

import pytest

from gjcore.config import versions
from gjcore.io import load_yaml
from gjcore.paths import repo_path
from gjcore.records import content_hash
from generation.pipelines import gates, review, review_store as RS, split
from generation.pipelines.export import export
from generation.pipelines.pool import load_pool

POOL = {r["id"]: r for r, _, _ in load_pool()}
RUBRIC = RS.load_rubric()
PAIRWISE = ("reviewer_diversity", "calibration_agreement")
# The multi-reviewer calibration round ended with this event; later events must not change what it recorded.
HISTORICAL_LAST_EVENT = "rev-d8b4bb408657"


def _reviewer(rid, langs=("en", "ru"), roles=("dataset_reviewer",), domains=(), human=True, active=True):
    return {"id": rid, "roles": list(roles), "languages": list(langs), "expert_domains": list(domains),
            "human": human, "active": active}


OWNER = _reviewer("owner")


@pytest.fixture
def store(tmp_path):
    return RS.ReviewStore(tmp_path / "events.jsonl", tmp_path / "snapshots")


def good(rec):
    return {c: "good" for c in RS.applicable_criteria(RUBRIC, rec)}


def decide(store, registry, rec, who, action="approve", overall="excellent", **kw):
    ratings = kw.pop("ratings", good(rec) if action == "approve" else {})
    return RS.record_decision(store, registry, RUBRIC, rec, who, action, ratings, overall, **kw)


def historical_events():
    events = RS.ReviewStore.default().events()
    ids = [e["event_id"] for e in events]
    return events[:ids.index(HISTORICAL_LAST_EVENT) + 1]


@pytest.fixture(scope="module")
def committed_results():
    """Gates on the committed v0.1.1 release with the historical multi-reviewer events, in both modes."""
    ev = historical_events()
    return {mode: {r.id: r for r in gates.evaluate("0.1.1", events=ev, mode=mode)} for mode in RS.REVIEW_MODES}


# ---- mode --------------------------------------------------------------------------------------

def test_solo_owner_is_the_configured_mode_and_old_configs_mean_multi_reviewer():
    assert RS.review_mode() == "solo_owner"
    assert RS.review_mode({}) == "multi_reviewer"          # a config written before D-026
    with pytest.raises(RS.ReviewError, match="governance.mode"):
        RS.review_mode({"governance": {"mode": "solo"}})


def test_only_inter_reviewer_gates_are_mode_scoped():
    """Solo mode must not switch off safety, provenance or approval gates: only the pairwise checks are scoped."""
    scopes = {gid: g["scope"] for gid, g in load_yaml(repo_path("configs/release_gates.yaml"))["gates"].items()}
    assert {gid for gid, s in scopes.items() if s != "always"} == set(PAIRWISE)
    assert all(s in gates.SCOPES for s in scopes.values())


# ---- solo happy path -----------------------------------------------------------------------------

def test_solo_owner_decides_alone_and_their_latest_decision_is_final(store):
    registry = {"owner": OWNER}            # no second reviewer, no adjudicator
    rec = POOL["gj-clar-004"]
    decide(store, registry, rec, "owner")
    info = RS.resolve(rec, store.events())
    assert (info["status"], info["decisions"]) == ("approved", {"owner": "approve"})
    assert RS.training_eligibility(info) == {"human_reviewed": True, "training_eligible": True, "reason": None}
    decide(store, registry, rec, "owner", "revise", "needs_revision", notes="on reflection: question 2 is redundant")
    assert RS.resolve(rec, store.events())["status"] == "needs_revision"
    decide(store, registry, rec, "owner")
    assert RS.resolve(rec, store.events())["status"] == "approved"
    assert store.verify() == ([], [])


def test_solo_owner_can_review_the_whole_sample_without_pairwise_gate_failures(store):
    registry = {"owner": OWNER}
    manifest = json.loads(repo_path("review/review_manifest_v0.1.0.json").read_text(encoding="utf-8"))
    sample = [POOL[i["example_id"]] for i in manifest["items"]]
    for rec in sample:
        decide(store, registry, rec, "owner")
    infos = {r["id"]: RS.resolve(r, store.events()) for r in sample}
    expert = {r["id"] for r in sample if RS.required_expert_domains(r)}
    assert expert                                          # the sample covers the former expert tier
    # D-030: the owner (no domain_expert role) approves every row, the former expert tier included
    assert all((infos[r["id"]]["status"], infos[r["id"]]["detail"]) == ("approved", "decided") for r in sample)
    results = {r.id: r for r in gates.evaluate("0.1.1", rows={"train": sample, "validation": []},
                                               events=store.events(), mode="solo_owner")}
    for gid in PAIRWISE:
        assert (results[gid].applicable, results[gid].passed, results[gid].state) == (False, None, "N/A")
    assert not set(PAIRWISE) & set(gates.failing(results.values()))
    assert results["review_all_approved"].passed is True


# ---- former expert tier (D-030: owner-only approval) ---------------------------------------------

EXPERT_TIER = ("gj-safe-007", "gj-safe-005")      # physical_safety / legal risk domains


def test_owner_approval_of_a_former_expert_tier_example_is_approved_and_training_eligible(store):
    registry = {"owner": OWNER}                                     # dataset_reviewer only, no expert domains
    for ex in EXPERT_TIER:
        rec = POOL[ex]
        assert RS.review_tier(rec) == "expert_review_required" and RS.required_expert_domains(rec)   # still a risk label
        ev = decide(store, registry, rec, "owner")
        assert (ev["new_status"], ev["new_status_detail"]) == ("approved", "decided")
        assert ev["review_tier"] == "expert_review_required"         # the event still records the risk tier
        info = RS.resolve(rec, store.events())
        assert (info["status"], info["detail"]) == ("approved", "decided")
        assert RS.training_eligibility(info) == {"human_reviewed": True, "training_eligible": True, "reason": None}
    assert store.verify() == ([], [])


def test_an_expert_role_is_neither_needed_nor_decisive(tmp_path):
    """An owner without the domain_expert role and one with it reach the same status; the role is never consulted."""
    rec = POOL["gj-safe-007"]
    plain = RS.ReviewStore(tmp_path / "a.jsonl", tmp_path / "snap")
    expert = RS.ReviewStore(tmp_path / "b.jsonl", tmp_path / "snap")
    decide(plain, {"owner": OWNER}, rec, "owner")
    decide(expert, {"owner": _reviewer("owner", roles=("dataset_reviewer", "domain_expert"), domains=("legal",))},
           rec, "owner")
    a, b = RS.resolve(rec, plain.events()), RS.resolve(rec, expert.events())
    assert (a["status"], a["detail"]) == (b["status"], b["detail"]) == ("approved", "decided")
    assert "missing_expert_domains" not in a and "covered_expert_domains" not in a


def test_revise_and_reject_still_block_a_former_expert_tier_example(store):
    registry = {"owner": OWNER}
    rec = POOL["gj-safe-007"]
    decide(store, registry, rec, "owner")
    decide(store, registry, rec, "owner", "revise", "needs_revision", notes="the referral wording needs a change")
    te = RS.training_eligibility(RS.resolve(rec, store.events()))
    assert (te["training_eligible"], te["reason"]) == (False, "needs_revision")
    decide(store, registry, rec, "owner", "reject", "incorrect", notes="cannot be fixed in place")
    te = RS.training_eligibility(RS.resolve(rec, store.events()))
    assert (te["training_eligible"], te["reason"]) == (False, "rejected")


def test_a_changed_former_expert_tier_example_needs_a_new_decision(store):
    """Hash binding is unchanged: the owner's approval covers the exact content it was given, nothing else."""
    rec = copy.deepcopy(POOL["gj-safe-007"])
    decide(store, {"owner": OWNER}, rec, "owner")
    assert RS.resolve(rec, store.events())["status"] == "approved"
    rec["expected_output"]["message_to_user"] += " Edited."
    info = RS.resolve(rec, store.events())
    assert (info["status"], info["detail"]) == ("pending", "content_changed")
    assert not RS.training_eligibility(info)["training_eligible"]


def test_findings_still_need_acknowledgement_on_a_former_expert_tier_example(store):
    rec = POOL["gj-safe-007"]
    with pytest.raises(RS.ReviewError, match="open high-severity findings"):
        decide(store, {"owner": OWNER}, rec, "owner", open_findings=["AF-x"])
    ev = decide(store, {"owner": OWNER}, rec, "owner", open_findings=["AF-x"], acknowledge=True)
    assert ev["acknowledged_findings"] == ["AF-x"] and ev["new_status"] == "approved"


def test_historical_review_events_still_validate_and_resolve():
    """D-030 changes no recorded event: the log verifies, every event validates against the current schema, none
    carries awaiting_expert, and the reviewer and risk-tier snapshots stay readable."""
    from gjcore import schemas
    store = RS.ReviewStore.default()
    events = store.events()
    assert events and store.verify()[0] == []
    for ev in events:
        assert schemas.validate("review_event", ev) == [], ev["event_id"]
        assert ev["new_status_detail"] != "awaiting_expert"
        assert {"roles", "languages", "expert_domains", "human"} <= set(ev["reviewer"])
        assert ev["review_tier"] in ("human_review_required", "expert_review_required")
    assert not any("domain_expert" in ev["reviewer"]["roles"] for ev in events)   # no expert event was ever added
    # the archived 0.1.3 schema, which listed awaiting_expert, still loads and validates the recorded events
    assert all(schemas.validate("review_event", ev, "0.1.3") == [] for ev in events)


def test_release_gates_other_than_review_approval_are_unchanged():
    """D-030 changes who may approve, not what a training-ready release needs."""
    cfg = load_yaml(repo_path("configs/release_gates.yaml"))["gates"]
    settings = {gid: {k: v for k, v in g.items() if k not in ("description", "rationale")} for gid, g in cfg.items()}
    assert settings == {
        "validation_strict": {"blocking": True, "scope": "always"},
        "review_all_approved": {"blocking": True, "scope": "always", "min_approved_share": 1.0},
        "findings_acknowledged": {"blocking": True, "scope": "always"},
        "known_issues_closed": {"blocking": True, "scope": "always", "max_open_severity": "low"},
        "reviewer_diversity": {"blocking": True, "scope": "multi_reviewer", "min_distinct_reviewers": 2,
                               "max_share_single_reviewer": 0.8},
        "calibration_agreement": {"blocking": True, "scope": "multi_reviewer", "min_shared_items": 8,
                                  "min_decision_agreement": 0.75, "min_decision_kappa": 0.4},
        "leakage_hard_clean": {"blocking": True, "scope": "always"},
        "leakage_dispositions": {"blocking": True, "scope": "always"},
        "coverage_minimums": {"blocking": True, "scope": "always", "min_approved_train": 1000, "min_per_task_type": 20,
                              "min_language_share": {"ru": 0.35, "en": 0.35}, "min_mixed_input_share": 0.03,
                              "min_non_allowed_safety_share": 0.08},
        "preference_minimums": {"blocking": True, "scope": "always", "applies_to": ["preference"],
                                "min_per_failure_mode": 5},
        "eval_readiness": {"blocking": True, "scope": "always", "min_cases": 200, "min_cases_per_task_type": 10},
        "licensing_resolved": {"blocking": True, "scope": "always", "file": "configs/licensing_status.yaml"},
    }


def test_no_current_code_path_produces_awaiting_expert():
    assert "awaiting_expert" not in RS.DETAILS and "awaiting_expert" not in RS.INELIGIBILITY_REASONS
    assert "expert_tier_requires_expert" not in RS.review_config()["approval"]
    events = RS.ReviewStore.default().events()
    infos = [RS.resolve(r, events) for r in POOL.values()]
    assert all(i["detail"] in RS.DETAILS for i in infos)
    assert all(RS.training_eligibility(i)["reason"] in (None, *RS.INELIGIBILITY_REASONS) for i in infos)


# ---- AI copilot ----------------------------------------------------------------------------------

def test_ai_copilot_can_never_create_a_human_approval(store):
    rec = POOL["gj-safe-007"]
    registry = {"owner": OWNER, "ai-copilot": _reviewer("ai-copilot", roles=("dataset_reviewer", "domain_expert"),
                                                        domains=("physical_safety",), human=False)}
    with pytest.raises(RS.ReviewError, match="not marked human"):
        decide(store, registry, rec, "ai-copilot")
    with pytest.raises(RS.ReviewError, match="unknown reviewer"):
        decide(store, registry, rec, "claude")
    # the copilot may dry-check a draft decision: that validates, and records nothing
    assert RS.check_decision(RUBRIC, rec, "approve", good(rec), "excellent") == []
    assert store.events() == [] and RS.resolve(rec, store.events())["status"] == "pending"
    # even a forged non-human event with an expert role cannot approve
    forged = {"example_id": rec["id"], "content_hash": content_hash(rec), "reviewer_id": "ai-copilot", "action": "approve",
              "reviewer": {"roles": ["domain_expert"], "languages": ["en"], "expert_domains": ["physical_safety"], "human": False}}
    info = RS.resolve(rec, [forged])
    assert (info["status"], info["detail"]) == ("pending", "not_reviewed")
    assert not RS.training_eligibility(info)["training_eligible"]


def test_a_rating_changed_after_ai_critique_is_recorded_as_not_independent(store):
    rec = POOL["gj-clar-004"]
    ev = review.decide("approve", rec["id"], "owner", rates=[f"{c}=good" for c in good(rec)], overall="acceptable",
                       notes="changed K from major to minor after the copilot pointed to the anchor", independent=False,
                       store=store, registry={"owner": OWNER}, pool={rec["id"]: (rec, None, "authored")})
    assert ev["independent_rating"] is False and ev["reviewer"]["human"] is True
    assert RS.resolve(rec, store.events())["status"] == "approved"      # still the human's decision


# ---- history and multi-reviewer compatibility ----------------------------------------------------

def test_historical_multi_reviewer_events_still_resolve_as_recorded():
    ev = historical_events()
    assert RS.ReviewStore.default().verify()[0] == []
    expected = {"gj-safe-003": "needs_revision", "gj-safe-006": "needs_revision", "gj-time-001": "approved",
                "gj-mem-004": "approved", "gj-web-001": "approved", "gj-daily-001": "approved", "gj-jour-003": "approved",
                "gj-clar-005": "approved"}
    assert {i: RS.resolve(POOL[i], ev)["status"] for i in expected} == expected
    assert RS.resolve(POOL["gj-safe-003"], ev)["decisions"] == {"po-reviewer": "revise", "po-reviewer-two": "approve"}


def test_multi_reviewer_mode_keeps_the_pairwise_gates(committed_results):
    multi = committed_results["multi_reviewer"]
    assert multi["calibration_agreement"].applicable and multi["calibration_agreement"].passed is True
    assert multi["reviewer_diversity"].applicable and multi["reviewer_diversity"].passed is False


def test_multi_reviewer_adjudication_still_overrides(store):
    registry = {"alice": _reviewer("alice"), "bob": _reviewer("bob"), "adj": _reviewer("adj", roles=("adjudicator",))}
    rec = POOL["gj-clar-004"]
    decide(store, registry, rec, "alice")
    decide(store, registry, rec, "bob", "revise", "needs_revision", notes="question 2 is redundant")
    assert RS.resolve(rec, store.events())["status"] == "needs_revision"
    decide(store, registry, rec, "adj", notes="adjudicated: question 2 changes the route")
    assert RS.resolve(rec, store.events())["status"] == "approved"


# ---- reviewer_diversity counts one approval per reviewer per approved row ----------------------------

TWO = {"alice": _reviewer("alice"), "bob": _reviewer("bob")}


def _human_tier_rows(n):
    ids = sorted(i for i, r in POOL.items() if not RS.required_expert_domains(r) and r["language"] in ("en", "ru"))
    return [copy.deepcopy(POOL[i]) for i in ids[:n]]


def _diversity(rows, events, mode="multi_reviewer"):
    results = gates.evaluate("0.1.1", rows={"train": rows, "validation": []}, events=events, mode=mode)
    return next(r for r in results if r.id == "reviewer_diversity")


def _share(result):
    return int(result.detail.split("largest share ")[1].rstrip("%"))


def test_repeated_approvals_by_one_reviewer_of_the_same_row_count_once(store):
    rows = _human_tier_rows(2)
    for rec in rows:
        decide(store, TWO, rec, "alice")
        decide(store, TWO, rec, "alice")            # a corrective re-approval of the same content hash
    decide(store, TWO, rows[0], "bob")
    res = _diversity(rows, store.events())
    assert res.detail == "2 distinct approving reviewer(s); largest share 100%"
    assert _share(res) <= 100


def test_the_rv_0_1_0_01_correction_event_cannot_push_a_share_above_100_percent():
    events = RS.ReviewStore.default().events()
    mine = [e for e in events if e["example_id"] == "gj-feas-005" and e["reviewer_id"] == "po-reviewer"
            and e["action"] == "approve"]
    assert len(mine) >= 2 and mine[-1]["independent_rating"] is False       # the recorded correction
    res = {r.id: r for r in gates.evaluate("0.1.1", events=events, mode="multi_reviewer")}["reviewer_diversity"]
    assert 0 < _share(res) <= 100
    assert not res.passed                        # still fails: po-reviewer approved every approved row
    solo = {r.id: r for r in gates.evaluate("0.1.1", events=events, mode="solo_owner")}
    assert solo["reviewer_diversity"].state == "N/A"


def test_a_genuine_multi_reviewer_distribution_computes_the_expected_shares(store):
    rows = _human_tier_rows(5)
    for rec in rows[:3]:
        decide(store, TWO, rec, "alice")
    for rec in rows[2:]:
        decide(store, TWO, rec, "bob")
    decide(store, TWO, rows[0], "alice")             # repeats change nothing
    res = _diversity(rows, store.events())
    assert res.detail == "2 distinct approving reviewer(s); largest share 60%" and res.passed is True

    skewed = _human_tier_rows(5)
    for rec in skewed:
        decide(store, TWO, rec, "alice")
    decide(store, TWO, skewed[0], "bob")
    res = _diversity(skewed, store.events())
    assert res.detail == "2 distinct approving reviewer(s); largest share 100%" and res.passed is False


def test_an_approval_of_an_older_content_version_does_not_count_for_the_current_one(store):
    rec = _human_tier_rows(1)[0]
    decide(store, TWO, rec, "alice")
    edited = copy.deepcopy(rec)
    edited["expected_output"]["message_to_user"] = (edited["expected_output"].get("message_to_user") or "") + " Edited."
    decide(store, TWO, edited, "bob")
    res = _diversity([edited], store.events())
    assert res.detail == "1 distinct approving reviewer(s); largest share 100%"     # only bob approved this content


def test_solo_mode_keeps_reviewer_diversity_na_with_repeated_approvals(store):
    rows = _human_tier_rows(1)
    decide(store, {"owner": OWNER}, rows[0], "owner")
    decide(store, {"owner": OWNER}, rows[0], "owner")
    res = _diversity(rows, store.events(), mode="solo_owner")
    assert (res.applicable, res.passed, res.state) == (False, None, "N/A")


# ---- no fake pass ----------------------------------------------------------------------------------

def test_solo_mode_reports_pairwise_gates_as_na_never_passed(committed_results, capsys):
    solo = committed_results["solo_owner"]
    for gid in PAIRWISE:
        assert (solo[gid].applicable, solo[gid].passed, solo[gid].state) == (False, None, "N/A")
        assert solo[gid].detail.startswith("N/A in solo_owner mode")
    # same data, same events: only the mode differs, and nothing else changes
    others = set(solo) - set(PAIRWISE)
    assert {g: solo[g].passed for g in others} == {g: committed_results["multi_reviewer"][g].passed for g in others}
    assert not gates.training_ready(solo.values())
    review.cmd_stats()
    out = capsys.readouterr().out
    assert "Review mode: solo_owner" in out
    assert "Independent pair calibration: N/A" in out and "Reviewer diversity: N/A" in out


# ---- content revision and training release ---------------------------------------------------------

def test_changing_reviewed_content_invalidates_the_owner_approval(store):
    rec = copy.deepcopy(POOL["gj-clar-004"])
    decide(store, {"owner": OWNER}, rec, "owner")
    rec["expected_output"]["message_to_user"] += " Edited."
    te = RS.training_eligibility(RS.resolve(rec, store.events()))
    assert (te["training_eligible"], te["human_reviewed"], te["reason"]) == (False, False, "content_changed")


@pytest.fixture
def owner_decisions(store):
    registry = {"owner": OWNER}
    for ex in ("gj-clar-004", "gj-safe-001", "gj-nav-001"):
        decide(store, registry, POOL[ex], "owner")
    decide(store, registry, POOL["gj-safe-007"], "owner")       # former expert tier: the owner's approval suffices (D-030)
    decide(store, registry, POOL["gj-feas-005"], "owner", "revise", "needs_revision", notes="arithmetic in the message")
    return store


@pytest.mark.parametrize("policy", ["require_approved", "allow_pending"])
def test_release_plan_lists_every_ineligible_example_with_its_reason(owner_decisions, monkeypatch, policy):
    monkeypatch.setattr(split, "load_review_events", lambda: owner_decisions.events())
    monkeypatch.setattr(gates, "evaluate", lambda *a, **k: [gates.GateResult("stub", False, "not evaluated here", "")])
    paths = split.release_paths(versions()["dataset_version"])
    before = {k: p.read_bytes() for k, p in paths.items() if p.exists()}
    plan = split.plan_release(review_policy=policy)                              # computes, never writes
    assert {k: p.read_bytes() for k, p in paths.items() if p.exists()} == before
    released = {json.loads(line)["id"] for s in ("train", "validation") for line in plan["texts"][s].splitlines()}
    acc = plan["manifest"]["training_eligibility"]
    listed = {e["id"]: e for e in acc["examples"]}
    assert plan["manifest"]["review_mode"] == "solo_owner"
    assert acc["eligible"] == 4 and len(listed) == len(POOL) - 4 == sum(acc["not_eligible"].values())
    assert "gj-safe-007" not in listed and "gj-safe-007" in released        # owner-approved former expert tier
    assert "awaiting_expert" not in acc["reasons"] and "awaiting_expert" not in acc["not_eligible"]
    assert set(acc["not_eligible"]) <= set(RS.INELIGIBILITY_REASONS)
    assert listed["gj-feas-005"]["reason"] == "needs_revision" and "gj-feas-005" not in released
    assert all(e["in_release"] == (e["id"] in released) for e in listed.values())
    if policy == "require_approved":
        assert released == {"gj-clar-004", "gj-safe-001", "gj-nav-001", "gj-safe-007"}
    else:   # a draft may carry pending rows, but the manifest says each one is not training-eligible and why
        assert plan["release_status"] == "draft_unreviewed"
        assert any(e["in_release"] and e["reason"] == "not_reviewed" for e in listed.values())


def test_training_export_never_contains_a_row_that_is_not_approved(tmp_path):
    assert export("sft", out_dir=str(tmp_path)) == 1           # not training_ready: refused
    assert export("sft", out_dir=str(tmp_path), allow_draft=True) == 0
    rows = [json.loads(line) for split_name in ("train", "validation")
            for line in (tmp_path / f"v{versions()['dataset_version']}-draft" / f"sft_{split_name}.jsonl").read_text(
                encoding="utf-8").splitlines()]
    events = RS.ReviewStore.default().events()
    assert rows and all(r["metadata"]["review_status"] == "approved" for r in rows)
    assert all(RS.resolve(POOL[r["metadata"]["id"]], events)["status"] == "approved" for r in rows)
    assert all(r["metadata"]["training_eligible"] is False for r in rows)     # draft: never marked eligible
