"""Score model outputs against evaluation cases and aggregate metrics.

No overall score is produced on purpose: results are reported per metric and per dimension.

A *unit* is one model call. Atomic cases are one unit; composite and longitudinal cases (eval
v0.2.0) have one unit per step, id `<case_id>/<step_id>`, each on a canonical (teacher-forced)
input, so a mistake in one step never cascades into the next and every step is scored on its own.
A case passes only if all of its units pass. Outputs are validated and linted against the case's
`schema_version` (default 0.1.0, the contract of evaluation v0.1.0).
"""
import json
import re
from collections import defaultdict

from gjcore import schemas
from generation.validators import semantic

from .checks import LOWER_IS_BETTER, run_check


def extract_json(raw: str):
    """Parse the model's raw text into a JSON object. Tolerates code fences, nothing else."""
    if raw is None:
        return None, "empty output"
    s = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", s, re.DOTALL)
    if fence:
        s = fence.group(1)
    try:
        obj = json.loads(s)
    except json.JSONDecodeError as e:
        return None, f"not valid JSON: {e}"
    if not isinstance(obj, dict):
        return None, "top-level JSON value is not an object"
    return obj, None


CASE_FIELDS = ("language", "input_language", "domain", "safety_category", "dimensions", "schema_version",
               "case_type", "strata", "adversarial", "scenario_group", "title", "human_review_focus")


def expand_units(case: dict) -> list:
    """The model calls a case consists of: the case itself (atomic) or one unit per step."""
    if not case.get("steps"):
        return [{**case, "unit_id": case["id"], "case_id": case["id"], "step_id": None,
                 "case_type": case.get("case_type", "atomic")}]
    units = []
    for st in case["steps"]:
        unit = {k: case[k] for k in CASE_FIELDS if k in case}
        unit.update({"id": f"{case['id']}/{st['step_id']}", "unit_id": f"{case['id']}/{st['step_id']}",
                     "case_id": case["id"], "step_id": st["step_id"], "task_type": st["task_type"],
                     "input": st["input"], "checks": st["checks"]})
        if "reference_output" in st:
            unit["reference_output"] = st["reference_output"]
        if st.get("human_review_focus"):
            unit["human_review_focus"] = st["human_review_focus"]
        if st.get("title"):
            unit["step_title"] = st["title"]
        units.append(unit)
    return units


def score_case(case: dict, output, parse_error=None) -> dict:
    """Score one unit (an atomic case or one step of a multi-step case)."""
    op = case["task_type"]
    version = case.get("schema_version", "0.1.0")
    schema_errors = [parse_error] if parse_error else schemas.validate_output(op, output, version)
    schema_ok = not schema_errors
    lint = semantic.lint_output(op, output, case["input"], {}, case["language"], case.get("safety_category"), version) \
        if isinstance(output, dict) else []
    results = [run_check(chk, output, schema_ok, lint) for chk in case["checks"]]
    return {
        "case_id": case.get("case_id", case["id"]),
        "unit_id": case.get("unit_id", case["id"]),
        "step_id": case.get("step_id"),
        "case_type": case.get("case_type", "atomic"),
        "task_type": op,
        "dimensions": case["dimensions"],
        "schema_ok": schema_ok,
        "schema_errors": schema_errors[:10],
        "lint": [str(i) for i in lint],
        "checks": [r.to_dict() for r in results],
        "passed_all": all(r.passed for r in results),
    }


def aggregate(scored: list) -> dict:
    """Metrics over units; case-level pass counts, overall and per case type."""
    by_metric = defaultdict(lambda: {"bad": 0, "total": 0, "checks": 0, "failed_checks": 0, "cases": set()})
    by_dim = defaultdict(lambda: {"checks": 0, "passed": 0, "cases": set()})
    for s in scored:
        for r in s["checks"]:
            m = by_metric[r["metric"]]
            m["bad"] += r["bad"]
            m["total"] += r["total"]
            m["checks"] += 1
            m["failed_checks"] += 0 if r["passed"] else 1
            m["cases"].add(s["case_id"])
            d = by_dim[r["dimension"]]
            d["checks"] += 1
            d["passed"] += 1 if r["passed"] else 0
            d["cases"].add(s["case_id"])
    metrics = {}
    for name, m in sorted(by_metric.items()):
        if m["total"]:
            rate = m["bad"] / m["total"]
            value = rate if name in LOWER_IS_BETTER else 1 - rate
        else:
            value = None
        metrics[name] = {
            "value": None if value is None else round(value, 4),
            "direction": "lower_is_better" if name in LOWER_IS_BETTER else "higher_is_better",
            "numerator_bad": m["bad"], "denominator": m["total"],
            "checks": m["checks"], "failed_checks": m["failed_checks"], "cases": len(m["cases"]),
        }
    dimensions = {
        name: {"check_pass_rate": round(d["passed"] / d["checks"], 4), "checks": d["checks"], "cases": len(d["cases"])}
        for name, d in sorted(by_dim.items())
    }
    cases, ctype = {}, {}
    for s in scored:
        cid = s.get("case_id", s.get("unit_id"))
        cases[cid] = cases.get(cid, True) and s["passed_all"]
        ctype[cid] = s.get("case_type", "atomic")
    by_type = defaultdict(lambda: {"cases": 0, "passing": 0, "units": 0, "units_passing": 0})
    for s in scored:
        t = by_type[s.get("case_type", "atomic")]
        t["units"] += 1
        t["units_passing"] += 1 if s["passed_all"] else 0
    for cid, ok in cases.items():
        t = by_type[ctype[cid]]
        t["cases"] += 1
        t["passing"] += 1 if ok else 0
    return {
        "cases": len(cases),
        "units": len(scored),
        "cases_passing_all_checks": sum(cases.values()),
        "units_passing_all_checks": sum(1 for s in scored if s["passed_all"]),
        "by_case_type": {k: dict(v) for k, v in sorted(by_type.items())},
        "metrics": metrics,
        "dimensions": dimensions,
    }
