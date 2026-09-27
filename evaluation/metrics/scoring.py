"""Score model outputs against evaluation cases and aggregate metrics.

No overall score is produced on purpose: results are reported per metric and per dimension.
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


def score_case(case: dict, output, parse_error=None) -> dict:
    op = case["task_type"]
    schema_errors = [parse_error] if parse_error else schemas.validate_output(op, output)
    schema_ok = not schema_errors
    lint = semantic.lint_output(op, output, case["input"], {}, case["language"], case.get("safety_category")) \
        if isinstance(output, dict) else []
    results = [run_check(chk, output, schema_ok, lint) for chk in case["checks"]]
    return {
        "case_id": case["id"],
        "task_type": op,
        "dimensions": case["dimensions"],
        "schema_ok": schema_ok,
        "schema_errors": schema_errors[:10],
        "lint": [str(i) for i in lint],
        "checks": [r.to_dict() for r in results],
        "passed_all": all(r.passed for r in results),
    }


def aggregate(scored: list) -> dict:
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
    return {
        "cases": len(scored),
        "cases_passing_all_checks": sum(1 for s in scored if s["passed_all"]),
        "metrics": metrics,
        "dimensions": dimensions,
    }
