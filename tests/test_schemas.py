from gjcore import schemas
from gjcore.config import versions
from gjcore.io import load_yaml
from gjcore.paths import PROMPTS_DIR
from generation.validators import semantic


def test_all_schemas_load_and_are_valid():
    names = schemas.schema_names()
    assert len(names) >= 25
    for n in names:
        schemas.validator(n)  # raises on invalid schema or bad $id


def test_every_operation_has_an_output_schema():
    ops = schemas.validator("common").schema["$defs"]["operation"]["enum"]
    assert set(ops) == set(schemas.OPERATION_SCHEMAS)
    for op, name in schemas.OPERATION_SCHEMAS.items():
        assert schemas.validator(name).schema["properties"]["type"]["const"] == op


def test_failure_mode_catalogue_is_consistent():
    enum = set(schemas.validator("common").schema["$defs"]["failure_mode"]["enum"])
    catalogue = load_yaml(PROMPTS_DIR / "generation" / f"v{versions()['generation_prompt_version']}" / "failure_modes.yaml")
    assert set(catalogue) == enum
    auto = {m for m, v in catalogue.items() if v["detection"] == "auto"}
    assert auto == semantic.ALWAYS_DETECTABLE
    assert set(semantic.FAILURE_MODE_CODES) <= enum


def test_archived_failure_mode_catalogue_matches_archived_schema():
    enum = set(schemas.validator("common", "0.1.0").schema["$defs"]["failure_mode"]["enum"])
    assert set(load_yaml(PROMPTS_DIR / "generation" / "v0.1.0" / "failure_modes.yaml")) == enum


def test_every_schema_version_loads():
    assert schemas.available_versions()[:2] == ["0.1.0", "0.1.1"]
    for v in schemas.available_versions():
        for n in schemas.schema_names(v):
            schemas.validator(n, v)


def test_goal_requires_only_title():
    assert schemas.validate("goal", {"title": "Learn to swim"}) == []
    assert schemas.validate("goal", {}) != []


def test_memory_scope_rules():
    assert schemas.validate("memory", {"scope": "goal", "category": "fact", "content": "x"}) != []
    assert schemas.validate("memory", {"scope": "user", "goal_id": "g1", "category": "fact", "content": "x"}) != []
    assert schemas.validate("memory", {"scope": "goal", "goal_id": "g1", "category": "fact", "content": "x"}) == []


def test_verified_claim_requires_source():
    out = {"type": "web_research_decision", "needs_research": False, "reason_categories": ["none"], "rationale": "x",
           "facts_to_verify": [], "queries": [], "unsupported_claims": [], "can_proceed_without_research": True}
    assert schemas.validate_output("web_research_decision", out) == []
    feas = {"type": "feasibility_assessment", "response_language": "en", "message_to_user": "x", "status": "feasible",
            "summary": "x", "assumptions": [], "risks": [], "missing_information": [], "recommended_adjustments": [],
            "needs_web_research": False, "external_claims": [{"claim": "Fee is 10", "status": "verified_with_source"}]}
    assert schemas.validate_output("feasibility_assessment", feas) != []


def test_achievements_cannot_be_activity_based():
    ach = {"id": "a1", "title": "Streak", "unlock": {"type": "login_streak"}}
    journey = {"regions": [{"id": "r1", "title": "R", "order": 1}],
               "milestones": [{"id": "m1", "title": "M", "region_id": "r1", "success_criteria": ["x"]}],
               "nodes": [{"id": "n1", "type": "task", "title": "Do it", "region_id": "r1", "status": "available"}],
               "achievements": [ach]}
    assert schemas.validate("journey", journey)
