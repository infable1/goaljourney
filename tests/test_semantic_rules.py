"""Unit tests for the behavioural lint rules (one rule per test, minimal fixtures)."""
from generation.validators.semantic import lint_output


def codes(op, out, ctx=None, ann=None, lang=None, safety=None):
    return {i.code for i in lint_output(op, out, ctx or {}, ann or {}, lang, safety)}


def protocol(methods, **kw):
    return {"task_nature": kw.get("nature", "other"), "objective_verifiability": kw.get("ov", "medium"),
            "methods": methods, "pass_criteria": ["x"], "confidence_ceiling": kw.get("ceiling", "medium"),
            "self_report_only": kw.get("sro", False), "rationale": "x"}


def vp_output(p):
    return {"type": "verification_protocol_design", "response_language": "en", "message_to_user": "Here is the check.",
            "task_id": "t1", "protocol": p}


def test_photo_only_protocol_is_rejected():
    p = protocol([{"method": "photo", "role": "required", "instructions": "Photo."}])
    assert "VP_PHOTO_ONLY" in codes("verification_protocol_design", vp_output(p))


def test_photo_with_questions_is_fine():
    p = protocol([{"method": "photo", "role": "required", "instructions": "Photo."},
                  {"method": "follow_up_questions", "role": "required", "instructions": "Q.", "questions": ["a?", "b?"]}])
    assert "VP_PHOTO_ONLY" not in codes("verification_protocol_design", vp_output(p))


def test_self_report_protocol_must_cap_confidence():
    p = protocol([{"method": "structured_self_report", "role": "required", "instructions": "Log."}], ov="low", ceiling="high")
    assert "VP_SELF_REPORT_CEILING" in codes("verification_protocol_design", vp_output(p))


def test_writing_task_needs_artifact_review():
    p = protocol([{"method": "structured_self_report", "role": "required", "instructions": "Tell me."}],
                 nature="writing", ov="high", ceiling="limited", sro=True)
    c = codes("verification_protocol_design", vp_output(p))
    assert {"VP_NATURE_MISMATCH", "VP_WEAK_FOR_VERIFIABLE"} <= c


def _vr(status, results, basis="objective", conf="high", extra=None):
    return {"type": "verification_result", "response_language": "en", "message_to_user": "Result.", "task_id": "t1",
            "attempt": 1, "status": status, "confidence": conf, "evidence_basis": basis,
            "criteria_results": [{"criterion": f"c{i}", "result": r} for i, r in enumerate(results)],
            "reason": "x", "additional_evidence": extra or [],
            "decision_summary": {"what_changed": "x", "why": "x", "impact": "x"}}


def test_cannot_verify_with_unmet_criteria():
    assert "VR_VERIFIED_UNMET" in codes("verification_result", _vr("verified", ["met", "unclear"]))


def test_photo_alone_cannot_verify():
    ctx = {"task": {"id": "t1"}, "evidence": [{"id": "e1", "type": "photo"}]}
    assert "VR_PHOTO_ONLY_VERIFIED" in codes("verification_result", _vr("verified", ["met"]), ctx)


def test_insufficient_evidence_is_not_rejection():
    assert "VR_REJECT_WITHOUT_FAILURE" in codes("verification_result", _vr("rejected", ["unclear"]))


def test_self_report_means_limited_confidence():
    ctx = {"task": {"id": "t1"}, "evidence": [{"id": "e1", "type": "structured_self_report"}]}
    c = codes("verification_result", _vr("verified", ["met"], basis="objective", conf="high"), ctx)
    assert {"VR_BASIS_MISMATCH"} <= c
    c2 = codes("verification_result", _vr("verified", ["met"], basis="self_report", conf="high"), ctx)
    assert "VR_SELF_REPORT_CONFIDENCE" in c2


def test_demanding_video_for_self_report_protocol():
    ctx = {"task": {"id": "t1", "verification_protocol": protocol(
        [{"method": "structured_self_report", "role": "required", "instructions": "Log."}], sro=True, ceiling="limited", ov="none")}}
    out = _vr("needs_more_evidence", ["met"], basis="self_report", conf="limited",
              extra=[{"request": "Send a video of each workout", "why": "proof"}])
    c = codes("verification_result", out, ctx)
    assert {"VR_DEMANDS_OBJECTIVE_FOR_SELF_REPORT", "VR_SELF_REPORT_DISMISSED"} <= c


JOURNEY = {"regions": [{"id": "r1", "title": "R", "order": 1}],
           "milestones": [{"id": "m1", "title": "M", "region_id": "r1", "success_criteria": ["x"]}],
           "nodes": [{"id": "n1", "type": "task", "title": "Done task", "region_id": "r1", "milestone_id": "m1", "status": "verified"},
                     {"id": "n2", "type": "task", "title": "Open task", "region_id": "r1", "milestone_id": "m1", "status": "available",
                      "depends_on": ["n1"], "estimated_duration_minutes": 30, "due_date": "2026-09-28"},
                     {"id": "n3", "type": "task", "title": "Blocked task", "region_id": "r1", "milestone_id": "m1", "status": "locked",
                      "depends_on": ["n2"], "estimated_duration_minutes": 30}]}


def _ra(**kw):
    base = {"type": "route_adaptation", "response_language": "en", "message_to_user": "Changed.",
            "trigger": {"type": "other", "description": "x"}, "change_level": "moderate", "requires_user_confirmation": False,
            "removed_nodes": [], "added_nodes": [], "modified_nodes": [], "modified_deadlines": [], "preserved_progress": ["n1"],
            "decision_summary": {"what_changed": "x", "why": "x", "impact": "x"}}
    base.update(kw)
    return base


def test_route_adaptation_must_preserve_completed_nodes():
    out = _ra(removed_nodes=[{"node_id": "n1", "reason": "x"}], preserved_progress=[])
    assert {"RA_REMOVED_COMPLETED"} <= codes("route_adaptation", out, {"journey": JOURNEY})


def test_major_change_requires_confirmation():
    out = _ra(change_level="major", removed_nodes=[{"node_id": "n3", "reason": "x"}])
    assert "RA_MAJOR_NO_CONFIRM" in codes("route_adaptation", out, {"journey": JOURNEY})


def test_time_change_must_respect_new_budget():
    out = _ra(trigger={"type": "less_time", "description": "x"}, new_weekly_hours_planned=10,
              removed_nodes=[{"node_id": "n3", "reason": "x"}])
    assert "RA_OVER_TIME" in codes("route_adaptation", out, {"journey": JOURNEY, "time_budget": {"hours_per_week": 3}})


def _dp(recs, avail=30):
    return {"type": "daily_plan", "response_language": "en", "message_to_user": "Today.", "available_minutes": avail,
            "recommended_tasks": recs, "total_minutes": sum(r["estimated_duration_minutes"] for r in recs), "next_action": "Start."}


def test_daily_plan_time_and_dependencies():
    ctx = {"today": "2026-09-27", "journey": JOURNEY, "time_budget": {"available_minutes_today": 30}}
    over = _dp([{"task_id": "n2", "reason": "x", "estimated_duration_minutes": 30},
                {"task_id": "n3", "reason": "x", "estimated_duration_minutes": 30}])
    assert "DP_OVER_TIME" in codes("daily_plan", over, ctx)
    blocked = _dp([{"task_id": "n3", "reason": "x", "estimated_duration_minutes": 30}])
    c = codes("daily_plan", blocked, ctx)
    assert {"DP_BLOCKED_TASK", "DP_IGNORED_DUE"} <= c
    good = _dp([{"task_id": "n2", "reason": "x", "estimated_duration_minutes": 30}])
    assert not {i for i in codes("daily_plan", good, ctx) if i.startswith("DP_")}


def test_clarification_rules():
    out = {"type": "goal_clarification", "response_language": "en", "message_to_user": "Questions below.", "ready_to_plan": False,
           "questions": [{"question": "When is your deadline?", "targets": ["deadline"], "impact": "Sets the pace of the plan."}]}
    c = codes("goal_clarification", out, {"goal": {"title": "x", "deadline": "2026-12-01"}},
              {"critical_targets": [["available_time"]]})
    assert {"Q_ASKS_KNOWN", "Q_MISSED_CRITICAL"} <= c


def test_claims_must_come_from_provided_research():
    out = {"type": "feasibility_assessment", "response_language": "en", "message_to_user": "Assessment.", "status": "feasible",
           "summary": "x", "assumptions": [], "risks": [], "missing_information": [], "recommended_adjustments": [],
           "needs_web_research": False,
           "external_claims": [{"claim": "Fee is 10", "status": "verified_with_source",
                                "source": {"title": "t", "url": "https://invented.example.com/x"}}]}
    assert "CLAIM_SOURCE_NOT_IN_CONTEXT" in codes("feasibility_assessment", out, {})
    ctx = {"research_results": [{"id": "r1", "finding": "x", "source": {"title": "t", "url": "https://invented.example.com/x"}}]}
    assert "CLAIM_SOURCE_NOT_IN_CONTEXT" not in codes("feasibility_assessment", out, ctx)


def test_levels_ignore_app_activity():
    out = {"type": "progress_update", "response_language": "en", "message_to_user": "Level up!",
           "goal_progress": {"percent": 40, "basis": "activity"},
           "level": {"current_index": 1, "current_title": "L1", "changed": True, "previous_index": 0,
                     "reason": "30-day streak", "based_on": []},
           "achievements_unlocked": []}
    c = codes("progress_update", out, {"progress": {"current_level_index": 0, "app_activity": {"streak_days": 30}}})
    assert {"PU_ACTIVITY_BASED", "PU_LEVEL_UNSUPPORTED", "PU_PROGRESS_WITHOUT_VERIFICATION"} <= c


def test_language_and_reasoning_leaks():
    out = {"type": "navigator_response", "response_language": "ru", "message_to_user": "Sure, here you go <think>plan</think>",
           "intent": "other", "in_scope": True, "proposed_changes": [], "requires_user_confirmation": False}
    c = codes("navigator_response", out, {}, lang="ru")
    assert {"LANG_SCRIPT", "EXPOSED_REASONING"} <= c


def test_memory_leak_annotation():
    out = {"type": "navigator_response", "response_language": "en", "message_to_user": "Given your knee injury, rest.",
           "intent": "other", "in_scope": True, "proposed_changes": [], "requires_user_confirmation": False}
    assert "MEMORY_LEAK" in codes("navigator_response", out, {}, {"must_not_mention": ["knee"]})


def test_safety_rules():
    base = {"type": "safety_classification", "response_language": "en", "message_to_user": "Declined.", "domains": ["illegal_activity"],
            "professional_referral": {"needed": False}, "boundaries": ["No"], "allowed_support": [], "proceed_with_journey": True}
    assert "S_RESTRICTED_PROCEED" in codes("safety_classification", {**base, "category": "restricted", "ai_role": "declined"})
    assert "S_OVER_REFUSAL" in codes("safety_classification", {**base, "category": "allowed", "ai_role": "declined"})
    assert "S_CATEGORY_MISMATCH" in codes("safety_classification", {**base, "category": "allowed", "ai_role": "full_navigator"},
                                          safety="high_risk")
