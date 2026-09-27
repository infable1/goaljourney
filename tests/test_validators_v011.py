"""Deterministic validators added in v0.1.1 (docs/POLICY_DECISIONS_v0.1.1.md): calendar, arithmetic,
deadline autonomy, capabilities, evidence classes, fact provenance, Russian voice — and version gating."""
import copy
from datetime import date

import pytest

from generation.validators import calendar as CAL
from generation.validators import policy as POL
from generation.validators import provenance as PROV
from generation.validators import quantities as Q
from generation.validators import russian as RU
from generation.validators import workload as W
from generation.validators.semantic import lint_input, lint_output

TODAY = date(2026, 9, 27)  # a Sunday


def codes(op, out, ctx=None, version="0.1.1", lang="ru"):
    return {i.code for i in lint_output(op, out, ctx or {}, {}, lang, None, version)}


# ----------------------------------------------------------------------------- calendar

@pytest.mark.parametrize("text", [
    "позвоню в воскресенье 5-го", "Sunday, October 5", "2026-10-05 (Sunday)", "завтра, во вторник",
    "в субботу, 4 октября", "October 3 (Friday)",
])
def test_weekday_mismatches_are_found(text):
    assert CAL.weekday_mismatches(text, TODAY)


@pytest.mark.parametrize("text", [
    "позвоню в понедельник, 5-го", "Monday, October 5", "2026-10-05 (Monday)", "завтра, в понедельник",
    "в субботу, 3 октября", "с понедельника по пятницу 5 часов", "в субботу и воскресенье, 3 и 4 октября",
    "по субботам 2 часа", "сегодня воскресенье",
])
def test_correct_or_unpaired_weekdays_pass(text):
    assert CAL.weekday_mismatches(text, TODAY) == []


def test_mentions_and_grounds_dates():
    d = date(2026, 11, 23)
    assert CAL.mentions_date("перенесём на 23 ноября", d, TODAY)
    assert CAL.mentions_date("moved to November 23", d, TODAY)
    assert not CAL.mentions_date("moved to November 24", d, TODAY)
    assert CAL.date_grounded("я в командировке до пятницы", date(2026, 10, 2), TODAY)
    assert not CAL.date_grounded("я в командировке до пятницы", date(2026, 10, 9), TODAY)


# ----------------------------------------------------------------------------- workload & quantities

def _journey(nodes, milestones=None):
    return {"regions": [{"id": "r1", "title": "R", "order": 1}],
            "milestones": milestones or [{"id": "m1", "title": "Первый этап", "region_id": "r1", "success_criteria": ["x"],
                                          "target_date": "2026-12-20"}],
            "nodes": nodes}


def _node(nid, minutes, status="available", milestone="m1"):
    n = {"id": nid, "type": "task", "title": f"Задача {nid}", "region_id": "r1", "milestone_id": milestone, "status": status}
    if minutes:
        n["estimated_duration_minutes"] = minutes
    return n


CTX = {"operation": "route_adaptation", "today": "2026-09-27",
       "goal": {"id": "g1", "title": "Цель", "deadline": "2027-03-01"},
       "time_budget": {"hours_per_week": 3, "previous_hours_per_week": 10},
       "journey": _journey([_node("n1", 1500, "verified"), _node("n2", 1500), _node("n3", 1800), _node("n4", 900, milestone="m2")],
                           [{"id": "m1", "title": "Первый этап", "region_id": "r1", "success_criteria": ["x"], "target_date": "2026-12-20"},
                            {"id": "m2", "title": "Второй этап", "region_id": "r1", "success_criteria": ["x"], "target_date": "2027-02-15"}])}


def test_remaining_work_and_pace():
    total, missing = W.total_minutes(W.unfinished_nodes(CTX))
    assert (total, missing) == (4200, [])
    assert W.weeks_needed(TODAY, 70, 3) == pytest.approx(23.43, abs=0.15)
    phases = [{"from": "2026-09-28", "to": "2026-10-11", "weekly_hours": 15}]
    assert W.capacity_hours(TODAY, date(2026, 10, 11), 3, phases) == pytest.approx(30, abs=0.1)


def test_text_quantities_must_follow_from_the_plan():
    out = {"type": "route_adaptation", "workload": {}, "removed_nodes": [], "added_nodes": [], "modified_nodes": [],
           "modified_deadlines": []}
    vals = Q.derivable(CTX, out)
    assert Q.underivable("Осталось около 70 часов работы.", vals) == []
    assert Q.underivable("Осталось около 95 часов работы.", vals)          # counts the verified node
    assert Q.underivable("about 95 hours of remaining work", vals)
    assert Q.underivable("realistic at 3 h/week", vals) == []               # a pace, not a quantity


def _ra(**kw):
    out = {"type": "route_adaptation", "response_language": "ru", "message_to_user": "Предлагаю перенести срок цели.",
           "trigger": {"type": "less_time", "description": "Меньше времени"}, "change_level": "major",
           "requires_user_confirmation": True, "removed_nodes": [], "added_nodes": [], "modified_nodes": [],
           "modified_deadlines": [{"target": "goal", "target_id": "g1", "from": "2027-03-01", "to": "2027-04-01",
                                   "reason": "Не хватает времени", "autonomy": "confirm_required", "state": "proposed"}],
           "new_weekly_hours_planned": 3,
           "workload": {"weekly_hours": 3, "remaining_minutes_before": 4200, "remaining_minutes_after": 4200,
                        "horizon": {"target": "goal", "target_id": "g1", "date": "2027-04-01"},
                        "weeks_needed": 23.4, "weeks_available": 26.4, "fits": True},
           "preserved_progress": ["n1"],
           "decision_summary": {"what_changed": "Предложен новый срок 1 апреля.", "why": "Осталось 70 часов работы.",
                                "impact": "При 3 часах в неделю это около 23 недель."}}
    out.update(kw)
    return out


def test_consistent_time_adaptation_is_clean():
    assert codes("route_adaptation", _ra(), CTX) == set()


@pytest.mark.parametrize("patch,code", [
    ({"workload": None}, "RA_WORKLOAD_MISSING"),
    ({"workload.remaining_minutes_before": 5700}, "ARITH_REMAINING_BEFORE"),
    ({"workload.weeks_needed": 30}, "ARITH_WEEKS_NEEDED"),
    ({"workload.weeks_available": 20}, "ARITH_WEEKS_AVAILABLE"),
    ({"workload.horizon.date": "2027-05-01"}, "ARITH_HORIZON_DATE"),
    ({"modified_deadlines.0.state": "applied"}, "RA_DEADLINE_STATE_INCONSISTENT"),
    ({"modified_deadlines.0.autonomy": "auto"}, "RA_DEADLINE_AUTONOMY_WRONG"),
    ({"requires_user_confirmation": False, "modified_deadlines.0.state": "applied", "change_level": "moderate"},
     "RA_GOAL_DEADLINE_NO_CONFIRM"),
    ({"decision_summary.why": "Осталось 95 часов работы."}, "ARITH_TEXT_UNDERIVABLE"),
])
def test_time_adaptation_errors(patch, code):
    out = _ra()
    for key, value in patch.items():
        if value is None:
            out.pop(key)
            continue
        target = out
        parts = key.split(".")
        for p in parts[:-1]:
            target = target[int(p)] if p.isdigit() else target[p]
        target[parts[-1]] = value
    assert code in codes("route_adaptation", out, CTX)


def test_unfit_plan_needs_a_user_decision():
    out = _ra(modified_deadlines=[], requires_user_confirmation=False, change_level="minor",
              message_to_user="Темп снижен.", workload={**_ra()["workload"], "horizon": {"target": "milestone", "target_id": "m1",
                                                                                   "date": "2026-12-20"},
                                                         "remaining_minutes_before": 3300, "remaining_minutes_after": 3300,
                                                         "weeks_needed": 18.3, "weeks_available": 12.0, "fits": False},
              decision_summary={"what_changed": "Темп 3 часа в неделю.", "why": "Меньше времени.", "impact": "Этап m1 сдвинется."})
    assert "RA_UNFIT_NO_DECISION" in codes("route_adaptation", out, CTX)


def test_milestone_moves_must_fit_and_be_named():
    out = _ra(requires_user_confirmation=False, change_level="moderate", message_to_user="Этап перенесён.",
              modified_deadlines=[{"target": "milestone", "target_id": "m1", "from": "2026-12-20", "to": "2026-11-15",
                                   "reason": "x", "autonomy": "adapt_with_summary", "state": "applied"}],
              workload={**_ra()["workload"], "horizon": {"target": "milestone", "target_id": "m1", "date": "2026-11-15"},
                        "remaining_minutes_before": 3300, "remaining_minutes_after": 3300, "weeks_needed": 18.3,
                        "weeks_available": 7.0, "fits": False},
              decision_summary={"what_changed": "Изменён план.", "why": "Меньше времени.", "impact": "Без изменений цели."})
    c = codes("route_adaptation", out, CTX)
    assert {"MILESTONE_DATE_INFEASIBLE", "RA_MILESTONE_NO_SUMMARY", "RA_UNFIT_NO_DECISION"} <= c


def test_undeclared_due_date_change():
    out = _ra(modified_nodes=[{"node_id": "n2", "changes": [{"field": "due_date", "from": None, "to": "2026-10-20"}],
                               "reason": "x"}])
    assert "RA_UNDECLARED_DEADLINE_CHANGE" in codes("route_adaptation", out, CTX)


def test_new_rules_do_not_apply_to_v010_records():
    out = _ra()
    for d in out["modified_deadlines"]:
        d.pop("autonomy"), d.pop("state")
    out.pop("workload")
    c = codes("route_adaptation", out, CTX, version="0.1.0")
    assert not c & {"RA_WORKLOAD_MISSING", "RA_DEADLINE_AUTONOMY_MISSING", "ARITH_TEXT_UNDERIVABLE"}


# ----------------------------------------------------------------------------- navigator / goal change / journey

def test_navigator_reschedule_is_declared_and_goal_needs_confirmation():
    out = {"type": "navigator_response", "response_language": "ru", "message_to_user": "Предлагаю перенести.",
           "intent": "reschedule", "in_scope": True, "requires_user_confirmation": False,
           "proposed_changes": [{"action": "reschedule", "target_id": "n2", "description": "Перенос"},
                                {"action": "modify", "target_id": "g1", "target_type": "goal", "new_date": "2027-04-01",
                                 "description": "Перенос цели"}],
           "decision_summary": {"what_changed": "a", "why": "b", "impact": "c"}}
    c = codes("navigator_response", out, CTX)
    assert {"NAV_RESCHEDULE_UNDECLARED", "NAV_GOAL_DEADLINE_NO_CONFIRM"} <= c


def test_goal_change_deadline_needs_confirmation():
    out = {"type": "goal_change", "response_language": "ru", "message_to_user": "Цель обновлена.",
           "classification": "minor_adjustment", "updated_goal": {"title": "Цель", "deadline": "2027-06-01"},
           "preserved_progress": [{"node_id": "n1", "how_reused": "Основа"}], "discarded_progress": [],
           "recommend_separate_goal": False, "requires_user_confirmation": False,
           "decision_summary": {"what_changed": "a", "why": "b", "impact": "c"}}
    assert "GC_DEADLINE_NO_CONFIRM" in codes("goal_change", out, CTX)


def test_journey_milestone_overbooked():
    ctx = {"operation": "journey_generation", "today": "2026-09-27",
           "goal": {"title": "Цель", "deadline": "2027-03-01", "available_time": {"hours_per_week": 4}}}
    journey = _journey([_node("n1", 600), _node("n2", 600), _node("n3", 600)],
                       [{"id": "m1", "title": "Этап", "region_id": "r1", "success_criteria": ["x"], "target_date": "2026-10-18"}])
    journey["pacing"] = {"weekly_hours_planned": 4}
    out = {"type": "journey_generation", "response_language": "ru", "message_to_user": "Маршрут готов.",
           "goal": {"title": "Цель", "deadline": "2027-03-01"}, "journey": journey,
           "decision_summary": {"what_changed": "a", "why": "b", "impact": "c"}}
    assert "J_MILESTONE_OVERBOOKED" in codes("journey_generation", out, ctx)


# ----------------------------------------------------------------------------- capabilities & evidence

def _protocol(methods, ceiling="limited", self_report_only=True, verifiability="low", nature="other"):
    return {"task_nature": nature, "objective_verifiability": verifiability, "methods": methods, "pass_criteria": ["x"],
            "confidence_ceiling": ceiling, "self_report_only": self_report_only, "rationale": "x"}


def _m(method, role="required", **kw):
    return {"method": method, "role": role, "instructions": "Сделайте это.", **kw}


def test_protocol_support_levels():
    assert POL.protocol_support(_protocol([_m("structured_result")]))[0] == "limited"
    assert POL.protocol_support(_protocol([_m("structured_result", references_required=True), _m("url_review", "supplementary")]))[0] == "medium"
    assert POL.protocol_support(_protocol([_m("photo"), _m("structured_self_report")]))[0] == "medium"
    assert POL.protocol_support(_protocol([_m("artifact_review")]))[0] == "high"
    assert POL.protocol_support(_protocol([_m("structured_result", evidence_class="inspectable_artifact")]))[0] == "high"
    assert POL.protocol_is_users_word(_protocol([_m("structured_result"), _m("follow_up_questions")]))


def test_protocol_lint_v011():
    vp = {"type": "verification_protocol_design", "response_language": "ru", "message_to_user": "Протокол готов.",
          "task_id": "t1", "protocol": _protocol([_m("structured_result")], ceiling="medium", self_report_only=False)}
    c = codes("verification_protocol_design", vp, {"operation": "verification_protocol_design", "today": "2026-09-27"})
    assert {"VP_CEILING_ABOVE_EVIDENCE", "VP_SELF_REPORT_CEILING"} <= c
    vp["protocol"] = _protocol([_m("video"), _m("follow_up_questions", questions=["a?", "b?"])], ceiling="limited")
    assert "VP_METHOD_UNAVAILABLE" in codes("verification_protocol_design", vp, {"operation": "verification_protocol_design", "today": "2026-09-27"})
    assert "VP_METHOD_UNAVAILABLE" not in codes("verification_protocol_design", vp, {"today": "2026-09-27"}, version="0.1.0")


def test_capability_promises():
    assert list(POL.capability_promises("Пришлю задачи сразу после этого сообщения."))
    assert list(POL.capability_promises("Please upload a short video of the run."))
    assert list(POL.capability_promises("I'll remind you on Friday."))
    assert not list(POL.capability_promises("No video is needed: the transcript is enough."))
    assert not list(POL.capability_promises("Задачи — ниже в этом сообщении."))


def _vr(conf, basis, status="verified", **kw):
    return {"type": "verification_result", "response_language": "ru", "message_to_user": "Засчитано.", "task_id": "t1",
            "attempt": 1, "status": status, "confidence": conf, "evidence_basis": basis,
            "criteria_results": [{"criterion": "x", "result": "met"}], "reason": "x", "additional_evidence": [],
            "decision_summary": {"what_changed": "a", "why": "b", "impact": "c"}, **kw}


def test_verification_confidence_follows_evidence_class():
    ctx = {"operation": "verification_result", "today": "2026-09-27",
           "task": {"id": "t1", "title": "Пробежать 10 км", "description": "x", "why_it_matters": "x", "expected_result": "x",
                    "estimated_duration_minutes": 60, "difficulty": 2,
                    "verification_protocol": _protocol([_m("data_export")], ceiling="high", self_report_only=False,
                                                       verifiability="high", nature="physical_activity")},
           "evidence": [{"id": "e1", "type": "structured_result", "fields": {"km": 10}}]}
    assert "VR_CONFIDENCE_ABOVE_EVIDENCE" in codes("verification_result", _vr("medium", "mixed"), ctx)
    ctx["evidence"].append({"id": "e2", "type": "data_export", "description_source": "file_parser", "content": "distance 6.2 km"})
    contr = [{"evidence_ids": ["e1", "e2"], "user_claim": "10 км", "evidence_shows": "6,2 км"}]
    c = codes("verification_result", _vr("high", "objective", contradictions=contr), ctx)
    assert "VR_CONTRADICTION_VERIFIED" in c and "VR_CONFIDENCE_ABOVE_EVIDENCE" not in c


def test_lint_input_flags_unavailable_evidence_and_gendered_memory():
    ctx = {"operation": "verification_result", "today": "2026-09-27",
           "evidence": [{"id": "e1", "type": "video", "description": "видео пробежки"}],
           "user_memory": [{"id": "um1", "scope": "user", "category": "schedule", "content": "Свободен по выходным."}]}
    c = {i.code for i in lint_input(ctx, "0.1.1")}
    assert {"EVIDENCE_SOURCE_UNAVAILABLE", "RU_GENDERED_MEMORY"} <= c
    assert lint_input(ctx, "0.1.0") == []


# ----------------------------------------------------------------------------- provenance

PCTX = {"today": "2026-09-27",
        "conversation": [{"role": "user", "content": "Могу заниматься только по выходным, около 6 часов."},
                         {"role": "assistant", "content": "Понял."}],
        "user_memory": [{"id": "um1", "scope": "user", "category": "schedule", "content": "Работает сменами 2/2.", "source": "inferred"}],
        "research_results": [{"id": "rr1", "finding": "Экзамен проводится 12 раз в год.", "source": {"title": "x", "url": "https://example.org"}}]}


@pytest.mark.parametrize("fact,code", [
    ({"value": "Занимается по выходным, около 6 часов", "source_type": "user_provided", "source_ref": "conversation[0]"}, None),
    ({"value": "Занимается по выходным, около 8 часов", "source_type": "user_provided", "source_ref": "conversation[0]"}, "FACT_NOT_GROUNDED"),
    ({"value": "Занимается по выходным", "source_type": "user_provided", "source_ref": "conversation[1]"}, "FACT_NOT_GROUNDED"),
    ({"value": "Занимается по выходным", "source_type": "user_provided", "source_ref": "conversation[7]"}, "FACT_BAD_REF"),
    ({"value": "Работает сменами", "source_type": "user_provided", "source_ref": "user_memory:um1"}, "FACT_PROVENANCE_UPGRADED"),
    ({"value": "Работает сменами", "source_type": "model_inferred", "source_ref": "user_memory:um1"}, None),
    ({"value": "Экзамен 12 раз в год", "source_type": "externally_verified", "source_ref": "research:rr1"}, None),
    ({"value": "Экзамен 12 раз в год", "source_type": "externally_verified", "source_ref": "conversation[0]"}, "FACT_VERIFIED_WITHOUT_SOURCE"),
    ({"value": "Лимит времени забега", "source_type": "unknown"}, None),
])
def test_fact_provenance(fact, code):
    got = {c for c, _, _ in PROV.check_facts([fact], PCTX)}
    assert got == ({code} if code else set())


def test_user_stated_memory_must_come_from_the_user():
    ctx = {"today": "2026-09-27", "conversation": [{"role": "user", "content": "Экзамен DELF 14 марта, я в командировке до пятницы."}]}
    ok = [{"content": "DELF exam date is 2027-03-14.", "source": "user_stated"},
          {"content": "В командировке до 2026-10-02.", "source": "user_stated"}]
    assert PROV.memory_source_issues(ok, ctx) == []
    bad = [{"content": "Бюджет 500 000 рублей.", "source": "user_stated"}]
    assert PROV.memory_source_issues(bad, ctx)


# ----------------------------------------------------------------------------- Russian voice

@pytest.mark.parametrize("text", ["Подготовку разбил на 4 задачи.", "Я уверен, что успеете.", "Я всё проверил."])
def test_gendered_self_reference(text):
    assert next(RU.self_reference(text), None)


@pytest.mark.parametrize("text", ["Подготовка разбита на 4 задачи.", "Предлагаю перенести срок.", "Задача засчитана.",
                                  "Ментор предложил другой порядок.", "Вы написали, что уже проверили."])
def test_neutral_self_reference(text):
    assert next(RU.self_reference(text), None) is None


def test_gendered_user_address():
    assert list(RU.user_address("едете ли вы один или с семьёй?"))
    assert not list(RU.user_address("планируете переезд в одиночку или с семьёй?"))
    assert not list(RU.user_address("вы готовы начать?"))


def test_russian_voice_lint_is_gated_and_skips_badge_titles():
    out = {"type": "navigator_response", "response_language": "ru", "message_to_user": "Подготовку разбил на 4 задачи.",
           "intent": "explain_task", "in_scope": True, "proposed_changes": [], "requires_user_confirmation": False}
    assert "RU_GENDERED_SELF_REFERENCE" in codes("navigator_response", out)
    assert "RU_GENDERED_SELF_REFERENCE" not in codes("navigator_response", out, version="0.1.0")
