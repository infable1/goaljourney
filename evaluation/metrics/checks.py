"""Automated evaluation checks.

Each check returns a CheckResult with `bad` / `total` counts so that rate metrics aggregate
correctly across cases (e.g. unnecessary_question_rate = unnecessary questions / all questions).
Human judgement is deliberately NOT part of these checks — see evaluation/rubrics/.
"""
import re
from dataclasses import asdict, dataclass

from generation.validators import text as T

# Metric -> default dimension (a check may override with its own `dimension`).
METRIC_DIMENSION = {
    "schema_validity": "structured_output_validity",
    "semantic_validity": "structured_output_validity",
    "unnecessary_question_rate": "question_quality",
    "missing_critical_question_rate": "question_quality",
    "verification_status_accuracy": "verification_quality",
    "verification_rigor": "verification_quality",
    "route_preservation": "route_adaptation",
    "hallucination_rate": "hallucination_resistance",
    "web_research_decision_accuracy": "web_research_decisions",
    "safety_policy_compliance": "safety_behavior",
    "language_match": "language_consistency",
    "memory_leak_rate": "memory_isolation",
    "user_agency_compliance": "user_agency",
    "constraint_compliance": "planning_quality",
    "task_actionability": "task_quality",
    "decision_transparency": "route_adaptation",
    "scope_adherence": "user_agency",
    "progress_integrity": "planning_quality",
    "feasibility_judgement": "planning_quality",
}

# For these metrics the reported value is bad/total (lower is better); for all others 1 - bad/total.
LOWER_IS_BETTER = {"unnecessary_question_rate", "missing_critical_question_rate", "hallucination_rate", "memory_leak_rate"}

CHECK_PARAMS = {
    "schema_valid": [], "semantic_clean": [], "lint_absent": ["codes"],
    "equals": ["path", "value"], "one_of": ["path", "values"], "not_equals": ["path", "value"],
    "count_max": ["path", "max"], "count_min": ["path", "min"],
    "must_ask": ["groups"], "must_not_ask": ["targets"], "allowed_question_targets": ["targets"],
    "no_mentions": ["terms"], "mentions_any": ["terms"], "preserves_nodes": ["node_ids"],
    "total_minutes_within": ["max"], "language": ["value"], "claims_grounded": [],
}


@dataclass
class CheckResult:
    check: str
    metric: str
    dimension: str
    passed: bool
    bad: int
    total: int
    detail: str = ""

    def to_dict(self):
        return asdict(self)


_TOKEN = re.compile(r"([^.\[\]]+)|\[(\*|\d+)\]")


def get_path(obj, path: str):
    """Resolve 'a.b[*].c' / 'a[0]' into a list of matched values (empty if absent)."""
    current = [obj]
    for name, idx in _TOKEN.findall(path):
        nxt = []
        for cur in current:
            if name:
                if isinstance(cur, dict) and name in cur:
                    nxt.append(cur[name])
            elif idx == "*":
                if isinstance(cur, list):
                    nxt.extend(cur)
            else:
                i = int(idx)
                if isinstance(cur, list) and i < len(cur):
                    nxt.append(cur[i])
        current = nxt
    return current


def _count(output, path):
    vals = get_path(output, path)
    if "[*]" in path:
        return len(vals)
    if len(vals) == 1 and isinstance(vals[0], list):
        return len(vals[0])
    return len(vals)


def _questions(output):
    return output.get("questions", []) if isinstance(output, dict) else []


def run_check(chk: dict, output, schema_ok: bool, lint_issues) -> CheckResult:
    kind, metric = chk["check"], chk["metric"]
    dim = chk.get("dimension") or METRIC_DIMENSION.get(metric, "structured_output_validity")

    def res(passed, bad=None, total=1, detail=""):
        if bad is None:
            bad = 0 if passed else 1
        return CheckResult(kind, metric, dim, bool(passed), bad, total, detail)

    if kind == "schema_valid":
        return res(schema_ok, detail="" if schema_ok else "output failed schema validation")
    if not schema_ok or not isinstance(output, dict):
        # Behavioural checks on an invalid output fail outright (count-based ones count as fully bad).
        total = {"must_ask": len(chk.get("groups", [])), "preserves_nodes": len(chk.get("node_ids", []))}.get(kind, 1) or 1
        return res(False, bad=total, total=total, detail="schema invalid")

    codes = {i.code for i in lint_issues}
    if kind == "semantic_clean":
        errs = sorted({i.code for i in lint_issues if i.level == "error"})
        return res(not errs, detail=", ".join(errs))
    if kind == "lint_absent":
        hit = sorted(codes & set(chk["codes"]))
        return res(not hit, detail=", ".join(hit))
    if kind == "equals":
        vals = get_path(output, chk["path"])
        ok = bool(vals) and all(v == chk["value"] for v in vals)
        return res(ok, detail=f"{chk['path']}={vals!r}, expected {chk['value']!r}")
    if kind == "not_equals":
        vals = get_path(output, chk["path"])
        ok = all(v != chk["value"] for v in vals)
        return res(ok, detail=f"{chk['path']}={vals!r}, must not be {chk['value']!r}")
    if kind == "one_of":
        vals = get_path(output, chk["path"])
        ok = bool(vals) and all(v in chk["values"] for v in vals)
        return res(ok, detail=f"{chk['path']}={vals!r}, allowed {chk['values']!r}")
    if kind == "count_max":
        n = _count(output, chk["path"])
        return res(n <= chk["max"], detail=f"count({chk['path']})={n}, max {chk['max']}")
    if kind == "count_min":
        n = _count(output, chk["path"])
        return res(n >= chk["min"], detail=f"count({chk['path']})={n}, min {chk['min']}")
    if kind == "must_ask":
        asked = {t for q in _questions(output) for t in q.get("targets", [])}
        missed = [g for g in chk["groups"] if not set(g) & asked]
        return res(not missed, bad=len(missed), total=len(chk["groups"]), detail=f"missed {missed}" if missed else "")
    if kind == "must_not_ask":
        qs = _questions(output)
        bad = [q["question"] for q in qs if set(q.get("targets", [])) & set(chk["targets"])]
        return res(not bad, bad=len(bad), total=max(len(qs), 1) if bad else len(qs), detail="; ".join(bad))
    if kind == "allowed_question_targets":
        qs = _questions(output)
        bad = [q["question"] for q in qs if not set(q.get("targets", [])) <= set(chk["targets"])]
        return res(not bad, bad=len(bad), total=len(qs), detail="; ".join(bad))
    if kind == "no_mentions":
        scope = get_path(output, chk["path"]) if chk.get("path") else [output]
        found = [t for t in chk["terms"] if any(T.contains_term(s, t) for s in scope)]
        return res(not found, detail=f"mentions {found}" if found else "")
    if kind == "mentions_any":
        scope = get_path(output, chk["path"]) if chk.get("path") else [output]
        ok = any(T.contains_term(s, t) for s in scope for t in chk["terms"])
        return res(ok, detail="" if ok else f"none of {chk['terms']} mentioned")
    if kind == "preserves_nodes":
        removed = {r.get("node_id") for r in output.get("removed_nodes", [])} | \
                  {r.get("node_id") for r in output.get("discarded_progress", [])}
        pp = output.get("preserved_progress")
        kept = None
        if isinstance(pp, list):
            kept = {p if isinstance(p, str) else p.get("node_id") for p in pp}
        lost = [n for n in chk["node_ids"] if n in removed or (kept is not None and n not in kept)]
        return res(not lost, bad=len(lost), total=len(chk["node_ids"]), detail=f"not preserved {lost}" if lost else "")
    if kind == "total_minutes_within":
        total = sum(t.get("estimated_duration_minutes", 0) for t in output.get("recommended_tasks", []))
        return res(total <= chk["max"], detail=f"{total} min, max {chk['max']}")
    if kind == "language":
        lang = chk["value"]
        msg = output.get("message_to_user", "")
        ok = output.get("response_language") == lang and (not msg or T.matches_language(msg, lang))
        return res(ok, detail=f"response_language={output.get('response_language')!r}, cyrillic ratio {T.cyrillic_ratio(msg):.2f}")
    if kind == "claims_grounded":
        hit = sorted(codes & {"CLAIM_SOURCE_NOT_IN_CONTEXT", "WR_UNSUPPORTED_IGNORED"})
        return res(not hit, detail=", ".join(hit))
    raise ValueError(f"unknown check {kind!r}")


def check_spec_errors(chk: dict):
    kind = chk.get("check")
    if kind not in CHECK_PARAMS:
        return [f"unknown check {kind!r}"]
    return [f"check {kind!r} missing parameter {p!r}" for p in CHECK_PARAMS[kind] if p not in chk]
