import pytest

from gjcore.config import load_config
from gjcore.io import load_yaml
from gjcore.paths import repo_path
from gjcore.records import load_eval_cases, load_examples
from evaluation.metrics.checks import get_path
from evaluation.metrics.scoring import aggregate, expand_units, extract_json, score_case
from evaluation.runners.baselines import naive_output
from evaluation.runners.validate_cases import validate_cases
from generation.validators import similarity

V010 = "evaluation/cases/v0.1.0"
V020 = "evaluation/cases/v0.2.0"
CASES = [c for c, _ in load_eval_cases(repo_path(V010))]          # frozen v0.1.0 set
CASES2 = [c for c, _ in load_eval_cases(repo_path(V020))]         # current v0.2.0 set
UNITS2 = [u for c in CASES2 for u in expand_units(c)]


def test_current_cases_dir_is_v020():
    assert load_config("evaluation")["cases_dir"] == V020


# --------------------------------------------------------------------------- v0.1.0 (frozen, still valid)

def test_v010_cases_validate_and_references_pass_their_checks():
    s = validate_cases(str(repo_path(V010)))
    assert s["invalid"] == [], s["invalid"]
    assert s["cases"] == 30
    assert len(s["dimensions"]) == 12


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_naive_baseline_is_schema_valid(case):
    assert score_case(case, naive_output(case))["schema_ok"]


def test_checks_discriminate_naive_from_reference():
    ref = aggregate([score_case(c, c["reference_output"]) for c in CASES])
    naive = aggregate([score_case(c, naive_output(c)) for c in CASES])
    assert ref["cases_passing_all_checks"] == len(CASES)
    assert naive["cases_passing_all_checks"] <= len(CASES) // 4
    assert naive["metrics"]["semantic_validity"]["value"] < 0.5
    assert naive["metrics"]["route_preservation"]["value"] < ref["metrics"]["route_preservation"]["value"]


# --------------------------------------------------------------------------- v0.2.0

def test_v020_cases_validate_and_references_pass_their_checks():
    s = validate_cases(str(repo_path(V020)))
    assert s["invalid"] == [], s["invalid"]
    assert 60 <= s["cases"] <= 100
    assert set(s["case_types"]) == {"atomic", "composite", "longitudinal"}
    assert s["units"] == len(UNITS2) and s["units"] > s["cases"]
    assert {"state_consistency", "numeric_consistency", "evidence_integrity"} <= set(s["dimensions"])


@pytest.mark.parametrize("unit", UNITS2, ids=[u["unit_id"] for u in UNITS2])
def test_v020_naive_baseline_is_schema_valid(unit):
    assert score_case(unit, naive_output(unit))["schema_ok"]


def test_v020_checks_discriminate_naive_from_reference():
    ref = aggregate([score_case(u, u["reference_output"]) for u in UNITS2])
    naive = aggregate([score_case(u, naive_output(u)) for u in UNITS2])
    assert ref["units_passing_all_checks"] == len(UNITS2)
    assert ref["cases_passing_all_checks"] == len(CASES2)
    assert naive["units_passing_all_checks"] <= len(UNITS2) // 10
    assert naive["cases_passing_all_checks"] == 0
    for metric in ("state_consistency", "numeric_consistency", "evidence_integrity", "deadline_autonomy"):
        assert naive["metrics"][metric]["value"] < ref["metrics"][metric]["value"], metric


def test_v020_builder_output_is_committed():
    """The YAML files are generated from evaluation/builders/; editing them by hand is caught here."""
    from evaluation.builders import build
    assert build.run(check=True) == 0


def test_v020_case_type_shapes():
    by_type = {}
    for c in CASES2:
        by_type.setdefault(c["case_type"], []).append(c)
    assert all("steps" not in c for c in by_type["atomic"])
    assert all(2 <= len(c["steps"]) <= 3 for c in by_type["composite"])
    assert all(5 <= len(c["steps"]) <= 12 for c in by_type["longitudinal"])
    # reference_status is derived from the recorded human reference reviews (D-028): a case without one is a draft
    from evaluation import reference_review as RR
    assert all(c["reference_status"] == RR.derive_status(c) for c in CASES2)
    assert all(c["reference_status"] == "draft_unreviewed" for c in CASES2 if "reference_review" not in c)


REQUIRED_STRATA = {"ru", "en", "mixed_language", "safety", "verification", "route_adaptation", "memory", "time_change",
                   "goal_change", "web_research", "user_disagreement", "multi_turn", "calendar_arithmetic",
                   "capability_boundary", "provenance"}
REQUIRED_ADVERSARIAL = {"evidence_attack", "embedded_instruction", "contradictory_evidence", "contradictory_memory",
                        "impossible_constraint", "unrealistic_deadline", "major_route_change", "user_disagreement",
                        "unsupported_external_fact"}


def test_v020_strata_and_adversarial_coverage():
    strata = {s: sum(1 for c in CASES2 if s in c["strata"]) for s in REQUIRED_STRATA}
    assert all(n >= 3 for n in strata.values()), strata
    adv = {a: sum(1 for c in CASES2 if a in c.get("adversarial", [])) for a in REQUIRED_ADVERSARIAL}
    assert all(n >= 1 for n in adv.values()), adv
    assert {c["language"] for c in CASES2} == {"ru", "en"}
    assert any(c["input_language"] == "mixed" for c in CASES2)


def test_v020_longitudinal_chain_covers_the_full_loop():
    """At least one case follows goal -> clarification -> journey -> task -> proof -> verification ->
    new information -> route adaptation -> next task."""
    loop = ["goal_clarification", "journey_generation", "task_generation", "verification_result", "route_adaptation",
            "daily_plan"]
    for c in CASES2:
        if c["case_type"] != "longitudinal":
            continue
        ops = [s["task_type"] for s in c["steps"]]
        it = iter(ops)
        if all(op in it for op in loop):  # subsequence
            return
    pytest.fail("no longitudinal case covers the full loop in order")


def test_v020_python_example_from_the_brief():
    case = next(c for c in CASES2 if c["id"] == "e2-long-01")
    user_turns = " ".join(t["content"] for s in case["steps"] for t in s["input"].get("conversation", [])
                          if t["role"] == "user").lower()
    for phrase in ("learn python", "weekends only", "javascript", "no courses", "two months, not six"):
        assert phrase in user_turns, phrase
    assert len(case["steps"]) >= 5


def test_v020_scenarios_and_seeds_are_isolated_from_training():
    reg = {s["id"]: s for s in load_yaml(repo_path("data/scenarios/behavioural_scenarios.yaml"))["scenarios"]}
    train_patterns = {(s["operation"], s["trigger"], s["condition"], s["decision"]) for s in reg.values() if s["side"] == "train"}
    groups = [c["scenario_group"] for c in CASES2]
    assert len(groups) == len(set(groups)), "one behavioural scenario per evaluation case"
    for g in groups:
        assert reg[g]["side"] == "eval"
        assert (reg[g]["operation"], reg[g]["trigger"], reg[g]["condition"], reg[g]["decision"]) not in train_patterns
    for u in UNITS2:
        if u.get("step_pattern"):
            assert tuple(u["step_pattern"].split("|")) not in train_patterns, u["unit_id"]
    seeds = load_yaml(repo_path("evaluation/seeds/v0.2.0.yaml"))["seeds"]
    seed_ids = [s["id"] for s in seeds]
    assert len(seed_ids) == len(set(seed_ids)) == len(CASES2)
    assert {c["seed_id"] for c in CASES2} == set(seed_ids)
    train_seed_ids = {(r.get("provenance") or {}).get("scenario_id") for r, _ in load_examples(repo_path("data/raw/examples"))}
    assert not set(seed_ids) & train_seed_ids


def test_v020_leakage_has_no_hard_findings_and_every_candidate_is_reviewed():
    from generation.pipelines.leakage import build
    rep, summary, problems = build()
    assert not problems, problems
    assert not rep.hard, [f.to_dict() for f in rep.hard]
    assert summary["unreviewed_auto_candidates"] == []
    assert summary["eval_cases_without_metadata"] == []
    assert set(summary["families"]) == {"lexical", "semantic_template", "scenario"}


def test_v020_no_near_duplicates_with_training_pool():
    pool = [(r["id"], similarity.signature_text(r["input"])) for r, _ in load_examples(repo_path("data/raw/examples"))]
    units = [(u["unit_id"], similarity.signature_text(u["input"])) for u in UNITS2]
    assert similarity.cross_near_duplicates(pool, units, 0.55) == []


# --------------------------------------------------------------------------- scoring helpers

def test_unparseable_output_fails_everything():
    case = CASES[0]
    obj, err = extract_json("not json at all")
    scored = score_case(case, obj, parse_error=err)
    assert not scored["schema_ok"] and not any(c["passed"] for c in scored["checks"])


def test_extract_json_tolerates_fences():
    obj, err = extract_json('```json\n{"a": 1}\n```')
    assert err is None and obj == {"a": 1}


def test_get_path():
    data = {"a": {"b": [{"c": 1}, {"c": 2}]}}
    assert get_path(data, "a.b[*].c") == [1, 2]
    assert get_path(data, "a.b[1].c") == [2]
    assert get_path(data, "a.missing") == []


def test_expand_units_carries_step_fields():
    case = next(c for c in CASES2 if c["case_type"] == "composite")
    units = expand_units(case)
    assert [u["unit_id"] for u in units] == [f"{case['id']}/{s['step_id']}" for s in case["steps"]]
    assert all(u["case_id"] == case["id"] and u["step_pattern"] for u in units)


def test_no_leakage_between_training_pool_and_eval_cases():
    pool = [(r["id"], similarity.signature_text(r["input"])) for r, _ in load_examples(repo_path("data/raw/examples"))]
    cases = [(c["id"], similarity.signature_text(c["input"])) for c in CASES]
    assert similarity.cross_near_duplicates(pool, cases, 0.55) == []
