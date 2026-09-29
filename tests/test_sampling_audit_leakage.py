"""Review sample, audit heuristics, leakage layers, release gates and gated export."""
import copy

import pytest

from gjcore import schemas
from gjcore.config import load_config, versions
from gjcore.io import load_json
from gjcore.paths import repo_path
from gjcore.records import load_eval_cases
from generation.pipelines import audit, gates, leakage, sampling, split
from generation.pipelines.export import export
from generation.pipelines.pool import load_pool
from generation.validators import leakage as L

POOL = [r for r, _, _ in load_pool()]
BY_ID = {r["id"]: r for r in POOL}
CASES = [c for c, _ in load_eval_cases(repo_path(load_config("evaluation")["cases_dir"]))]   # current (v0.2.0)
CASES_V010 = [c for c, _ in load_eval_cases(repo_path("evaluation/cases/v0.1.0"))]           # frozen, atomic only


def _release_rows(version):
    import json
    paths = split.release_paths(version)
    return [json.loads(line) for s in ("train", "validation") for line in paths[s].read_text(encoding="utf-8").splitlines()]


# ---- review sample -------------------------------------------------------------------------

def test_sample_is_deterministic_valid_and_covers_everything():
    # the sample in force is the frozen v0.1.0 draw, regenerated from the v0.1.0 inputs
    a, b = sampling.build_sample_in_force(), sampling.build_sample_in_force()
    assert a == b == load_json(repo_path("review/review_manifest_v0.1.0.json"))
    assert schemas.validate("review_manifest", a) == []
    assert a["sample_size"] == 30 and len({it["example_id"] for it in a["items"]}) == 30
    assert {s["name"]: s["count"] for s in a["strata"]} == {"random": 12, "highest_risk": 9, "contrastive": 6, "edge": 3}
    assert a["uncovered"] == []
    assert sum(1 for it in a["items"] if it["tier"] == "expert_review_required") >= 3
    assert a["calibration"]["size"] == 8 and sum(it["calibration"] for it in a["items"]) == 8
    assert [it["review_item_id"] for it in a["items"]] == [f"rv-0.1.0-{i:02d}" for i in range(1, 31)]
    assert all(rp["stratum"] != "random" for rp in a["coverage_repairs"])


def test_random_stratum_is_a_pure_seeded_draw():
    m = sampling.build_manifest()
    drawn = sorted(BY_ID, key=lambda i: sampling._rank(m["seed"], "random:" + i))[:12]
    assert [it["example_id"] for it in m["items"] if it["stratum"] == "random"] == drawn


def test_committed_manifest_is_valid_and_points_at_the_pool():
    m = load_json(repo_path("review/review_manifest_v0.1.0.json"))
    assert schemas.validate("review_manifest", m) == []
    assert all(it["example_id"] in BY_ID for it in m["items"])


def test_largest_remainder_counts():
    strata = load_config("review")["sampling"]["strata"]
    assert sum(sampling._counts(7, strata).values()) == 7
    assert sampling._counts(30, strata) == {"random": 12, "highest_risk": 9, "contrastive": 6, "edge": 3}


# ---- audit heuristics ----------------------------------------------------------------------

def _run_rule(rule, out, inp=None, lang="ru", tt="navigator_response", scope="expected_output"):
    c = audit._Collector()
    rule(c, "x", scope, tt, inp or {"today": "2026-09-27"}, out, lang, {})
    return [f["rule"] for f in c.findings]


@pytest.mark.parametrize("text,flagged", [
    ("Подготовку разбил на 4 задачи.", True),
    ("Не переживайте, я уже всё проверил.", True),
    ("Я рада помочь с маршрутом.", True),
    ("Подготовка разбита на 4 задачи.", False),
    ("Ментор предложил три сессии.", False),
    ("Вы уже сделали самое сложное.", False),
])
def test_ru_gendered_self_reference(text, flagged):
    assert ("ru_gendered_self_reference" in _run_rule(audit.rule_p9, {"message_to_user": text})) is flagged


@pytest.mark.parametrize("text,flagged", [
    ("К какому сроку вы хотите переехать и едете ли вы один или с семьёй?", True),
    ("Вы готов начать?", True),
    ("Вы готовы начать?", False),
    ("Планируете переезд в одиночку или с семьёй?", False),
])
def test_ru_gendered_user_address(text, flagged):
    assert ("ru_gendered_user_address" in _run_rule(audit.rule_p9, {"message_to_user": text})) is flagged


@pytest.mark.parametrize("text,today,flagged", [
    ("позвоню в воскресенье 5-го, удобно?", "2026-09-27", True),        # 5 Oct 2026 is a Monday
    ("Call them on Monday, October 5.", "2026-09-27", False),
    ("5 октября (воскресенье)", "2026-09-27", True),
    ("About 5 hours on Saturday and 5 hours on Sunday", "2026-09-25", False),
])
def test_weekday_date_consistency(text, today, flagged):
    found = _run_rule(audit.rule_temporal, {"message_to_user": text}, inp={"today": today})
    assert ("weekday_date_mismatch" in found) is flagged


def test_user_entered_data_rated_objective_is_flagged():
    proto = {"methods": [{"method": "structured_result", "role": "required", "instructions": "x"}],
             "confidence_ceiling": "high", "self_report_only": False}
    assert "user_entered_as_objective" in _run_rule(audit.rule_p2, {"protocol": proto}, tt="verification_protocol_design")
    proto["confidence_ceiling"] = "limited"
    assert "user_entered_as_objective" not in _run_rule(audit.rule_p2, {"protocol": proto}, tt="verification_protocol_design")


def test_retrieved_memory_leak_is_flagged():
    inp = {"today": "2026-09-27", "goal": {"id": "g-a", "title": "Draw portraits"},
           "retrieved_memory": [{"goal_id": "g-debt", "content": "Paying off a 9,000 credit card balance"}]}
    assert "retrieved_memory_leak" in _run_rule(audit.rule_p8, {"message_to_user": "Mind your credit card balance."}, inp, "en")
    assert "retrieved_memory_leak" not in _run_rule(audit.rule_p8, {"message_to_user": "Draw eyes for 30 minutes."}, inp, "en")


def test_audit_report_is_valid_deterministic_and_committed_file_is_current():
    r1, problems = audit.build_report()
    r2, _ = audit.build_report()
    assert problems == [] and r1 == r2
    current = versions()["dataset_version"]
    assert load_json(repo_path(f"review/audit_findings_v{current}.json")) == r1, "run `gj audit --write`"


@pytest.mark.parametrize("version", ["0.1.0", "0.1.1"])
def test_known_issues_reference_existing_records(version):
    ids = set(BY_ID) | {c["id"] for c, _ in load_eval_cases(repo_path("evaluation/cases"))}
    for ki in audit.load_known_issues(version):
        assert set(ki["records"]) <= ids, ki["id"]


def test_audit_confirms_the_hand_found_high_issues_in_v010():
    rows = _release_rows("0.1.0")
    found = {(f["record_id"], f["rule"]) for f in audit.run_audit(rows) if f["scope"] == "expected_output"}
    assert ("gj-nav-006", "weekday_date_mismatch") in found
    assert ("gj-task-004", "ru_gendered_self_reference") in found
    assert ("gj-clar-007", "ru_gendered_user_address") in found
    assert not any(r == "gj-clar-004" and rule == "weekday_date_mismatch" for r, rule in found)


def test_v011_fixes_the_hand_found_high_issues():
    found = {(f["record_id"], f["rule"]) for f in audit.run_audit(POOL) if f["scope"] == "expected_output"}
    for pair in (("gj-nav-006", "weekday_date_mismatch"), ("gj-task-004", "ru_gendered_self_reference"),
                 ("gj-clar-007", "ru_gendered_user_address")):
        assert pair not in found, pair
    assert not any(f["severity"] == "high" for f in audit.run_audit(POOL) if f["scope"] == "expected_output")


# ---- leakage -------------------------------------------------------------------------------

def test_current_data_has_no_hard_leakage_and_complete_metadata():
    rep, summary, problems = leakage.build()
    assert rep.hard == [] and problems == []
    assert summary["eval_cases_without_metadata"] == []
    assert summary["unreviewed_auto_candidates"] == []


def _cfg():
    return load_config("dataset")["leakage"]


def test_exact_duplicate_of_an_eval_input_is_hard():
    fake = copy.deepcopy(BY_ID["gj-safe-001"])
    fake["id"], fake["input"] = "gj-fake-001", copy.deepcopy(CASES_V010[0]["input"])
    rep = L.run_checks(POOL + [fake], CASES_V010, _cfg())
    assert any(f.layer == "exact_input" and f.severity == "hard" for f in rep.findings)


def test_paraphrase_is_caught_by_the_lexical_layer_but_not_by_shingles():
    case = next(c for c in CASES_V010 if c["id"] == "ev-q-03")
    fake = copy.deepcopy(BY_ID["gj-clar-003"])
    fake["id"] = "gj-fake-002"
    fake["input"]["goal"] = {"title": "IELTS 7.0 к декабрю"}
    fake["input"]["conversation"] = [{"role": "user", "content": "Моя цель — IELTS на 7.0; экзамен забронирован на 12 декабря. "
                                                                 "Сейчас около 6.0 на пробном тесте, слабее всего у меня writing."}]
    rep = L.run_checks(POOL + [fake], CASES_V010, _cfg())
    kinds = {(f.layer, f.severity) for f in rep.findings if f.a == "gj-fake-002" and f.b == case["id"]}
    assert ("lexical_para", "hard") in kinds
    assert ("char_near_dup", "hard") not in kinds


def test_seed_and_scenario_group_reuse_are_hard():
    fake = copy.deepcopy(BY_ID["gj-safe-001"])
    fake["provenance"] = {**fake["provenance"], "scenario_id": "sc-x-001"}
    meta = {"ev-q-01": {"scenario_group": fake["scenario_group"], "seed_origin": "sc-x-001"}}
    rep = L.run_checks([fake], CASES_V010, _cfg(), eval_meta=meta)
    layers = {f.layer for f in rep.hard}
    assert {"seed", "scenario_group"} <= layers


def _units(cases):
    from evaluation.metrics.scoring import expand_units
    return [u for c in cases for u in expand_units(c)]


def test_step_of_a_multistep_case_is_checked_on_its_own_input():
    unit = next(u for u in _units(CASES) if u["unit_id"] == "e2-long-01/s5")
    fake = copy.deepcopy(BY_ID["gj-safe-001"])
    fake["id"], fake["input"] = "gj-fake-003", copy.deepcopy(unit["input"])
    rep = L.run_checks(POOL + [fake], _units(CASES), _cfg())
    assert any(f.layer == "exact_input" and f.b == "e2-long-01/s5" for f in rep.hard)


def test_reused_decision_pattern_is_hard_and_similar_one_is_flagged():
    from generation.pipelines.leakage import load_registry
    reg = load_registry()
    train = next(s for s in reg if s["side"] == "train")
    same = "|".join(train[k] for k in ("operation", "trigger", "condition", "decision"))
    near = "|".join([train["operation"], train["trigger"], train["condition"] + "+extra_twist", train["decision"]])
    units = [{"id": "e2-x-01/s1", "step_id": "s1", "case_id": "e2-x-01", "step_pattern": same},
             {"id": "e2-x-01/s2", "step_id": "s2", "case_id": "e2-x-01", "step_pattern": near}]
    found, _ = L.pattern_findings([(train["id"], same)], L.unit_patterns(units, reg), 0.5)
    assert {(f.b, f.severity) for f in found} == {("e2-x-01/s1", "hard"), ("e2-x-01/s2", "warning")}


def test_eval_case_on_a_training_side_scenario_is_hard():
    from generation.pipelines.leakage import load_registry
    reg = load_registry()
    train_sid = next(s["id"] for s in reg if s["side"] == "train")
    found, _ = L.registry_findings(reg, POOL, [{"id": "e2-x-02", "scenario_group": train_sid}])
    assert any(f.layer == "scenario_group" and f.severity == "hard" and f.b == "e2-x-02" for f in found)


def test_leakage_report_separates_the_three_families():
    rep, summary, problems = leakage.build()
    fams = summary["families"]
    assert set(fams) == {"lexical", "semantic_template", "scenario"}
    assert "decision_pattern" in fams["semantic_template"]["layers"] and "template" in fams["semantic_template"]["layers"]
    assert fams["semantic_template"]["reviewed_overlaps"] > 0
    assert all(info["limit"] for info in fams.values())


# ---- gates and export ------------------------------------------------------------------------

@pytest.mark.parametrize("version", ["0.1.0", "0.1.1"])
def test_release_is_not_training_ready_for_the_right_reasons(version):
    results = {r.id: r for r in gates.evaluate(version)}
    assert not gates.training_ready(results.values())
    assert results["leakage_hard_clean"].passed
    if version == "0.1.0":
        assert results["validation_strict"].passed
    else:
        # v0.1.1 lints input protocols too: the only strict failure is gj-vres-007, whose fix is an open
        # reviewer decision (KI-033) — the gate is left failing rather than loosened
        assert not results["validation_strict"].passed and "['gj-vres-007']" in results["validation_strict"].detail
        assert any(k["id"] == "KI-033" and k["status"] == "open" for k in audit.load_known_issues(version))
    # calibration_agreement is no longer expected to fail: all 8 calibration items were double-reviewed blind in
    # human review round 1 and passed the gate's own thresholds. The gate itself is unchanged.
    for gid in ("review_all_approved", "eval_readiness", "licensing_resolved", "coverage_minimums"):
        assert not results[gid].passed, gid


def test_training_export_is_refused_and_draft_is_marked(tmp_path):
    version = versions()["dataset_version"]
    assert export("sft", out_dir=str(tmp_path)) == 1
    assert export("sft", out_dir=str(tmp_path), review_policy="allow_pending") == 1
    assert export("sft", out_dir=str(tmp_path), review_policy="allow_pending", allow_draft=True) == 0
    draft = tmp_path / f"v{version}-draft"
    assert (draft / "DRAFT_NOT_FOR_TRAINING").exists()
    import json
    rows = [json.loads(line) for line in (draft / "sft_train.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows and all(r["metadata"]["training_eligible"] is False for r in rows)
    assert not (tmp_path / f"v{version}" / "sft_train.jsonl").exists()
    assert export("eval", out_dir=str(tmp_path)) == 0


def test_existing_release_is_idempotent(monkeypatch):
    # Never build a release from a test: only re-run the build when the current version is already released.
    paths = split.release_paths(versions()["dataset_version"])
    if not all(p.exists() for p in paths.values()):
        pytest.skip("current dataset version not released yet")
    from datetime import datetime
    from generation.pipelines.pool import load_review_events
    before = {k: p.read_bytes() for k, p in paths.items()}
    # Release rows snapshot each row's review status at build time, and human decisions recorded after the
    # release legitimately change what a rebuild selects. Rebuilding from the release's own inputs (the review
    # log as it stood when the release was built) must reproduce it exactly.
    built = datetime.fromisoformat(load_json(paths["manifest"])["created_at"])
    at_release = [e for e in load_review_events() if datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) <= built]
    monkeypatch.setattr(split, "load_review_events", lambda: at_release)
    assert split.build_release() == 0
    monkeypatch.undo()
    split.build_release()   # live review state: identical data is a no-op, different data is refused
    assert {k: p.read_bytes() for k, p in paths.items()} == before, "an existing release must never be rewritten"


# ---- v0.1.1: revisions, sample status, release ------------------------------------------------

def test_revision_ledger_accounts_for_every_change():
    from generation.pipelines import revisions
    errors, summary = revisions.check("0.1.1")
    assert errors == []
    assert summary["revised_examples"] == 36


def test_sample_status_carries_the_frozen_sample_and_approves_nothing():
    from generation.pipelines import sample_status
    doc = sample_status.build("0.1.1")
    assert schemas.validate("review_sample_status", doc) == []
    assert load_json(repo_path("review/review_sample_status_v0.1.1.json")) == doc, "run `gj review sample-status --write`"
    frozen = load_json(repo_path("review/review_manifest_v0.1.0.json"))
    assert [i["review_item_id"] for i in doc["items"]] == [i["review_item_id"] for i in frozen["items"]]
    assert doc["calibration_items"] == sorted(frozen["calibration"]["items"]) and len(doc["calibration_items"]) == 8
    assert doc["summary"]["approved_by_automation"] == 0
    # Statuses come only from human decisions in the review log; an approved item needs a human approval of
    # its exact current content (the log started empty; human review round 1 has since recorded decisions).
    from generation.pipelines import review_store as RS
    from generation.pipelines.pool import load_review_events
    events = load_review_events()
    for i in doc["items"]:
        info = RS.resolve(BY_ID[i["example_id"]], events)
        assert (i["human_review_status"], i["human_review_detail"]) == (info["status"], info["detail"]), i["example_id"]
        if i["human_review_status"] == "approved":
            assert any(e["example_id"] == i["example_id"] and e["content_hash"] == i["current_content_hash"]
                       and e["action"] == "approve" and e["reviewer"]["human"] for e in events), i["example_id"]
    for i in doc["items"]:
        assert i["changed_since_sampling"] == (i["sampled_content_hash"] != i["current_content_hash"])
        assert bool(i["revision_ids"]) == i["changed_since_sampling"], i["example_id"]


def test_v011_release_records_revisions_and_is_draft():
    m = load_json(split.release_paths("0.1.1")["manifest"])
    assert m["release_status"] == "draft_unreviewed"
    assert m["revisions"]["base_version"] == "0.1.0" and m["revisions"]["revised_examples"] == 36
    revised = [e for e in m["examples"] if e.get("revision_ids")]
    assert len(revised) == 36 and all(e["previous_content_hash"] != e["content_hash"] for e in revised)
    assert m["counts"]["test_eval_cases"] == len(CASES)
