"""Human reviews of evaluation reference outputs, stored in the cases (D-028, schema 0.1.3)."""
import copy
import shutil
from datetime import datetime, timezone

import pytest

from gjcore import schemas
from gjcore.paths import repo_path
from gjcore.records import load_eval_cases
from evaluation import reference_review as RR
from evaluation.builders import build
from evaluation.runners.validate_cases import validate_cases
from generation.pipelines import review_store

V020 = repo_path("evaluation/cases/v0.2.0")
CASES = {c["id"]: c for c, _ in load_eval_cases(V020)}
# the cases as the builder authors them, with no recorded review: tests of the mechanism must not depend on
# which cases the owner has reviewed so far
PRISTINE = {cid: RR.attach(copy.deepcopy(c), None) for cid, c in CASES.items()}
REGISTRY = review_store.load_registry()
TS = "2026-10-01T12:00:00Z"


def _unreviewed(cid):
    """The case as the builder authors it, without any recorded review."""
    return RR.attach(copy.deepcopy(CASES[cid]), None)


def _unit(case, step_id=None, **kw):
    ref = RR.reference_units(case)[step_id]
    u = {"step_id": step_id} if step_id else {}
    u.update({"content_hash": RR.reference_hash(ref), "action": "approve", "overall": "excellent", "issues": [],
              "notes": ""})
    u.update(kw)
    return u


def _session(units, ts=TS, reviewer="po-reviewer", independent=True):
    return {"reviewer_id": reviewer, "timestamp": ts, "governance_mode": "solo_owner",
            "independent_rating": independent, "units": units}


def _reviewed(case, *sessions):
    return RR.attach(case, {"metadata_schema_version": RR.INTRODUCED_IN, "sessions": list(sessions)})


def _decisions(case, steps=None, **kw):
    keys = list(RR.reference_units(case)) if steps is None else steps
    return [{**({"step_id": k} if k else {}), "action": "approve", "overall": "excellent", "issues": [], "notes": "",
             **kw} for k in keys]


# ---- schema -------------------------------------------------------------------------------------

def test_schema_accepts_a_hash_bound_review_and_its_version_is_the_metadata_version():
    case = _reviewed(_unreviewed("e2-long-02"), _session([_unit(_unreviewed("e2-long-02"), "s1")]))
    assert schemas.validate("eval_case", case, RR.INTRODUCED_IN) == []
    # the case's own schema_version stays the model input/output contract, which has no review block
    assert case["schema_version"] == "0.1.1"
    assert schemas.validate("eval_case", case, case["schema_version"])
    assert schemas.validate("eval_case", case, "0.1.2"), "schema 0.1.2 is archived without reference_review"


@pytest.mark.parametrize("change", [
    {"overall": "needs_revision"},                                    # approve needs excellent|acceptable
    {"issues": [{"severity": "major", "description": "wrong date"}]},  # approve tolerates minor issues only
    {"action": "revise", "overall": "needs_revision"},                 # revise needs an issue
    {"action": "reject", "overall": "incorrect"},                      # reject needs an issue
    {"action": "approved"},
    {"rating_q": "good"},                                              # no invented criterion ratings
])
def test_schema_refuses_inconsistent_unit_decisions(change):
    base = _unreviewed("e2-long-02")
    case = _reviewed(base, _session([_unit(base, "s1", **change)]))
    assert schemas.validate("eval_case", case, RR.INTRODUCED_IN)


def test_schema_refuses_multi_reviewer_sessions():
    base = _unreviewed("e2-long-02")
    s = _session([_unit(base, "s1")])
    s["governance_mode"] = "multi_reviewer"
    assert schemas.validate("eval_case", _reviewed(base, s), RR.INTRODUCED_IN)


# ---- status derivation --------------------------------------------------------------------------

def test_status_is_human_reviewed_only_when_every_reference_output_is_decided():
    base = _unreviewed("e2-long-02")
    steps = list(RR.reference_units(base))
    partial = _reviewed(base, _session([_unit(base, k) for k in steps[:-1]]))
    assert partial["reference_status"] == "draft_unreviewed"
    assert RR.summary(partial) == {"units": len(steps), "decided": len(steps) - 1, "stale": [],
                                   "status": "draft_unreviewed", "missing_expert_domains": []}
    full = _reviewed(base, _session([_unit(base, k) for k in steps[:-1]]),
                     _session([_unit(base, steps[-1])], ts="2026-10-02T09:00:00Z"))
    assert full["reference_status"] == "human_reviewed"
    # a revise decision is still a human decision: the status says reviewed, the unit says what was decided
    revised = _reviewed(base, _session([_unit(base, k) for k in steps[:-1]] + [
        _unit(base, steps[-1], action="revise", overall="needs_revision",
              issues=[{"severity": "major", "description": "the plan skips the deadline"}])]))
    assert revised["reference_status"] == "human_reviewed"
    assert RR.decided_units(revised)[steps[-1]]["action"] == "revise"


def test_a_review_of_changed_content_does_not_count():
    base = _unreviewed("e2-clar-02")
    reviewed = _reviewed(base, _session([_unit(base)]))
    assert reviewed["reference_status"] == "human_reviewed"
    changed = copy.deepcopy(reviewed)
    changed["reference_output"]["message_to_user"] = changed["reference_output"].get("message_to_user", "") + " "
    assert RR.derive_status(changed) == "draft_unreviewed"
    assert RR.summary(changed) == {"units": 1, "decided": 0, "stale": [None], "status": "draft_unreviewed",
                                   "missing_expert_domains": []}


def test_the_latest_decision_on_the_current_content_counts():
    base = _unreviewed("e2-clar-02")
    case = _reviewed(base, _session([_unit(base)]),
                     _session([_unit(base, overall="acceptable", notes="second look")], ts="2026-10-03T08:00:00Z"))
    assert RR.decided_units(case)[None]["overall"] == "acceptable"


def test_as_of_restores_the_case_a_release_was_built_from():
    base = _unreviewed("e2-long-02")
    later = _reviewed(base, _session([_unit(base, "s1")], ts="2026-10-05T10:00:00Z"))
    before = datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert RR.as_of(later, before) == base
    assert RR.as_of(later, datetime(2026, 10, 6, tzinfo=timezone.utc)) == later
    assert list(later)[list(later).index("reference_status") + 1] == "reference_review"


# ---- semantic checks ----------------------------------------------------------------------------

def test_semantic_errors_catch_what_the_schema_cannot():
    base = _unreviewed("e2-long-02")
    ok = _reviewed(base, _session([_unit(base, "s1")]))
    assert RR.semantic_errors(ok, REGISTRY) == []
    assert any("not a registered human" in e
               for e in RR.semantic_errors(_reviewed(base, _session([_unit(base, "s1")], reviewer="ghost")), REGISTRY))
    bad_step = _reviewed(base, _session([{**_unit(base, "s1"), "step_id": "s42"}]))
    assert any("no reference output" in e for e in RR.semantic_errors(bad_step, REGISTRY))
    twice = _reviewed(base, _session([_unit(base, "s1"), _unit(base, "s1")]))
    assert any("decided twice" in e for e in RR.semantic_errors(twice, REGISTRY))
    order = _reviewed(base, _session([_unit(base, "s1")], ts="2026-10-02T00:00:00Z"), _session([_unit(base, "s2")]))
    assert any("timestamp order" in e for e in RR.semantic_errors(order, REGISTRY))
    forged = {**base, "reference_status": "human_reviewed"}
    assert any("derived" in e for e in RR.semantic_errors(forged, REGISTRY))
    atomic = _unreviewed("e2-clar-02")
    stepped = _reviewed(atomic, _session([{**_unit(atomic), "step_id": "s1"}]))
    assert any("atomic" in e for e in RR.semantic_errors(stepped, REGISTRY))


# ---- builder and recording (on a temporary copy of the case files) -------------------------------

@pytest.fixture
def cases_copy(tmp_path, monkeypatch):
    """A temporary copy of the case files with every recorded review removed (rendered by the builder)."""
    d = tmp_path / "v0.2.0"
    shutil.copytree(V020, d)
    monkeypatch.setattr(build, "CASES_DIR", d)
    assert build.run(reviews={}) == 0
    assert {c["id"]: c for c, _ in load_eval_cases(d)} == PRISTINE
    return d


def _case(d, cid):
    return next(c for c, _ in load_eval_cases(d) if c["id"] == cid)


def test_recording_a_partial_then_complete_review_through_the_builder(cases_copy):
    case = _case(cases_copy, "e2-comp-01")
    first, second = list(RR.reference_units(case))
    out = RR.record("e2-comp-01", "po-reviewer", _decisions(case, [first]), True, timestamp="2026-10-01T10:00:00Z")
    assert out["reference_status"] == "draft_unreviewed"
    on_disk = _case(cases_copy, "e2-comp-01")
    assert on_disk == out
    assert build.run(check=True) == 0, "the recorded review is carried over: regeneration reproduces the file"
    with pytest.raises(RR.ReferenceReviewError, match="already have po-reviewer's decision"):
        RR.record("e2-comp-01", "po-reviewer", _decisions(case, [first]), True, timestamp="2026-10-01T11:00:00Z")
    out = RR.record("e2-comp-01", "po-reviewer", _decisions(case, [second]), False, timestamp="2026-10-01T11:00:00Z")
    assert out["reference_status"] == "human_reviewed"
    sessions = out["reference_review"]["sessions"]
    assert [s["independent_rating"] for s in sessions] == [True, False]
    assert [u["step_id"] for s in sessions for u in s["units"]] == [first, second]
    # nothing but the review block and the derived status changed; every other case is untouched
    assert {k: v for k, v in out.items() if k not in ("reference_review", "reference_status")} == \
           {k: v for k, v in PRISTINE["e2-comp-01"].items() if k not in ("reference_review", "reference_status")}
    assert {c["id"]: c for c, _ in load_eval_cases(cases_copy) if c["id"] != "e2-comp-01"} == \
           {k: v for k, v in PRISTINE.items() if k != "e2-comp-01"}
    s = validate_cases(str(cases_copy))
    assert s["invalid"] == [], s["invalid"]
    assert s["reference_reviews"]["human_reviewed_cases"] >= 1


def test_the_builder_never_drops_a_recorded_review(cases_copy):
    case = _case(cases_copy, "e2-clar-02")
    review = {"metadata_schema_version": RR.INTRODUCED_IN, "sessions": [_session([_unit(case)])]}
    with pytest.raises(build.BuildError, match="no longer produces"):
        build.render({"e2-zzz-99": review})


@pytest.mark.parametrize("args, match", [
    (("e2-clar-02", "ghost"), "unknown reviewer"),
    (("e2-nope-01", "po-reviewer"), "no evaluation case"),
])
def test_record_refuses(cases_copy, args, match):
    case = CASES.get(args[0]) or CASES["e2-clar-02"]
    with pytest.raises(RR.ReferenceReviewError, match=match):
        RR.record(*args, _decisions(case), True)
    assert {c["id"]: c for c, _ in load_eval_cases(cases_copy)} == PRISTINE, "a refused review writes nothing"


def test_record_refuses_bad_decision_files(cases_copy):
    case = CASES["e2-long-02"]
    for units, match in [
        ([{"action": "approve", "overall": "excellent"}], "needs a step_id"),
        ([{"step_id": "s99", "action": "approve", "overall": "excellent"}], "no reference output"),
        (_decisions(case, ["s1", "s1"]), "listed twice"),
        ([{**_decisions(case, ["s1"])[0], "content_hash": "0" * 64}], "computed, never given"),
        ([{"step_id": "s1", "overall": "excellent"}], "`action` is required"),
        (_decisions(case, ["s1"], overall="needs_revision"), "eval_case schema"),
        ([], "non-empty"),
    ]:
        with pytest.raises(RR.ReferenceReviewError, match=match):
            RR.record("e2-long-02", "po-reviewer", units, True)
    with pytest.raises(RR.ReferenceReviewError, match="independent_rating"):
        RR.record("e2-long-02", "po-reviewer", _decisions(case), None)
    assert {c["id"]: c for c, _ in load_eval_cases(cases_copy)} == PRISTINE


def test_record_refuses_non_humans_language_gaps_and_multi_reviewer_mode(cases_copy, monkeypatch):
    case = CASES["e2-clar-02"]
    real = dict(REGISTRY)
    monkeypatch.setattr(review_store, "load_registry", lambda path=None: {
        **real, "bot": {**real["po-reviewer"], "id": "bot", "human": False},
        "ru-only": {**real["po-reviewer"], "id": "ru-only", "languages": ["ru"]}})
    with pytest.raises(RR.ReferenceReviewError, match="not marked human"):
        RR.record("e2-clar-02", "bot", _decisions(case), True)
    with pytest.raises(RR.ReferenceReviewError, match="needs a reviewer who reads"):
        RR.record("e2-clar-02", "ru-only", _decisions(case), True)
    monkeypatch.setattr(review_store, "review_mode", lambda cfg=None: "multi_reviewer")
    with pytest.raises(RR.ReferenceReviewError, match="solo_owner only"):
        RR.record("e2-clar-02", "po-reviewer", _decisions(case), True)
    assert {c["id"]: c for c, _ in load_eval_cases(cases_copy)} == PRISTINE


def _with_experts(monkeypatch):
    real = dict(REGISTRY)
    expert = {**real["po-reviewer"], "roles": ["domain_expert"], "languages": ["en", "ru"]}
    monkeypatch.setattr(review_store, "load_registry", lambda path=None: {
        **real, "med-expert": {**expert, "id": "med-expert", "expert_domains": ["medical"]},
        "law-expert": {**expert, "id": "law-expert", "expert_domains": ["legal"]}})


def test_owner_review_of_an_expert_tier_case_awaits_the_expert(cases_copy, monkeypatch):
    """D-029: the owner may record on an expert-tier case; only a matching domain_expert completes it."""
    case = _case(cases_copy, "e2-safe-01")
    assert RR.required_expert_domains(case) == ["medical"]
    out = RR.record("e2-safe-01", "po-reviewer", _decisions(case), True, timestamp="2026-10-02T10:00:00Z")
    owner = out["reference_review"]["sessions"][0]
    assert (owner["reviewer_roles"], owner["reviewer_expert_domains"]) == (["dataset_reviewer"], [])
    assert out["reference_status"] == "awaiting_expert"
    assert RR.missing_expert_domains(out) == ["medical"]
    assert build.run(check=True) == 0
    s = validate_cases(str(cases_copy))
    assert s["invalid"] == [], s["invalid"]
    assert s["reference_reviews"]["awaiting_expert_cases"] == ["e2-safe-01 (needs medical)"]
    _with_experts(monkeypatch)
    # an expert in another domain covers nothing; a second reviewer's decision needs no --replace
    out = RR.record("e2-safe-01", "law-expert", _decisions(case), True, timestamp="2026-10-02T11:00:00Z")
    assert out["reference_status"] == "awaiting_expert"
    out = RR.record("e2-safe-01", "med-expert", _decisions(case), True, timestamp="2026-10-02T12:00:00Z")
    assert out["reference_status"] == "human_reviewed" and RR.missing_expert_domains(out) == []
    assert [s["reviewer_id"] for s in out["reference_review"]["sessions"]] == ["po-reviewer", "law-expert",
                                                                              "med-expert"]
    with pytest.raises(RR.ReferenceReviewError, match="already have med-expert's decision"):
        RR.record("e2-safe-01", "med-expert", _decisions(case), True, timestamp="2026-10-02T13:00:00Z")


def test_a_session_without_recorded_roles_gives_no_expert_coverage():
    base = _unreviewed("e2-safe-01")
    session = _session([_unit(base)])          # no reviewer_roles / reviewer_expert_domains
    assert _reviewed(base, session)["reference_status"] == "awaiting_expert"
    expert = {**session, "reviewer_id": "med-expert", "reviewer_roles": ["domain_expert"],
              "reviewer_expert_domains": ["medical"], "timestamp": "2026-10-03T00:00:00Z"}
    assert _reviewed(base, session, expert)["reference_status"] == "human_reviewed"
    not_expert = {**expert, "reviewer_roles": ["dataset_reviewer"]}
    assert _reviewed(base, session, not_expert)["reference_status"] == "awaiting_expert", \
        "expert domains count only with the domain_expert role"
    assert schemas.validate("eval_case", _reviewed(base, session, expert), RR.INTRODUCED_IN) == []
    bad = {**expert, "reviewer_roles": ["oracle"]}
    assert schemas.validate("eval_case", _reviewed(base, session, bad), RR.INTRODUCED_IN)


def test_a_human_tier_case_needs_no_expert():
    base = _unreviewed("e2-clar-02")
    assert RR.required_expert_domains(base) == []
    assert _reviewed(base, _session([_unit(base)]))["reference_status"] == "human_reviewed"


# ---- committed state ----------------------------------------------------------------------------

def test_committed_reference_reviews_are_bound_registered_and_derived():
    for case in CASES.values():
        assert RR.semantic_errors(case, REGISTRY) == [], case["id"]
        assert case["reference_status"] == RR.derive_status(case), case["id"]
        for s in (case.get("reference_review") or {}).get("sessions") or []:
            assert REGISTRY[s["reviewer_id"]]["human"]
            assert s["governance_mode"] == "solo_owner"
        if RR.required_expert_domains(case) and case["reference_status"] == "human_reviewed":
            assert RR.missing_expert_domains(case) == [], f"{case['id']} claims expert coverage it lacks"
