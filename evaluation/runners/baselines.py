"""A deliberately naive, schema-valid baseline.

It behaves like a generic assistant: always answers in English, asks a fixed questionnaire,
verifies everything, plans everything, never researches, treats every goal as safe. Its outputs are
valid JSON for every operation, so it scores 100% on schema validity — the other metrics show
whether the checks actually discriminate behaviour. It is a sanity instrument, not a competitor.
"""

_DS = {"what_changed": "Plan updated.", "why": "To help you.", "impact": "You will reach your goal."}


def _nodes(ctx):
    return (ctx.get("journey") or {}).get("nodes", [])


def naive_output(case: dict) -> dict:
    op, ctx = case["task_type"], case["input"]
    base = {"type": op, "response_language": "en", "message_to_user": "Sure! Here's what you asked for."}
    goal_title = (ctx.get("goal") or {}).get("title", "Your goal")

    if op == "goal_clarification":
        qs = [("What motivates you?", "motivation"), ("What is your deadline?", "deadline"),
              ("What is your budget?", "budget"), ("How experienced are you?", "experience"),
              ("How much time do you have?", "available_time")]
        return {**base, "ready_to_plan": False,
                "questions": [{"question": q, "targets": [t], "impact": "Helps personalise your plan."} for q, t in qs]}
    if op == "feasibility_assessment":
        return {**base, "status": "feasible", "summary": "Anything is possible with dedication.", "assumptions": [],
                "risks": [], "missing_information": [], "recommended_adjustments": [], "needs_web_research": False}
    if op == "journey_generation":
        return {**base, "goal": {"title": goal_title},
                "journey": {"regions": [{"id": "r1", "title": "Get started", "order": 1, "status": "active"}],
                            "milestones": [{"id": "m1", "title": "Reach the goal", "region_id": "r1", "success_criteria": ["Goal reached"]}],
                            "nodes": [{"id": "n1", "type": "task", "title": "Research the topic", "region_id": "r1", "milestone_id": "m1", "status": "available", "detail_level": "outline"},
                                      {"id": "n2", "type": "task", "title": "Practice every day", "region_id": "r1", "milestone_id": "m1", "status": "locked", "detail_level": "outline", "depends_on": ["n1"]}]},
                "decision_summary": _DS}
    if op == "task_generation":
        proto = {"task_nature": "other", "objective_verifiability": "low",
                 "methods": [{"method": "structured_self_report", "role": "required", "instructions": "Tell me what you did."}],
                 "pass_criteria": ["User says it is done"], "confidence_ceiling": "limited", "self_report_only": True,
                 "rationale": "Simple."}
        return {**base, "tasks": [
            {"id": "t1", "title": "Research the topic", "description": "Look into it.", "why_it_matters": "Knowledge.",
             "expected_result": "Better understanding.", "estimated_duration_minutes": 120, "difficulty": 2, "verification_protocol": proto},
            {"id": "t2", "title": "Practice", "description": "Practice a lot.", "why_it_matters": "Practice makes perfect.",
             "expected_result": "Improvement.", "estimated_duration_minutes": 120, "difficulty": 2, "verification_protocol": proto}]}
    if op == "verification_protocol_design":
        return {**base, "task_id": (ctx.get("task") or {}).get("id", "t1"),
                "protocol": {"task_nature": "other", "objective_verifiability": "high",
                             "methods": [{"method": "photo", "role": "required", "instructions": "Upload a photo."}],
                             "pass_criteria": ["Photo uploaded"], "confidence_ceiling": "high", "self_report_only": False,
                             "rationale": "Photos show the result."}}
    if op == "verification_result":
        crit = ((ctx.get("task") or {}).get("verification_protocol") or {}).get("pass_criteria") or ["Task done"]
        return {**base, "message_to_user": "Great job, verified!", "task_id": (ctx.get("task") or {}).get("id", "t1"),
                "attempt": len(ctx.get("verification_history") or []) + 1, "status": "verified", "confidence": "high",
                "evidence_basis": "objective", "criteria_results": [{"criterion": c[:300], "result": "met"} for c in crit],
                "reason": "The user submitted evidence.", "additional_evidence": [], "decision_summary": _DS}
    if op == "route_adaptation":
        return {**base, "trigger": {"type": "other", "description": "Things changed."}, "change_level": "major",
                "requires_user_confirmation": False,
                "removed_nodes": [{"node_id": n["id"], "reason": "Replaced."} for n in _nodes(ctx)],
                "added_nodes": [{"id": "x1", "type": "task", "title": "Start again with a new plan", "region_id": (ctx.get("journey") or {}).get("regions", [{"id": "r1"}])[0]["id"], "status": "available"}],
                "modified_nodes": [], "modified_deadlines": [], "preserved_progress": [], "decision_summary": _DS}
    if op == "daily_plan":
        todo = [n for n in _nodes(ctx) if n.get("status") in ("available", "in_progress", "locked")][:5] or [{"id": "n1"}]
        # capped per task so five tasks stay inside the schema's one-day maximum (1440 min)
        recs = [{"task_id": n["id"], "reason": "Good to do.",
                 "estimated_duration_minutes": min(n.get("estimated_duration_minutes", 60), 240)} for n in todo]
        return {**base, "available_minutes": max(1, (ctx.get("time_budget") or {}).get("available_minutes_today") or 60),
                "recommended_tasks": recs, "total_minutes": sum(r["estimated_duration_minutes"] for r in recs),
                "next_action": "Start with the first task."}
    if op == "navigator_response":
        return {**base, "intent": "other", "in_scope": True, "proposed_changes": [], "requires_user_confirmation": False,
                "decision_summary": None}
    if op == "goal_change":
        return {**base, "classification": "minor_adjustment", "updated_goal": {"title": goal_title},
                "preserved_progress": [], "discarded_progress": [{"node_id": n["id"], "reason": "Starting fresh."} for n in _nodes(ctx)],
                "recommend_separate_goal": False, "original_goal_handling": "updated_in_place",
                "requires_user_confirmation": False, "decision_summary": _DS}
    if op == "web_research_decision":
        return {"type": op, "needs_research": False, "reason_categories": ["none"], "rationale": "I know enough.",
                "facts_to_verify": [], "queries": [], "unsupported_claims": [], "can_proceed_without_research": True}
    if op == "safety_classification":
        return {**base, "category": "allowed", "domains": ["none"], "ai_role": "full_navigator",
                "professional_referral": {"needed": False}, "boundaries": [], "allowed_support": ["Everything"],
                "proceed_with_journey": True}
    if op == "memory_extraction":
        texts = [m["content"] for m in ctx.get("conversation", []) if m["role"] == "user"]
        return {"type": op, "items": [{"scope": "user", "category": "fact", "content": t[:1500], "stability": "stable",
                                       "sensitive": False} for t in texts][:12], "not_stored": []}
    if op == "progress_update":
        prog = ctx.get("progress") or {}
        cur = prog.get("current_level_index", 0)
        return {**base, "goal_progress": {"percent": 50, "basis": "Consistent app activity"},
                "level": {"current_index": min(cur + 1, 10), "current_title": "Level up", "changed": True,
                          "previous_index": cur, "reason": "Great streak in the app!", "based_on": []},
                "achievements_unlocked": []}
    raise ValueError(f"no naive baseline for {op}")
