import pytest

from gjcore.paths import repo_path
from gjcore.records import flow_style_issues, load_examples
from generation.validators.records import check_unique_ids, validate_example

EXAMPLES = [r for r, _ in load_examples(repo_path("data/raw/examples"))]


@pytest.mark.parametrize("record", EXAMPLES, ids=[r["id"] for r in EXAMPLES])
def test_example_is_valid(record):
    rep = validate_example(record)
    assert rep.ok, "\n".join(rep.errors)


def test_example_ids_unique():
    assert check_unique_ids(EXAMPLES) == []


def test_no_misplit_yaml_prose():
    issues = [(f, i) for f in sorted(repo_path("data/raw/examples").glob("*.yaml")) for i in flow_style_issues(f)]
    assert issues == []


def test_pool_covers_every_operation_and_behaviour():
    from gjcore import schemas
    ops = set(schemas.OPERATION_SCHEMAS)
    assert {r["task_type"] for r in EXAMPLES} == ops
    required = {"clarification", "feasibility", "journey", "task", "verification_protocol", "verification_decision",
                "verification_retry", "route_adaptation", "navigator", "daily_prioritization", "time_adaptation",
                "goal_change", "decision_summary", "web_research", "safety", "memory", "progress", "language"}
    assert required <= {b for r in EXAMPLES for b in r["behavior"]}


def test_pool_diversity_minimums():
    langs = {r["language"] for r in EXAMPLES}
    assert langs == {"ru", "en"}
    assert sum(r["input_language"] == "mixed" for r in EXAMPLES) >= 3
    assert {r["safety_category"] for r in EXAMPLES} == {"allowed", "sensitive", "high_risk", "needs_professional_support", "restricted"}
    assert len({r["domain"] for r in EXAMPLES}) >= 15
    assert len({r["scenario_group"] for r in EXAMPLES}) == len(EXAMPLES)


def test_important_failure_modes_have_several_contrastive_examples():
    from collections import Counter
    counts = Counter(m for r in EXAMPLES for c in r.get("contrastive") or [] for m in c["failure_modes"])
    important = ["unnecessary_questions", "generic_plan", "vague_tasks", "assumed_user_info", "photo_as_proof",
                 "accepted_unsupported_proof", "rejected_reasonable_self_report", "overplanning",
                 "ignored_available_time", "ignored_deadline", "ignored_preferences", "silent_route_change",
                 "unverified_current_facts", "generic_assistant_drift", "overrode_user_decision"]
    assert {m: counts[m] for m in important if counts[m] < 2} == {}
