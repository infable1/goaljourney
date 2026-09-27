import json

import pytest

from gjcore.paths import repo_path
from gjcore.records import load_eval_cases, load_examples
from evaluation.metrics.checks import get_path
from evaluation.metrics.scoring import aggregate, extract_json, score_case
from evaluation.runners.baselines import naive_output
from evaluation.runners.validate_cases import validate_cases
from generation.validators import similarity

CASES = [c for c, _ in load_eval_cases(repo_path("evaluation/cases/v0.1.0"))]


def test_cases_validate_and_references_pass_their_checks():
    s = validate_cases()
    assert s["invalid"] == [], s["invalid"]
    assert 20 <= s["cases"] <= 30
    assert len(s["dimensions"]) == 12  # every evaluation dimension is covered


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


def test_no_leakage_between_training_pool_and_eval_cases():
    pool = [(r["id"], similarity.signature_text(r["input"])) for r, _ in load_examples(repo_path("data/raw/examples"))]
    cases = [(c["id"], similarity.signature_text(c["input"])) for c in CASES]
    assert similarity.cross_near_duplicates(pool, cases, 0.55) == []
