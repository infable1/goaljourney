"""`gj audit`: targeted heuristic audits of the pool (Problems 1–9 of Milestone 1.5) + known issues.

These rules are review aids. They flag *candidates* for a human to look at; they never approve,
reject or edit an example, and a clean audit is not evidence of quality. Rules that are reliable
enough to block a release live in generation/validators/semantic.py instead.

Problems
  P1 generic tasks            P4 missing critical questions   P7 hallucinated external facts
  P2 fake verification        P5 overplanning                 P8 memory leakage
  P3 excessive questioning    P6 user agency                  P9 language (incl. Russian gender neutrality)
  X  temporal consistency (dates/weekdays relative to `today`) — added after manual inspection found two errors.
"""
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta

from gjcore import schemas
from gjcore.config import load_config, versions
from gjcore.io import dump_json, load_yaml
from gjcore.paths import rel, repo_path
from gjcore.records import load_eval_cases
from generation.validators import calendar as CAL
from generation.validators import policy as POL
from generation.validators import russian as RU
from generation.validators import text as T

from .pool import load_pool

RULES = {
    "vague_node_title": ("P1", "Task/outline/added node title is generic (no object or quantity); outline titles are not linted."),
    "generic_rationale": ("P1", "why_it_matters / reason uses a stock phrase that carries no task-specific reason."),
    "user_entered_as_objective": ("P2", "The protocol's ceiling exceeds what its required evidence classes support (POL-B: user-entered data is the user's word)."),
    "capability_assumption": ("P2", "Asks for or promises a capability that configs/product_capabilities.yaml marks planned or unsupported (POL-A)."),
    "unverifiable_criterion": ("P2", "An acceptance criterion the navigator cannot actually check from the evidence it asks for."),
    "too_many_questions": ("P3", "More than 3 clarification questions, or several questions in a non-clarification answer."),
    "unsupported_feasibility_claim": ("P4", "Asserts that a date/target still works without the current-state facts needed to know it."),
    "tiny_goal_overplanned": ("P5", "A tiny goal gets more than 4 tasks/nodes."),
    "capacity_mismatch": ("P5", "Planned durations do not fit (or wildly underuse) weekly hours x horizon."),
    "deadline_change_without_consent": ("P6", "A deadline changes without the autonomy POL-C allows (goal dates need confirmation; every change declares its autonomy)."),
    "change_without_consent": ("P6", "Moderate/major change or removal applied without asking."),
    "applied_while_pending": ("P6", "Message says a change was already made although it still needs the user's confirmation."),
    "unsupported_generalisation": ("P7", "Confident generalisation about people/markets/institutions without a source."),
    "novel_quantity": ("P7", "A quantity with a unit (hours, weeks, %, money) in user-facing text does not appear in the input; confirm it is derived correctly."),
    "retrieved_memory_leak": ("P8", "Distinctive words/numbers from another goal's retrieved memory appear in the output."),
    "sensitive_memory_unflagged": ("P8", "Stored memory about health/caregiving/finances is marked sensitive: false."),
    "ru_gendered_self_reference": ("P9", "The assistant refers to itself with a gendered Russian form (e.g. 'разбил', 'я проверил')."),
    "ru_gendered_user_address": ("P9", "The user is addressed with a gendered Russian form (e.g. 'вы один', 'вы готов')."),
    "ru_gendered_identity_label": ("P9", "A Russian level/achievement title labels the user with a grammatically gendered noun/adjective."),
    "ru_informal_address": ("P9", "Informal 'ты' in a user-facing answer (product register is 'вы')."),
    "ru_gendered_memory_input": ("P9", "Stored user memory in the input describes the user with a gendered form."),
    "en_third_person_pronoun": ("P9", "A gendered third-person pronoun in an English output — check it does not refer to the user or to someone whose pronouns are unknown."),
    "weekday_date_mismatch": ("X", "A weekday named together with a date does not match the calendar."),
    "past_weekend_day": ("X", "Plans a day of 'this weekend' that is already in the past relative to `today`."),
    "promises_later_message": ("X", "Promises to send something in a later message — requires a product capability."),
}

SEVERITY = {
    "vague_node_title": "medium", "generic_rationale": "low", "user_entered_as_objective": "medium",
    "capability_assumption": "medium", "unverifiable_criterion": "low", "too_many_questions": "medium",
    "unsupported_feasibility_claim": "low", "tiny_goal_overplanned": "medium", "capacity_mismatch": "medium",
    "deadline_change_without_consent": "medium", "change_without_consent": "medium", "applied_while_pending": "medium",
    "unsupported_generalisation": "low", "novel_quantity": "info", "retrieved_memory_leak": "high",
    "sensitive_memory_unflagged": "low", "ru_gendered_self_reference": "high", "ru_gendered_user_address": "high",
    "ru_gendered_identity_label": "medium", "ru_informal_address": "low", "ru_gendered_memory_input": "low",
    "en_third_person_pronoun": "low", "weekday_date_mismatch": "high", "past_weekend_day": "high",
    "promises_later_message": "low",
}

# ---------------------------------------------------------------------------------------------
# Russian gendered forms: shared with the v0.1.1 lint (generation/validators/russian.py).

_ru_self_reference = RU.self_reference
_ru_memory_gendered = RU.memory_gendered
_RU_USER_ADDR_RE = RU.USER_ADDRESS_RE
_RU_INFORMAL_RE = RU.INFORMAL_RE
_RU_AGENT_NOUN_RE = RU.AGENT_NOUN_RE
_EN_PRONOUN_RE = re.compile(r"\b(he|she|him|his|hers|himself|herself)\b", re.IGNORECASE)

# ---------------------------------------------------------------------------------------------
# Other text patterns

_GENERIC_RATIONALE = re.compile(
    r"^(practice makes perfect|this is important|it'?s important|you need (to|this)|needed|important|"
    r"это важно|нужно знать|это нужно|так надо|для практики|theory first|precision|safety first|consistency)\.?$",
    re.IGNORECASE)
_UNVERIFIABLE_CRIT = re.compile(r"(rules? (are|is) respected|правила соблюдены|honestly|честно)", re.IGNORECASE)
_FEASIBLE_CLAIM = re.compile(r"(still works|is realistic|fits comfortably|you'?ll (easily )?make it|"
                             r"вполне реально|успеете|срок подходит|всё ещё реально|всё еще реально)", re.IGNORECASE)
_GENERALISATION = re.compile(
    r"\b(usually|typically|most (people|fighters|users|beginners|hiring managers|reviewers|clients|employers)|"
    r"many (people|fighters|providers|offer)|everyone|every professional|exactly what (a |the )?\w+( \w+)? (looks? for|likes?)|"
    r"(what|everything) (a |the )?(hiring managers?|judges|reviewers?|employers|investors) (look for|looks for|decide on|want)|"
    r"обычно|чаще всего|как правило|большинств\w+|всегда|ценнее любого|работает хуже любого|месяцев проб и ошибок)\b",
    re.IGNORECASE)
_UNIT_NUM = re.compile(
    r"(\d+(?:[.,]\d+)?)\s?(hours?|h\b|hrs?|weeks?|months?|minutes?|min\b|%|kg|кг|час\w*|недел\w*|месяц\w*|минут\w*|"
    r"тысяч\w*|руб\w*|\$|€)", re.IGNORECASE)
_APPLIED_RE = re.compile(r"\b(I'?ve (added|removed|changed|moved|split|replaced|switched|rebuilt|dropped|lowered|cut)|"
                         r"I have (added|removed|changed|moved)|(добавил|убрал|изменил|перенёс|перенес|сократил|заменил|"
                         r"удалил|сдвинул)[аи]?\b)", re.IGNORECASE)
_LATER_MSG = re.compile(r"(я пришлю|пришлю (их|вам)|сразу после этого сообщения|I'?ll send (you )?(them|it|the)|"
                        r"in my next message|в следующем сообщении)", re.IGNORECASE)
_WEEKEND_INPUT = re.compile(r"\b(this weekend|на этих выходных|в эти выходные|на этой неделе в выходные)\b", re.IGNORECASE)
_SATURDAY = re.compile(r"\b(saturday|суббот\w*)\b", re.IGNORECASE)

USER_TEXT_KEYS = {"message_to_user", "question", "reason", "next_action", "suggested_next_action", "what_changed",
                  "why", "impact", "why_not", "option", "request", "scope_note", "note", "interim_guidance",
                  "description", "title", "why_it_matters", "expected_result", "instructions", "safer_reframing",
                  "summary", "rationale", "strategy_summary", "route_impact", "how_reused", "content", "critique"}


def _strings(obj, path="", keys=None):
    """Yield (path, string) for user-facing string leaves."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if isinstance(v, str):
                if keys is None or k in keys:
                    yield p, v
            else:
                yield from _strings(v, p, keys)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{path}[{i}]"
            if isinstance(v, str):
                if keys is None or path.split(".")[-1] in {"questions", "boundaries", "allowed_support", "user_options",
                                                           "risks", "success_criteria", "pass_criteria",
                                                           "acceptance_criteria", "known_context_used", "fields"}:
                    yield p, v
            else:
                yield from _strings(v, p, keys)


def _snippet(text, m=None, width=70):
    if m is None:
        return text[:width * 2]
    a, b = max(0, m.start() - width // 2), min(len(text), m.end() + width // 2)
    return ("…" if a else "") + text[a:b] + ("…" if b < len(text) else "")


class _Collector:
    def __init__(self):
        self.findings = []
        self._n = Counter()

    def add(self, rule, scope, record_id, location, evidence, message=None, severity=None):
        sev = severity or SEVERITY[rule]
        if scope == "contrastive" and sev in ("high", "medium"):
            sev = "low"  # a defect in a rejected output matters only as an untagged extra failure
        key = (rule, record_id)
        self._n[key] += 1
        safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", record_id)
        self.findings.append({
            "finding_id": f"AF-{rule}-{safe_id}-{self._n[key]}", "rule": rule, "problem": RULES[rule][0],
            "severity": sev, "scope": scope, "record_id": record_id, "location": location,
            "message": message or RULES[rule][1], "evidence": evidence[:400],
        })


# ---------------------------------------------------------------------------------------------
# Rule implementations. Each takes (collector, record_id, scope, task_type, input, output, language, meta).

def _nodes_with_titles(out):
    j = out.get("journey") or {}
    for i, n in enumerate(j.get("nodes") or []):
        yield f"journey.nodes[{i}].title", n.get("title", ""), n
    for i, n in enumerate(out.get("added_nodes") or []):
        yield f"added_nodes[{i}].title", n.get("title", ""), n
    for i, t in enumerate(out.get("tasks") or []):
        yield f"tasks[{i}].title", t.get("title", ""), t


def rule_p1(c, rid, scope, tt, inp, out, lang, meta):
    for loc, title, node in _nodes_with_titles(out):
        if node.get("type", "task") in ("task", "challenge") and T.title_is_vague(title):
            c.add("vague_node_title", scope, rid, loc, title)
    for loc, s in _strings(out, keys={"why_it_matters", "reason", "why"}):
        if _GENERIC_RATIONALE.match(s.strip()):
            c.add("generic_rationale", scope, rid, loc, s)


def _protocols(out, inp):
    if out.get("protocol"):
        yield "protocol", out["protocol"]
    for i, t in enumerate(out.get("tasks") or []):
        if t.get("verification_protocol"):
            yield f"tasks[{i}].verification_protocol", t["verification_protocol"]
    for i, n in enumerate((out.get("journey") or {}).get("nodes") or []):
        vp = (n.get("task") or {}).get("verification_protocol")
        if vp:
            yield f"journey.nodes[{i}].task.verification_protocol", vp


def rule_p2(c, rid, scope, tt, inp, out, lang, meta):
    for loc, p in _protocols(out, inp):
        req = [m.get("method") for m in p.get("methods") or [] if m.get("role") == "required"]
        support, classes = POL.protocol_support(p)
        ceiling = p.get("confidence_ceiling")
        if req and ceiling in POL.RANK and POL.RANK[ceiling] > POL.RANK[support]:
            c.add("user_entered_as_objective", scope, rid, loc,
                  f"required={req} ({', '.join(classes)}), ceiling={ceiling}, supported={support}")
        for j, m in enumerate(p.get("methods") or []):
            for crit in m.get("acceptance_criteria") or []:
                mm = _UNVERIFIABLE_CRIT.search(crit)
                if mm:
                    c.add("unverifiable_criterion", scope, rid, f"{loc}.methods[{j}].acceptance_criteria", crit)
    for loc, s in _strings(out, keys=USER_TEXT_KEYS):
        for cap, status, m in POL.capability_promises(s):
            c.add("capability_assumption", scope, rid, loc, f"{cap} ({status}): {_snippet(s, m)}")
            break
        m = _LATER_MSG.search(s)
        if m:
            c.add("promises_later_message", scope, rid, loc, _snippet(s, m))


def rule_p3(c, rid, scope, tt, inp, out, lang, meta):
    qs = out.get("questions") or []
    if len(qs) > 3:
        c.add("too_many_questions", scope, rid, "questions", f"{len(qs)} questions")
    msg = out.get("message_to_user") or ""
    # lines that enumerate test items («а) …?», «1) …?») are exercises, not questions to the user
    asked = "\n".join(l for l in msg.split("\n") if not re.match(r"^\s*(?:[а-яa-z]|\d{1,2})\)", l, re.IGNORECASE))
    if tt != "goal_clarification" and asked.count("?") > 2:
        c.add("too_many_questions", scope, rid, "message_to_user", f"{asked.count('?')} question marks")


def rule_p4(c, rid, scope, tt, inp, out, lang, meta):
    if tt not in ("goal_change", "journey_generation", "route_adaptation", "navigator_response"):
        return
    goal = inp.get("goal") or {}
    if goal.get("current_state"):
        return
    msg = out.get("message_to_user") or ""
    m = _FEASIBLE_CLAIM.search(msg)
    if m:
        c.add("unsupported_feasibility_claim", scope, rid, "message_to_user", _snippet(msg, m))


def _weeks_between(a, b):
    try:
        return (date.fromisoformat(b) - date.fromisoformat(a)).days / 7
    except (TypeError, ValueError):
        return None


def rule_p5(c, rid, scope, tt, inp, out, lang, meta):
    goal_size = meta.get("goal_size")
    items = (out.get("tasks") or []) or ((out.get("journey") or {}).get("nodes") or [])
    if goal_size == "tiny" and len(items) > 4:
        c.add("tiny_goal_overplanned", scope, rid, "tasks" if out.get("tasks") else "journey.nodes", f"{len(items)} items for a tiny goal")
    j = out.get("journey") or {}
    pacing = j.get("pacing") or {}
    nodes = j.get("nodes") or []
    if pacing.get("weekly_hours_planned") and pacing.get("horizon_weeks") and nodes:
        durs = [n.get("estimated_duration_minutes") for n in nodes]
        known = [d for d in durs if d]
        if len(known) >= 0.8 * len(nodes):
            planned_h = sum(known) / 60
            cap = pacing["weekly_hours_planned"] * pacing["horizon_weeks"]
            if planned_h > 1.1 * cap or planned_h < 0.3 * cap:
                c.add("capacity_mismatch", scope, rid, "journey.pacing",
                      f"node durations {planned_h:.0f} h vs capacity {cap:.0f} h ({pacing['weekly_hours_planned']} h/wk x {pacing['horizon_weeks']} wk)")
    if tt == "task_generation" and out.get("tasks"):
        total_h = sum(t.get("estimated_duration_minutes") or 0 for t in out["tasks"]) / 60
        hpw = ((inp.get("goal") or {}).get("available_time") or {}).get("hours_per_week")
        target = None
        tn = inp.get("target_node_id")
        jn = inp.get("journey") or {}
        node = next((n for n in jn.get("nodes") or [] if n.get("id") == tn), {})
        ms = next((m for m in jn.get("milestones") or [] if m.get("id") == node.get("milestone_id")), {})
        target = ms.get("target_date") or (inp.get("goal") or {}).get("deadline")
        weeks = _weeks_between(inp.get("today"), target) if target else None
        if hpw and weeks and total_h > hpw * weeks:
            c.add("capacity_mismatch", scope, rid, "tasks", f"tasks need {total_h:.1f} h, {hpw} h/wk x {weeks:.1f} wk available before {target}")


def rule_p6(c, rid, scope, tt, inp, out, lang, meta):
    msg = out.get("message_to_user") or ""
    if tt == "route_adaptation":
        confirm = out.get("requires_user_confirmation")
        allowed = {"node": "auto", "milestone": "adapt_with_summary"}
        bad = [d for d in out.get("modified_deadlines") or []
               if not confirm and allowed.get(d.get("target")) != d.get("autonomy")]
        if bad:
            ds = "; ".join(f"{d.get('target')} {d.get('target_id')}: {d.get('from')}→{d.get('to')}" for d in bad)
            c.add("deadline_change_without_consent", scope, rid, "modified_deadlines", ds)
        if out.get("change_level") in ("moderate", "major") and not confirm and out.get("removed_nodes"):
            c.add("change_without_consent", scope, rid, "removed_nodes",
                  f"{out.get('change_level')} change removes {[r.get('node_id') for r in out['removed_nodes']]} without confirmation")
        if confirm:
            m = _APPLIED_RE.search(msg)
            if m:
                c.add("applied_while_pending", scope, rid, "message_to_user", _snippet(msg, m))
    if tt == "navigator_response":
        acts = {p.get("action") for p in out.get("proposed_changes") or []}
        if acts & {"remove", "replace", "reschedule"} and not out.get("requires_user_confirmation"):
            c.add("change_without_consent", scope, rid, "proposed_changes", f"actions {sorted(acts)} without confirmation")
        if out.get("requires_user_confirmation"):
            m = _APPLIED_RE.search(msg)
            if m:
                c.add("applied_while_pending", scope, rid, "message_to_user", _snippet(msg, m))


def _input_numbers(inp):
    text = json.dumps(inp, ensure_ascii=False)
    text = re.sub(r"(?<=\d)[\s ](?=\d{3}\b)", "", text)
    return set(re.findall(r"\d+(?:[.,]\d+)?", text))


def rule_p7(c, rid, scope, tt, inp, out, lang, meta):
    innums = _input_numbers(inp)
    for loc, s in _strings(out, keys={"message_to_user", "what_changed", "why", "impact", "why_not", "reason",
                                      "why_it_matters", "summary", "rationale"}):
        for m in _GENERALISATION.finditer(s):
            end = min((i for i in (s.find(ch, m.end()) for ch in ".!?\n") if i >= 0), default=len(s))
            if end < len(s) and s[end] == "?":
                continue  # a question about the user's own experience ("где вы чаще всего сбивались?")
            c.add("unsupported_generalisation", scope, rid, loc, _snippet(s, m))
        if tt in ("route_adaptation", "feasibility_assessment", "goal_change", "journey_generation", "navigator_response"):
            flat = re.sub(r"(?<=\d)[\s ](?=\d{3}\b)", "", s)
            for m in _UNIT_NUM.finditer(flat):
                n = m.group(1)
                if n not in innums and n.replace(",", ".") not in innums and float(n.replace(",", ".")) > 12:
                    c.add("novel_quantity", scope, rid, loc, _snippet(flat, m))


_MEM_SENSITIVE = re.compile(r"(health|medical|diagnos|carer|caregiv|debt|salary|pay\b|ипотек|долг|зарплат|болезн|диагноз|уход за)", re.IGNORECASE)


def rule_p8(c, rid, scope, tt, inp, out, lang, meta):
    goal_id = (inp.get("goal") or {}).get("id")
    other = [m for m in inp.get("retrieved_memory") or [] if m.get("goal_id") and m.get("goal_id") != goal_id]
    if other:
        rest = json.dumps({k: v for k, v in inp.items() if k != "retrieved_memory"}, ensure_ascii=False).lower()
        out_text = json.dumps(out, ensure_ascii=False).lower()
        for m in other:
            content = (m.get("content") or "").lower()
            toks = set(re.findall(r"[a-zа-яё]{6,}", content)) | set(re.findall(r"\d[\d\s,.]*\d|\d", content))
            toks = {t.strip() for t in toks if t.strip() and t.strip() not in rest}
            hits = sorted(t for t in toks if t in out_text)
            if hits:
                c.add("retrieved_memory_leak", scope, rid, "output", f"goal {m.get('goal_id')}: {hits[:5]}")
    if tt == "memory_extraction":
        for i, it in enumerate(out.get("items") or []):
            if not it.get("sensitive") and _MEM_SENSITIVE.search(it.get("content") or ""):
                c.add("sensitive_memory_unflagged", scope, rid, f"items[{i}]", it.get("content", ""))


def rule_p9(c, rid, scope, tt, inp, out, lang, meta):
    if lang == "ru" or scope == "input":
        for loc, s in _strings(out, keys=USER_TEXT_KEYS - {"critique"}):
            if T.cyrillic_ratio(s) < 0.5:
                continue
            for hit in _ru_self_reference(s):
                c.add("ru_gendered_self_reference", scope, rid, loc, f"{hit!r} in: {s[:160]}")
                break
            for m in _RU_USER_ADDR_RE.finditer(s):
                c.add("ru_gendered_user_address", scope, rid, loc, _snippet(s, m))
            for m in _RU_INFORMAL_RE.finditer(s):
                if loc.startswith("questions") or "message" in loc or loc.startswith("decision_summary"):
                    c.add("ru_informal_address", scope, rid, loc, _snippet(s, m))
                    break
        j = out.get("journey") or {}
        labels = [(f"journey.levels[{i}].title", lv.get("title", "")) for i, lv in enumerate(j.get("levels") or [])]
        labels += [(f"journey.achievements[{i}].title", a.get("title", "")) for i, a in enumerate(j.get("achievements") or [])]
        if (out.get("level") or {}).get("current_title"):
            labels.append(("level.current_title", out["level"]["current_title"]))
        for loc, s in labels:
            m = _RU_AGENT_NOUN_RE.search(s)
            if m and T.cyrillic_ratio(s) >= 0.5:
                c.add("ru_gendered_identity_label", scope, rid, loc, s,
                      severity="medium" if m.group(1) else "low")
    if lang == "en" and scope != "input":
        for loc, s in _strings(out, keys={"message_to_user", "what_changed", "why", "impact", "reason", "question"}):
            m = _EN_PRONOUN_RE.search(s)
            if m:
                c.add("en_third_person_pronoun", scope, rid, loc, _snippet(s, m))


def rule_memory_input(c, rid, inp):
    for key in ("user_memory", "retrieved_memory"):
        for i, m in enumerate(inp.get(key) or []):
            s = m.get("content") or ""
            if T.cyrillic_ratio(s) >= 0.5:
                mm = _ru_memory_gendered(s)
                if mm:
                    c.add("ru_gendered_memory_input", "input", rid, f"input.{key}[{i}].content", _snippet(s, mm))


def rule_temporal(c, rid, scope, tt, inp, out, lang, meta):
    try:
        today = date.fromisoformat(inp.get("today"))
    except (TypeError, ValueError):
        return
    for loc, s in _strings(out, keys=USER_TEXT_KEYS):
        for mm in CAL.weekday_mismatches(s, today):
            c.add("weekday_date_mismatch", scope, rid, loc, mm.message())
    user_text = " ".join(m.get("content", "") for m in inp.get("conversation") or [] if m.get("role") == "user")
    user_text += " " + ((inp.get("goal") or {}).get("title") or "")
    if today.weekday() == 6 and _WEEKEND_INPUT.search(user_text):
        msg = out.get("message_to_user") or ""
        m = _SATURDAY.search(msg)
        if m:
            c.add("past_weekend_day", scope, rid, "message_to_user",
                  f"today {today.isoformat()} is a Sunday; plan uses {m.group(0)!r}: {_snippet(msg, m)}")


RULE_FUNCS = (rule_p1, rule_p2, rule_p3, rule_p4, rule_p5, rule_p6, rule_p7, rule_p8, rule_p9, rule_temporal)


def audit_output(c, rid, scope, task_type, inp, out, lang, meta):
    if not isinstance(out, dict):
        return
    for fn in RULE_FUNCS:
        fn(c, rid, scope, task_type, inp, out, lang, meta)


def run_audit(records, cases=()):
    c = _Collector()
    for r in sorted(records, key=lambda r: r["id"]):
        meta = {"goal_size": r.get("goal_size"), "safety_category": r.get("safety_category")}
        audit_output(c, r["id"], "expected_output", r["task_type"], r["input"], r["expected_output"], r["language"], meta)
        for k in r.get("contrastive") or []:
            audit_output(c, k["id"], "contrastive", r["task_type"], r["input"], k["output"], r["language"], meta)
        rule_memory_input(c, r["id"], r["input"])
    from evaluation.metrics.scoring import expand_units
    for case in sorted(cases, key=lambda x: x["id"]):
        for unit in expand_units(case):
            if unit.get("reference_output"):
                audit_output(c, unit["unit_id"], "eval_reference", unit["task_type"], unit["input"], unit["reference_output"],
                             unit.get("language"), {})
                rule_memory_input(c, unit["unit_id"], unit["input"])
    return c.findings


# ---------------------------------------------------------------------------------------------
# Known issues register + report

def _path_for(key, version):
    return repo_path(load_config("review")["paths"][key].format(version=version))


def load_known_issues(version=None):
    version = version or versions()["dataset_version"]
    path = _path_for("known_issues", version)
    if not path.exists():
        return []
    data = load_yaml(path) or {}
    return data.get("issues") or []


def risk_by_record(findings, known_issues, weights):
    """{example_id: score}, {example_id: [signal codes]} — contrastive findings count towards their parent
    example; each audit rule counts once per example (at its highest severity) so that one rule firing on
    every task of a long output does not outweigh a single serious finding."""
    score, signals = defaultdict(int), defaultdict(list)
    per_rule = defaultdict(dict)
    for f in findings:
        if f["scope"] not in ("expected_output", "contrastive", "input"):
            continue
        rid = re.sub(r"-c\d+$", "", f["record_id"])
        w = weights["audit_finding"].get(f["severity"], 0)
        if w:
            per_rule[rid][f["rule"]] = max(per_rule[rid].get(f["rule"], 0), w)
    for rid, rules in per_rule.items():
        score[rid] += sum(rules.values())
        signals[rid] += sorted(rules)
    for ki in known_issues:
        if ki.get("status") != "open":
            continue
        for rid in ki["records"]:
            score[rid] += weights["known_issue"][ki["severity"]]
            signals[rid].append(ki["id"])
    return score, signals


def build_report(version=None):
    version = version or versions()["dataset_version"]
    records = [r for r, _, _ in load_pool()]
    ids = {r["id"] for r in records}
    cases = [c for c, _ in load_eval_cases(repo_path(load_config("evaluation")["cases_dir"]))]
    findings = run_audit(records, cases)
    known = load_known_issues(version)
    # known issues may name cases of any (including frozen) evaluation version
    case_ids = {c["id"] for c, _ in load_eval_cases(repo_path("evaluation/cases"))}
    problems = []
    for ki in known:
        unknown = [r for r in ki.get("records", []) if r not in ids and r not in case_ids]
        if unknown:
            problems.append(f"{ki.get('id')}: unknown record(s) {unknown}")
    by_rule = Counter(f["rule"] for f in findings if f["scope"] == "expected_output")
    by_problem = defaultdict(Counter)
    for f in findings:
        by_problem[f["problem"]][f"{f['scope']}:{f['severity']}"] += 1
    summary = {
        "records_scanned": len(records), "eval_cases_scanned": len(cases),
        "findings_total": len(findings),
        "findings_by_scope": dict(sorted(Counter(f["scope"] for f in findings).items())),
        "expected_output_findings_by_rule": dict(sorted(by_rule.items())),
        "findings_by_problem": {k: dict(sorted(v.items())) for k, v in sorted(by_problem.items())},
        "examples_with_expected_output_findings": len({f["record_id"] for f in findings if f["scope"] == "expected_output"}),
        "known_issues": dict(sorted(Counter(k["severity"] for k in known).items())),
        "known_issue_records": len({r for k in known for r in k["records"]}),
    }
    report = {
        "report_version": "1.0", "dataset_version": version,
        "rules": {k: {"problem": v[0], "severity": SEVERITY[k], "description": v[1]} for k, v in sorted(RULES.items())},
        "summary": summary, "findings": findings, "known_issues": known,
    }
    errs = schemas.validate("audit_report", report)
    if errs:
        problems += [f"audit report schema: {e}" for e in errs[:5]]
    return report, problems


def run(version=None, write=False, as_json=False, record=None):
    report, problems = build_report(version)
    if record:
        report = {**report, "findings": [f for f in report["findings"] if f["record_id"].startswith(record)],
                  "known_issues": [k for k in report["known_issues"] if record in k["records"]]}
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print(report)
    for p in problems:
        print(f"✗ {p}")
    if write and not record:
        path = _path_for("audit_findings", report["dataset_version"])
        dump_json(report, path)
        print(f"Wrote {rel(path)}")
    return 1 if problems else 0


def _print(report):
    s = report["summary"]
    print(f"Audit v{report['dataset_version']}: {s['records_scanned']} examples, {s['eval_cases_scanned']} eval cases, "
          f"{s['findings_total']} heuristic findings ({s['findings_by_scope']}); "
          f"{sum(s['known_issues'].values()) if s['known_issues'] else 0} known issues on {s['known_issue_records']} records.")
    print("Heuristic findings are review aids — not verdicts. Severity is the rule's default, not a judgement.\n")
    by_problem = defaultdict(list)
    for f in report["findings"]:
        by_problem[f["problem"]].append(f)
    for prob in sorted(by_problem):
        fs = by_problem[prob]
        print(f"== {prob} ({len(fs)}) ==")
        for f in sorted(fs, key=lambda f: ({"high": 0, "medium": 1, "low": 2, "info": 3}[f["severity"]], f["record_id"])):
            if f["severity"] == "info":
                continue
            print(f"  [{f['severity']:6}] {f['record_id']:18} {f['scope']:15} {f['rule']}: {f['evidence'][:110]}")
        n_info = sum(1 for f in fs if f["severity"] == "info")
        if n_info:
            print(f"  (+{n_info} info-level findings; see --json)")
    if report["known_issues"]:
        print(f"\n== Known issues register ({len(report['known_issues'])}) ==")
        for k in report["known_issues"]:
            print(f"  {k['id']} [{k['severity']:6}] {k['status']:9} {', '.join(k['records'])}: {k['description'][:100]}")
