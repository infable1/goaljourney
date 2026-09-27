"""Helpers for authoring evaluation v0.2.0 cases (see docs/EVALUATION_V0.2_DESIGN.md).

Cases are authored as Python data so that shared structure (checks, decision summaries, request
envelopes) is written once; `gj eval build-cases` renders them to evaluation/cases/v0.2.0/*.yaml.
Edit the builder, not the YAML: a test fails when the two drift apart.
"""

EVAL_VERSION = "0.2.0"
SCHEMA_VERSION = "0.1.1"

SEEDS = []       # evaluation seeds: independent situations written before the cases
SCENARIOS = []   # side=eval behavioural scenarios (merged into data/scenarios/behavioural_scenarios.yaml)
CASES = []


def seed(sid, language, domain, situation, twists=()):
    """Register an evaluation seed: the situation the case(s) are written from."""
    SEEDS.append({"id": sid, "language": language, "domain": domain, "situation": situation, "twists": list(twists)})
    return sid


def scenario(sid, operation, trigger, condition, decision, description):
    SCENARIOS.append({"id": sid, "side": "eval", "operation": operation, "trigger": trigger, "condition": condition,
                      "decision": decision, "description": description})
    return sid


def ctx(op, today, **kw):
    return {"operation": op, "today": today, **kw}


def say(*turns):
    """conversation: alternating user/assistant turns starting with the user; prefix 'A:' marks an assistant turn."""
    out = []
    for t in turns:
        if t.startswith("A:"):
            out.append({"role": "assistant", "content": t[2:].strip()})
        else:
            out.append({"role": "user", "content": t})
    return out


def ds(what, why, impact, alternatives=None):
    d = {"what_changed": what, "why": why, "impact": impact}
    if alternatives:
        d["alternatives_considered"] = [{"option": o, "why_not": w} for o, w in alternatives]
    return d


def c(check, metric, **kw):
    return {"check": check, "metric": metric, **kw}


def base_checks(language):
    return [c("schema_valid", "schema_validity"), c("semantic_clean", "semantic_validity"),
            c("language", "language_match", value=language)]


def lint_absent(metric, *codes, note=None):
    chk = c("lint_absent", metric, codes=list(codes))
    if note:
        chk["note"] = note
    return chk


def step(step_id, task_type, input_, checks, reference, focus=(), pattern=None, title=None):
    s = {"step_id": step_id, "task_type": task_type, "input": input_, "checks": checks, "reference_output": reference}
    if title:
        s["title"] = title
    if focus:
        s["human_review_focus"] = list(focus)
    if pattern:
        s["step_pattern"] = pattern
    return s


def case(cid, *, title, case_type, seed_id, scenario_group, strata, dimensions, language, input_language, domain,
         focus, adversarial=(), safety="allowed", task_type=None, input=None, checks=None, reference=None, steps=None,
         notes=None):
    d = {"id": cid, "eval_version": EVAL_VERSION, "schema_version": SCHEMA_VERSION, "title": title, "case_type": case_type,
         "scenario_group": scenario_group, "seed_id": seed_id, "strata": list(strata)}
    if adversarial:
        d["adversarial"] = list(adversarial)
    d.update({"dimensions": list(dimensions), "language": language, "input_language": input_language, "domain": domain,
              "safety_category": safety})
    if steps:
        d["steps"] = steps
    else:
        d.update({"task_type": task_type, "input": input, "checks": checks})
    d["human_review_focus"] = list(focus)
    if reference is not None:
        d["reference_output"] = reference
    d["reference_status"] = "draft_unreviewed"
    if notes:
        d["notes"] = notes
    CASES.append(d)
    return d


def protocol(nature, verifiability, methods, pass_criteria, ceiling, self_report_only, rationale):
    return {"task_nature": nature, "objective_verifiability": verifiability, "methods": methods,
            "pass_criteria": pass_criteria, "confidence_ceiling": ceiling, "self_report_only": self_report_only,
            "rationale": rationale}


def m(method, role, instructions, **kw):
    return {"method": method, "role": role, "instructions": instructions, **kw}


def task(tid, title, description, why, result, minutes, difficulty, vp=None, **kw):
    t = {"id": tid, "title": title, "description": description, "why_it_matters": why, "expected_result": result,
         "estimated_duration_minutes": minutes, "difficulty": difficulty, **kw}
    if vp:
        t["verification_protocol"] = vp
    return t


def node(nid, title, region, milestone, status, minutes=None, depends=(), **kw):
    n = {"id": nid, "type": kw.pop("type", "task"), "title": title, "region_id": region, "milestone_id": milestone,
         "status": status}
    if depends:
        n["depends_on"] = list(depends)
    if minutes:
        n["estimated_duration_minutes"] = minutes
    n.update(kw)
    return n
