"""Candidate generation: scenario x operation -> validated candidate record.

Stage 1 (input): the teacher writes the request object for the scenario.
Stage 2 (output): the teacher writes the ideal output for that input.
Stage 3 (optional): the teacher writes a rejected output for a failure mode.
Every stage is validated; failures are kept with reasons (never silently dropped).
Candidates are NOT training data until a human approves them (see gj review).
"""
import re
from datetime import date

from gjcore import schemas
from gjcore.config import load_config, versions
from generation.validators.records import validate_example
from generation.validators import semantic
from generation.pipelines.pool import load_pool, load_review_events, review_status
from evaluation.metrics.scoring import extract_json

from . import prompting

OP_BEHAVIOR = {
    "goal_clarification": ["clarification"], "feasibility_assessment": ["feasibility"],
    "journey_generation": ["journey"], "task_generation": ["task", "verification_protocol"],
    "verification_protocol_design": ["verification_protocol"], "verification_result": ["verification_decision"],
    "route_adaptation": ["route_adaptation"], "daily_plan": ["daily_prioritization"],
    "navigator_response": ["navigator"], "goal_change": ["goal_change"], "web_research_decision": ["web_research"],
    "safety_classification": ["safety"], "memory_extraction": ["memory"], "progress_update": ["progress"],
}

# Failure modes that make sense to demonstrate for each operation (contrastive stage).
OP_FAILURE_MODES = {
    "goal_clarification": {"unnecessary_questions", "asked_known_information", "missed_critical_question", "assumed_user_info", "wrong_language"},
    "feasibility_assessment": {"blind_compliance", "over_refusal", "unverified_current_facts", "exposed_reasoning"},
    "journey_generation": {"generic_plan", "vague_tasks", "overplanning", "ignored_available_time", "ignored_deadline", "ignored_preferences", "unverified_current_facts"},
    "task_generation": {"vague_tasks", "ignored_available_time", "ignored_preferences", "overplanning", "generic_verification"},
    "verification_protocol_design": {"photo_as_proof", "generic_verification", "assumed_user_info"},
    "verification_result": {"accepted_unsupported_proof", "rejected_reasonable_self_report", "premature_rejection", "photo_as_proof"},
    "route_adaptation": {"silent_route_change", "discarded_progress", "ignored_available_time", "ignored_deadline", "unverified_current_facts"},
    "daily_plan": {"ignored_available_time", "overplanning", "ignored_deadline", "memory_leak"},
    "navigator_response": {"overrode_user_decision", "generic_assistant_drift", "silent_route_change", "wrong_language"},
    "goal_change": {"discarded_progress", "goal_change_misclassified", "silent_route_change"},
    "web_research_decision": {"unnecessary_research", "unverified_current_facts"},
    "safety_classification": {"unsafe_compliance", "over_refusal", "pretended_professional"},
    "memory_extraction": {"memory_leak"},
    "progress_update": {"activity_based_progress"},
}


class StageError(Exception):
    def __init__(self, stage, reason, raw=None):
        super().__init__(f"{stage}: {reason}")
        self.stage, self.reason, self.raw = stage, reason, raw


def next_generated_number():
    nums = [int(m.group(1)) for rec, _, _ in load_pool() if (m := re.fullmatch(r"gj-gen-(\d+)", rec.get("id", "")))]
    return max(nums, default=0) + 1


def pick_few_shot(operation, domain):
    cfg = load_config("generation")["few_shot"]
    if cfg["max_examples"] < 1:
        return None
    events = load_review_events()
    candidates = [r for r, _, origin in load_pool(include_generated=False) if r["task_type"] == operation
                  and (not cfg["require_approved"] or review_status(r, events) == "approved")]
    candidates.sort(key=lambda r: (r["domain"] == domain, r["id"]))  # prefer a different domain
    return candidates[0] if candidates else None


def _parse(stage, raw):
    obj, err = extract_json(raw)
    if err:
        raise StageError(stage, err, raw)
    return obj


def generate_candidate(provider, scenario, operation, number, run_id, today=None, with_contrastive=False, call=None):
    """Return (record, notes). Raises StageError with the failing stage and reason."""
    call = call or (lambda system, user: provider.complete(system, user))
    today = today or date.today().isoformat()
    system = prompting.template("system.md")

    raw1 = call(system, prompting.stage1_prompt(scenario, operation, today))
    input_ctx = _parse("input", raw1)
    input_ctx["operation"], input_ctx["today"] = operation, today
    errs = schemas.validate("input_context", input_ctx)
    if errs:
        raise StageError("input", f"input_context schema: {errs[:3]}", raw1)

    few_shot = pick_few_shot(operation, scenario["domain"])
    raw2 = call(system, prompting.stage2_prompt(operation, input_ctx, few_shot))
    output = _parse("output", raw2)

    behavior = list(OP_BEHAVIOR[operation])
    if operation == "verification_result" and input_ctx.get("verification_history"):
        behavior.append("verification_retry")
    if operation == "route_adaptation" and (output.get("trigger") or {}).get("type") in {"less_time", "more_time"}:
        behavior.append("time_adaptation")
    if output.get("decision_summary"):
        behavior.append("decision_summary")

    v = versions()
    record = {
        "id": f"gj-gen-{number:05d}", "schema_version": v["schema_version"], "task_type": operation,
        "behavior": behavior, "language": scenario["language"], "input_language": scenario["input_language"],
        "domain": scenario["domain"], "difficulty": scenario.get("difficulty", "medium"),
        "goal_size": scenario["goal_size"], "tags": sorted(set(scenario.get("tags", [])))[:12],
        "safety_category": scenario["safety_category"], "scenario_group": scenario["id"],
        "input": input_ctx, "expected_output": output,
        "provenance": {"source": "synthetic", "method": "pipeline_generated", "author": "generation-pipeline",
                       "created": today, "license": "proprietary-internal", "generation_run_id": run_id,
                       "prompt_version": v["generation_prompt_version"],
                       "generator_model": f"{provider.name}:{provider.model}" if provider else "unknown"},
    }
    rep = validate_example(record)
    if not rep.ok:
        raise StageError("output", f"validation: {rep.errors[:5]}", raw2)
    notes = list(rep.warnings)

    modes = [m for m in scenario.get("contrastive_failure_modes", []) if m in OP_FAILURE_MODES[operation]]
    if with_contrastive and modes:
        mode = modes[number % len(modes)]
        raw3 = call(system, prompting.stage3_prompt(operation, input_ctx, output, [mode]))
        obj = _parse("contrastive", raw3)
        record["contrastive"] = [{"id": f"{record['id']}-c1", "failure_modes": [mode],
                                  "output": obj.get("output"), "critique": obj.get("critique") or "(missing)"}]
        rep = validate_example(record)
        if not rep.ok:
            notes.append(f"contrastive dropped: {rep.errors[:3]}")
            record.pop("contrastive")
        elif mode in semantic.ALWAYS_DETECTABLE and not rep.contrastive[0].detected_modes:
            notes.append("contrastive dropped: failure not detectable")
            record.pop("contrastive")
    return record, notes
