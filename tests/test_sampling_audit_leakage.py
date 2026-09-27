"""Review sample, audit heuristics, leakage layers, release gates and gated export."""
import copy

import pytest

from gjcore import schemas
from gjcore.config import load_config
from gjcore.io import load_json
from gjcore.paths import repo_path
from gjcore.records import load_eval_cases
from generation.pipelines import audit, gates, leakage, sampling, split
from generation.pipelines.export import export
from generation.pipelines.pool import load_pool
from generation.validators import leakage as L

POOL = [r for r, _, _ in load_pool()]
BY_ID = {r["id"]: r for r in POOL}
CASES = [c for c, _ in load_eval_cases(repo_path(load_config("evaluation")["cases_dir"]))]


# ---- review sample -------------------------------------------------------------------------

def test_sample_is_deterministic_valid_and_covers_everything():
    a, b = sampling.build_manifest(), sampling.build_manifest()
    assert a == b
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
    assert load_json(repo_path("review/audit_findings_v0.1.0.json")) == r1, "run `gj audit --write`"


def test_known_issues_reference_existing_records():
    ids = set(BY_ID) | {c["id"] for c in CASES}
    for ki in audit.load_known_issues("0.1.0"):
        assert set(ki["records"]) <= ids, ki["id"]


def test_audit_confirms_the_hand_found_high_issues():
    found = {(f["record_id"], f["rule"]) for f in audit.run_audit(POOL) if f["scope"] == "expected_output"}
    assert ("gj-nav-006", "weekday_date_mismatch") in found
    assert ("gj-task-004", "ru_gendered_self_reference") in found
    assert ("gj-clar-007", "ru_gendered_user_address") in found
    assert not any(r == "gj-clar-004" and rule == "weekday_date_mismatch" for r, rule in found)


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
    fake["id"], fake["input"] = "gj-fake-001", copy.deepcopy(CASES[0]["input"])
    rep = L.run_checks(POOL + [fake], CASES, _cfg())
    assert any(f.layer == "exact_input" and f.severity == "hard" for f in rep.findings)


def test_paraphrase_is_caught_by_the_lexical_layer_but_not_by_shingles():
    case = next(c for c in CASES if c["id"] == "ev-q-03")
    fake = copy.deepcopy(BY_ID["gj-clar-003"])
    fake["id"] = "gj-fake-002"
    fake["input"]["goal"] = {"title": "IELTS 7.0 к декабрю"}
    fake["input"]["conversation"] = [{"role": "user", "content": "Моя цель — IELTS на 7.0; экзамен забронирован на 12 декабря. "
                                                                 "Сейчас около 6.0 на пробном тесте, слабее всего у меня writing."}]
    rep = L.run_checks(POOL + [fake], CASES, _cfg())
    kinds = {(f.layer, f.severity) for f in rep.findings if f.a == "gj-fake-002" and f.b == case["id"]}
    assert ("lexical_para", "hard") in kinds
    assert ("char_near_dup", "hard") not in kinds


def test_seed_and_scenario_group_reuse_are_hard():
    fake = copy.deepcopy(BY_ID["gj-safe-001"])
    fake["provenance"] = {**fake["provenance"], "scenario_id": "sc-x-001"}
    meta = {"ev-q-01": {"scenario_group": fake["scenario_group"], "seed_origin": "sc-x-001"}}
    rep = L.run_checks([fake], CASES, _cfg(), eval_meta=meta)
    layers = {f.layer for f in rep.hard}
    assert {"seed", "scenario_group"} <= layers


# ---- gates and export ------------------------------------------------------------------------

def test_v010_is_not_training_ready_for_the_right_reasons():
    results = {r.id: r for r in gates.evaluate("0.1.0")}
    assert not gates.training_ready(results.values())
    assert results["validation_strict"].passed and results["leakage_hard_clean"].passed
    for gid in ("review_all_approved", "calibration_agreement", "eval_readiness", "licensing_resolved", "coverage_minimums"):
        assert not results[gid].passed, gid


def test_training_export_is_refused_and_draft_is_marked(tmp_path):
    assert export("sft", out_dir=str(tmp_path)) == 1
    assert export("sft", out_dir=str(tmp_path), review_policy="allow_pending") == 1
    assert export("sft", out_dir=str(tmp_path), review_policy="allow_pending", allow_draft=True) == 0
    draft = tmp_path / "v0.1.0-draft"
    assert (draft / "DRAFT_NOT_FOR_TRAINING").exists()
    import json
    rows = [json.loads(line) for line in (draft / "sft_train.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows and all(r["metadata"]["training_eligible"] is False for r in rows)
    assert not (tmp_path / "v0.1.0" / "sft_train.jsonl").exists()
    assert export("eval", out_dir=str(tmp_path)) == 0


def test_existing_release_is_idempotent():
    assert split.build_release() == 0
