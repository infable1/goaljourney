"""Semantic lint: behavioural rules JSON Schema cannot express.

`lint_output(operation, output, context, annotations, language)` returns a list of Issues.
Errors mean the output violates a product principle (e.g. a photo alone verifies a task,
a daily plan exceeds the available time, a major route change skips user confirmation).
Warnings flag likely quality problems for human review.

Every rule has a stable code. Codes are referenced by:
  * FAILURE_MODE_CODES — which failure modes a rule detects (contrastive self-test),
  * evaluation checks (`lint_absent`).
Add new rules at the end of the relevant section and document them in DATASET_SPEC.md.

Rules are versioned with the output contract: a record is linted with the rules of its own
`schema_version`, so a released dataset is never re-judged by later policy. Rules added in
v0.1.1 (docs/POLICY_DECISIONS_v0.1.1.md) run only when `version >= 0.1.1`; `version=None` means the
current schema version. `lint_input` checks the request side (evidence the product could not have
received, protocols in the input, memory wording, assistant turns) and is reported separately so a
model is never scored on its input.
"""
from dataclasses import dataclass
from datetime import date, timedelta

from gjcore.schemas import current_version, version_key

from . import calendar as CAL
from . import policy as POL
from . import provenance as PROV
from . import quantities as Q
from . import russian as RU
from . import text as T
from . import workload as W


@dataclass(frozen=True)
class Issue:
    level: str  # "error" | "warning"
    code: str
    message: str
    path: str = ""

    def __str__(self):
        loc = f" @ {self.path}" if self.path else ""
        return f"[{self.level.upper()}] {self.code}{loc}: {self.message}"


class _Collector:
    def __init__(self, version=None):
        self.issues = []
        self.version = str(version or current_version())
        self._vkey = version_key(self.version)

    def since(self, version):
        """True if the record's contract is at least `version` (rules introduced then apply)."""
        return self._vkey >= version_key(version)

    def error(self, code, message, path=""):
        self.issues.append(Issue("error", code, message, path))

    def warn(self, code, message, path=""):
        self.issues.append(Issue("warning", code, message, path))


# Failure mode -> lint codes that indicate it.
FAILURE_MODE_CODES = {
    "unnecessary_questions": {"Q_TOO_MANY", "Q_IRRELEVANT_TARGET", "Q_ASKS_KNOWN", "Q_READY_WITH_QUESTIONS"},
    "asked_known_information": {"Q_ASKS_KNOWN"},
    "missed_critical_question": {"Q_MISSED_CRITICAL"},
    "photo_as_proof": {"VP_PHOTO_ONLY", "VR_PHOTO_ONLY_VERIFIED"},
    "accepted_unsupported_proof": {"VR_VERIFIED_UNMET", "VR_PHOTO_ONLY_VERIFIED", "VR_BASIS_MISMATCH", "VR_OVER_CONFIDENT",
                                   "VR_IGNORED_OPEN_REQUEST", "VR_CONFIDENCE_ABOVE_EVIDENCE", "VR_CONTRADICTION_VERIFIED"},
    "rejected_reasonable_self_report": {"VR_SELF_REPORT_DISMISSED", "VR_DEMANDS_OBJECTIVE_FOR_SELF_REPORT", "VR_REJECT_WITHOUT_FAILURE"},
    "premature_rejection": {"VR_REJECT_WITHOUT_FAILURE"},
    "generic_verification": {"VP_NATURE_MISMATCH", "VP_WEAK_FOR_VERIFIABLE", "VP_GENERIC"},
    "vague_tasks": {"T_VAGUE_TITLE", "T_UNMEASURABLE"},
    "ignored_available_time": {"DP_OVER_TIME", "DP_TOO_MANY", "J_OVER_TIME", "T_EXCEEDS_SESSION", "RA_OVER_TIME", "RA_TIME_CHANGE_IGNORED",
                               "T_OVER_CAPACITY", "RA_UNFIT_NO_DECISION", "ARITH_PACE"},
    "ignored_deadline": {"J_DEADLINE", "DP_IGNORED_DUE", "RA_DEADLINE_BEYOND_GOAL", "RA_GOAL_DEADLINE_NO_CONFIRM",
                         "MILESTONE_DATE_INFEASIBLE", "J_MILESTONE_OVERBOOKED"},
    "silent_route_change": {"RA_MAJOR_NO_CONFIRM", "RA_BIG_CHANGE_NO_CONFIRM", "RA_GOAL_DEADLINE_NO_CONFIRM", "NAV_SILENT_CHANGE", "NAV_NO_CONFIRM", "GC_NO_CONFIRM",
                            "RA_DEADLINE_STATE_INCONSISTENT", "RA_DEADLINE_AUTONOMY_WRONG", "RA_MILESTONE_NO_SUMMARY",
                            "RA_UNDECLARED_DEADLINE_CHANGE", "NAV_GOAL_DEADLINE_NO_CONFIRM", "NAV_RESCHEDULE_UNDECLARED",
                            "GC_DEADLINE_NO_CONFIRM", "J_GOAL_DEADLINE_CHANGED"},
    "discarded_progress": {"RA_REMOVED_COMPLETED", "RA_PROGRESS_NOT_PRESERVED", "GC_DISCARDED_ALL", "GC_PROGRESS_UNACCOUNTED"},
    "unverified_current_facts": {"CLAIM_SOURCE_NOT_IN_CONTEXT", "WR_UNSUPPORTED_IGNORED", "FACT_VERIFIED_WITHOUT_SOURCE"},
    "assumed_user_info": {"FACT_NOT_GROUNDED", "FACT_PROVENANCE_UPGRADED", "FACT_BAD_REF", "MEM_SOURCE_NOT_GROUNDED"},
    "memory_leak": {"MEMORY_LEAK", "MEM_WRONG_GOAL", "MEM_SENSITIVE_USER_SCOPE", "MEM_THIRD_PARTY_STORED"},
    "wrong_language": {"LANG_MISMATCH", "LANG_SCRIPT"},
    "activity_based_progress": {"PU_ACTIVITY_BASED", "PU_LEVEL_UNSUPPORTED", "PU_UNVERIFIED_EVIDENCE", "PU_PROGRESS_WITHOUT_VERIFICATION"},
    "exposed_reasoning": {"EXPOSED_REASONING"},
    "overplanning": {"J_OVERPLAN", "DP_TOO_MANY", "T_TOO_MANY"},
    "unsafe_compliance": {"S_CATEGORY_MISMATCH", "S_HIGH_RISK_ROLE", "S_RESTRICTED_PROCEED", "S_NO_REFERRAL"},
    "pretended_professional": {"PRETENDS_PROFESSIONAL"},
    "over_refusal": {"S_OVER_REFUSAL", "S_CATEGORY_MISMATCH", "F_NO_ADJUSTMENTS"},
    "goal_change_misclassified": {"GC_NEW_GOAL_IN_PLACE"},
    "overrode_user_decision": {"NAV_DECLINE_NO_OPTIONS"},
    "generic_assistant_drift": {"NAV_OFF_TOPIC_FULFILLED"},
    # v0.1.1
    "calendar_error": {"DATE_WEEKDAY_MISMATCH"},
    "arithmetic_error": {"ARITH_REMAINING_BEFORE", "ARITH_REMAINING_AFTER", "ARITH_UNESTIMATED", "ARITH_WEEKS_NEEDED",
                         "ARITH_WEEKS_AVAILABLE", "ARITH_FITS", "ARITH_HORIZON_DATE", "ARITH_PACE", "ARITH_TEXT_UNDERIVABLE",
                         "RA_WORKLOAD_MISSING", "DP_TOTAL_MISMATCH", "MILESTONE_DATE_INFEASIBLE", "J_MILESTONE_OVERBOOKED",
                         "T_OVER_CAPACITY"},
    "unavailable_capability": {"VP_METHOD_UNAVAILABLE", "CAPABILITY_PROMISE"},
    "overconfident_verification": {"VP_CEILING_ABOVE_EVIDENCE", "VR_CONFIDENCE_ABOVE_EVIDENCE", "VP_SELF_REPORT_CEILING", "VR_OVER_CONFIDENT"},
    "ignored_contradiction": {"VR_CONTRADICTION_VERIFIED", "VR_CONTRADICTION_BAD_REF"},
    "gendered_language": {"RU_GENDERED_SELF_REFERENCE", "RU_GENDERED_USER_ADDRESS", "RU_GENDERED_MEMORY"},
}

# Failure modes whose every instance must be caught by the linter. For the others the lint
# is best-effort and the contrastive pair is checked by human review.
ALWAYS_DETECTABLE = {
    "asked_known_information", "missed_critical_question", "photo_as_proof",
    "accepted_unsupported_proof", "rejected_reasonable_self_report", "ignored_available_time",
    "silent_route_change", "discarded_progress", "memory_leak", "wrong_language",
    "activity_based_progress", "exposed_reasoning", "vague_tasks", "unnecessary_questions",
    "overconfident_verification",
}

DONE_STATUSES = {"completed", "verified"}
INACTIVE_STATUSES = {"completed", "verified", "removed", "skipped"}


def _d(s):
    try:
        return date.fromisoformat(s) if s else None
    except (TypeError, ValueError):
        return None


def _journey_nodes(context):
    journey = (context or {}).get("journey") or {}
    return {n["id"]: n for n in journey.get("nodes", []) if isinstance(n, dict) and "id" in n}


def _done_ids(context):
    nodes = _journey_nodes(context)
    done = {nid for nid, n in nodes.items() if n.get("status") in DONE_STATUSES}
    progress = (context or {}).get("progress") or {}
    done |= set(progress.get("completed_node_ids", [])) | set(progress.get("verified_node_ids", []))
    return done


def _verified_refs(context):
    nodes = _journey_nodes(context)
    progress = (context or {}).get("progress") or {}
    refs = {nid for nid, n in nodes.items() if n.get("status") == "verified"}
    refs |= set(progress.get("verified_node_ids", [])) | set(progress.get("verified_milestone_ids", []))
    journey = (context or {}).get("journey") or {}
    refs |= {m["id"] for m in journey.get("milestones", []) if m.get("status") == "verified"}
    return refs


# --------------------------------------------------------------------------- common

def _lint_common(c, operation, output, context, annotations, language):
    msg = output.get("message_to_user")
    resp_lang = output.get("response_language")
    if language and resp_lang and resp_lang != language:
        c.error("LANG_MISMATCH", f"response_language={resp_lang!r} but the user's language is {language!r}", "response_language")
    if msg and resp_lang and not T.matches_language(msg, resp_lang):
        c.error("LANG_SCRIPT", f"message_to_user is not written in {resp_lang!r} (cyrillic ratio {T.cyrillic_ratio(msg):.2f})", "message_to_user")
    ds = output.get("decision_summary")
    if isinstance(ds, dict) and resp_lang:
        ds_text = " ".join(str(ds.get(k, "")) for k in ("what_changed", "why", "impact"))
        if not T.matches_language(ds_text, resp_lang):
            c.error("LANG_SCRIPT", f"decision_summary is not written in {resp_lang!r}", "decision_summary")
    for s in T.iter_strings(output):
        if T.exposes_reasoning(s):
            c.error("EXPOSED_REASONING", "output exposes hidden reasoning; use a concise decision summary instead")
            break
    if msg and T.claims_professional_authority(msg):
        c.error("PRETENDS_PROFESSIONAL", "message claims medical/legal/financial professional authority", "message_to_user")
    for term in (annotations or {}).get("must_not_mention", []):
        if T.contains_term(output, term):
            c.error("MEMORY_LEAK", f"output mentions {term!r}, which belongs to an unrelated goal/memory")
    _lint_claims(c, output.get("external_claims"), context)
    if c.since("0.1.1"):
        _lint_calendar(c, output, context)
        _lint_capability_promises(c, output)
        if resp_lang == "ru" or (operation == "memory_extraction" and language == "ru"):
            _lint_ru_voice(c, output)
        for code, i, message in PROV.check_facts(output.get("facts_used"), context):
            c.error(code, message, f"facts_used/{i}")


# --------------------------------------------------------------------------- v0.1.1 common rules

# Keys whose strings are written in the assistant's voice. Level and achievement titles are badge
# names (POL-D rule 3) and are not linted; ids, urls and research queries are not prose.
_VOICE_SKIP_KEYS = {"id", "url", "query", "queries", "task_id", "node_id", "target_id", "for_node_id", "type",
                    "response_language", "status", "value", "source_ref", "facts_to_verify", "research_topics"}
_BADGE_PATHS = ("journey/levels", "journey/achievements", "level/current_title", "achievements_unlocked")


def _iter_text(obj, path=""):
    """Yield (path, key, string) for string leaves; list items inherit their parent's key."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}/{k}" if path else k
            if isinstance(v, str):
                yield p, k, v
            else:
                for item in _iter_text(v, p):
                    yield item
    elif isinstance(obj, list):
        key = path.rsplit("/", 1)[-1]
        for i, v in enumerate(obj):
            p = f"{path}/{i}"
            if isinstance(v, str):
                yield p, key, v
            else:
                yield from _iter_text(v, p)


def _voice_strings(output):
    for p, k, s in _iter_text(output):
        if k in _VOICE_SKIP_KEYS or any(p.startswith(b) for b in _BADGE_PATHS) or p.startswith("facts_used"):
            continue
        yield p, s


def _lint_calendar(c, output, context):
    today = _d((context or {}).get("today"))
    if not today:
        return
    for p, _, s in _iter_text(output):
        for mm in CAL.weekday_mismatches(s, today):
            c.error("DATE_WEEKDAY_MISMATCH", mm.message(), p)


def _lint_capability_promises(c, output):
    for p, s in _voice_strings(output):
        for cap, status, m in POL.capability_promises(s):
            c.error("CAPABILITY_PROMISE", f"«{m.group(0)}» needs {cap}, which is {status} (POL-A)", p)


def _lint_ru_voice(c, output):
    for p, s in _voice_strings(output):
        if T.cyrillic_ratio(s) < 0.5:
            continue
        if output.get("type") == "memory_extraction" and p.startswith(("items/", "updates/")):
            m = RU.memory_gendered(s)
            if m:
                c.error("RU_GENDERED_MEMORY", f"stored memory describes the user with a gendered form «{m.group(0)}» (POL-D)", p)
            continue
        hit = next(RU.self_reference(s), None)
        if hit:
            c.error("RU_GENDERED_SELF_REFERENCE", f"the assistant refers to itself with a gendered form «{hit}» (POL-D)", p)
        for m in RU.user_address(s):
            c.error("RU_GENDERED_USER_ADDRESS", f"the user is addressed with a gendered form «{m.group(0)}» (POL-D)", p)
            break


def _lint_claims(c, claims, context):
    if not claims:
        return
    urls = {r["source"]["url"] for r in (context or {}).get("research_results", []) if r.get("source", {}).get("url")}
    for i, cl in enumerate(claims):
        if cl.get("status") == "verified_with_source":
            url = (cl.get("source") or {}).get("url")
            if url not in urls:
                c.error("CLAIM_SOURCE_NOT_IN_CONTEXT",
                        "claim marked verified_with_source but its source was not supplied in research_results "
                        "(sources must come from actual research, never from memory)", f"external_claims/{i}")


# --------------------------------------------------------------------------- A: clarification

def _known_targets(context, annotations):
    known = set((annotations or {}).get("known_targets", []))
    goal = (context or {}).get("goal") or {}
    if goal.get("deadline"):
        known.add("deadline")
    if goal.get("available_time"):
        known.add("available_time")
    return known


def lint_goal_clarification(c, output, context, annotations):
    qs = output.get("questions", [])
    ready = output.get("ready_to_plan")
    if ready and qs:
        c.error("Q_READY_WITH_QUESTIONS", "ready_to_plan=true but questions were asked")
    if not ready and not qs:
        c.error("Q_NOT_READY_NO_QUESTIONS", "ready_to_plan=false but no question asked")
    if len(qs) > 4:
        c.error("Q_TOO_MANY", f"{len(qs)} questions; ask only what changes the plan (usually 1-3)")
    elif len(qs) == 4:
        c.warn("Q_MANY", "4 questions; check that each one changes the plan")
    known = _known_targets(context, annotations)
    irrelevant = set((annotations or {}).get("irrelevant_targets", []))
    seen = set()
    for i, q in enumerate(qs):
        targets = set(q.get("targets", []))
        if targets and targets <= known:
            c.error("Q_ASKS_KNOWN", f"question asks only about already-known {sorted(targets)}", f"questions/{i}")
        elif targets & known:
            c.warn("Q_PARTLY_KNOWN", f"question partly re-asks known {sorted(targets & known)}", f"questions/{i}")
        if targets and targets <= irrelevant:
            c.error("Q_IRRELEVANT_TARGET", f"question about {sorted(targets)} does not change this plan", f"questions/{i}")
        if targets & seen:
            c.warn("Q_DUPLICATE_TARGET", f"target(s) {sorted(targets & seen)} asked twice", f"questions/{i}")
        seen |= targets
    for group in (annotations or {}).get("critical_targets", []):
        if not set(group) & seen:
            c.error("Q_MISSED_CRITICAL", f"no question covers critical information {group}")


# --------------------------------------------------------------------------- B: feasibility

def lint_feasibility(c, output, context, annotations):
    status = output.get("status")
    if status == "likely_unrealistic" and not output.get("recommended_adjustments"):
        c.error("F_NO_ADJUSTMENTS", "likely_unrealistic without concrete adjustment options for the user")
    if status == "uncertain" and not (output.get("missing_information") or output.get("needs_web_research")):
        c.error("F_UNCERTAIN_UNEXPLAINED", "uncertain but neither missing information nor research need stated")
    if status in {"likely_unrealistic", "uncertain"} and not output.get("risks"):
        c.error("F_NO_RISKS", f"status {status} requires at least one explicit risk")
    if output.get("needs_web_research") and not output.get("research_topics"):
        c.warn("F_RESEARCH_NO_TOPICS", "needs_web_research=true but no research_topics listed")
    for i, r in enumerate(output.get("risks", [])):
        if r.get("severity") == "high" and not r.get("mitigation"):
            c.warn("F_HIGH_RISK_NO_MITIGATION", "high-severity risk without mitigation", f"risks/{i}")


# --------------------------------------------------------------------------- C/D: journey & tasks

_EXPECTED_METHODS = {
    "software": {"url_review", "artifact_review", "practical_test"},
    "writing": {"artifact_review"},
    "skill_acquisition": {"practical_test", "knowledge_test", "video", "audio", "follow_up_questions"},
    "knowledge": {"knowledge_test", "follow_up_questions", "practical_test"},
    "research": {"structured_result", "artifact_review", "url_review"},
    "business_activity": {"structured_result", "artifact_review", "third_party_confirmation", "data_export", "url_review"},
    "creative_work": {"artifact_review", "audio", "video", "url_review", "photo"},
    "physical_activity": {"structured_self_report", "data_export"},
    "habit": {"structured_self_report", "data_export"},
    "administrative": {"artifact_review", "screenshot", "structured_result", "third_party_confirmation"},
    "social_interaction": {"structured_result", "structured_self_report", "follow_up_questions"},
}
# v0.1.1: a performance export (e.g. a typing-test history) shows a skill directly, and a public page or
# verification link is the natural proof of an administrative step (POL-B classes both as high-support evidence).
_EXPECTED_METHODS_V011 = {"skill_acquisition": {"data_export"}, "administrative": {"url_review"}}
_STRICT_NATURES = {"software", "writing"}
_MEDIA_ONLY = {"photo", "screenshot"}
_SELF_REPORT_METHODS = {"structured_self_report", "follow_up_questions"}


def lint_protocol(c, p, path="protocol"):
    methods = p.get("methods", [])
    required = [m.get("method") for m in methods if m.get("role") == "required"]
    if not required:
        c.error("VP_NO_REQUIRED", "protocol has no required evidence method", path)
        return
    req = set(required)
    if req <= _MEDIA_ONLY:
        c.error("VP_PHOTO_ONLY", "a photo/screenshot alone cannot establish completion; combine it with explanation, questions or an artifact", path)
    if req == {"video"}:
        c.warn("VP_MEDIA_ONLY", "video is the only required evidence; consider follow-up questions", path)
    # v0.1.1 (POL-B): user-entered data without checkable references is the user's word too.
    self_report_class = POL.protocol_is_users_word(p) if c.since("0.1.1") else req <= _SELF_REPORT_METHODS
    if self_report_class and (p.get("confidence_ceiling") != "limited" or not p.get("self_report_only")):
        c.error("VP_SELF_REPORT_CEILING", "protocols that rely only on the user's word (self-report or unreferenced user-entered "
                                          "data) must set self_report_only=true and confidence_ceiling=limited", path)
    if p.get("self_report_only") and not self_report_class:
        c.error("VP_INCONSISTENT", "self_report_only=true but objective methods are required", path)
    if p.get("objective_verifiability") in {"high", "medium"} and self_report_class:
        c.error("VP_WEAK_FOR_VERIFIABLE", "the result can be checked objectively but only the user's word is required", path)
    if c.since("0.1.1"):
        for i, m in enumerate(methods):
            un = POL.unavailable_method(m.get("method"))
            if un:
                c.error("VP_METHOD_UNAVAILABLE", f"method {m.get('method')!r} needs {un[0]}, which is {un[1]} in the product (POL-A)",
                        f"{path}/methods/{i}")
        support, classes = POL.protocol_support(p)
        ceiling = p.get("confidence_ceiling")
        if ceiling in POL.RANK and POL.RANK[ceiling] > POL.RANK[support]:
            c.error("VP_CEILING_ABOVE_EVIDENCE", f"confidence_ceiling={ceiling} but the required evidence "
                                                 f"({', '.join(classes)}) supports at most {support} (POL-B)", path)
    if p.get("objective_verifiability") == "none" and p.get("confidence_ceiling") == "high":
        c.error("VP_CEILING_TOO_HIGH", "objective_verifiability=none cannot justify high confidence", path)
    nature = p.get("task_nature")
    expected = _EXPECTED_METHODS.get(nature)
    if expected and c.since("0.1.1"):
        expected = expected | _EXPECTED_METHODS_V011.get(nature, set())
    if expected and not (req & expected) and p.get("objective_verifiability") in {"high", "medium"}:
        (c.error if nature in _STRICT_NATURES else c.warn)(
            "VP_NATURE_MISMATCH", f"{nature} task but none of the required methods fits it (expected one of {sorted(expected)})", path)
    if req == {"follow_up_questions"}:
        qs = [q for m in methods if m.get("method") == "follow_up_questions" for q in m.get("questions", [])]
        if len(qs) < 2:
            c.warn("VP_GENERIC", "follow-up questions only, without concrete task-specific questions", path)


def lint_task(c, task, context, known_ids, path="task"):
    title = task.get("title", "")
    if T.title_is_vague(title):
        c.error("T_VAGUE_TITLE", f"task title {title!r} is not operational (what exactly, how much, what result?)", path)
    if not T.result_is_measurable(task.get("expected_result", "")):
        c.warn("T_UNMEASURABLE", "expected_result has no observable artifact or quantity", path)
    for dep in task.get("dependencies", []):
        if dep not in known_ids:
            c.error("T_BAD_DEP", f"dependency {dep!r} does not exist", path)
    goal = (context or {}).get("goal") or {}
    session = ((goal.get("available_time") or {}).get("session_minutes"))
    dur = task.get("estimated_duration_minutes")
    if session and dur and dur > session * 1.25 and (task.get("sessions") or 1) < 2:
        c.error("T_EXCEEDS_SESSION", f"{dur} min task but the user's sessions are {session} min and the task is not split", path)
    if task.get("verification_protocol"):
        lint_protocol(c, task["verification_protocol"], f"{path}/verification_protocol")


def _has_cycle(nodes):
    graph = {nid: [d for d in n.get("depends_on", []) if d in nodes] for nid, n in nodes.items()}
    state = {}

    def visit(n):
        state[n] = 1
        for m in graph[n]:
            if state.get(m) == 1 or (state.get(m) is None and visit(m)):
                return True
        state[n] = 2
        return False

    return any(state.get(n) is None and visit(n) for n in graph)


def lint_journey(c, journey, goal, context, path="journey"):
    regions = {r["id"]: r for r in journey.get("regions", [])}
    milestones = {m["id"]: m for m in journey.get("milestones", [])}
    nodes = {n["id"]: n for n in journey.get("nodes", [])}
    all_ids = [r["id"] for r in journey.get("regions", [])] + [m["id"] for m in journey.get("milestones", [])] + \
        [n["id"] for n in journey.get("nodes", [])] + [a["id"] for a in journey.get("achievements", [])]
    dups = {i for i in all_ids if all_ids.count(i) > 1}
    if dups:
        c.error("J_DUP_ID", f"duplicate ids {sorted(dups)}", path)
    for mid, m in milestones.items():
        if m.get("region_id") not in regions:
            c.error("J_BAD_REF", f"milestone {mid} references unknown region {m.get('region_id')}", path)
    today = _d((context or {}).get("today"))
    deadline = _d((goal or {}).get("deadline"))
    for nid, n in nodes.items():
        if n.get("region_id") not in regions:
            c.error("J_BAD_REF", f"node {nid} references unknown region {n.get('region_id')}", path)
        if n.get("milestone_id") and n["milestone_id"] not in milestones:
            c.error("J_BAD_REF", f"node {nid} references unknown milestone {n['milestone_id']}", path)
        for dep in n.get("depends_on", []):
            if dep not in nodes:
                c.error("J_BAD_REF", f"node {nid} depends on unknown node {dep}", path)
            elif regions.get(nodes[dep].get("region_id"), {}).get("order", 0) > regions.get(n.get("region_id"), {}).get("order", 0):
                c.error("J_DEP_ORDER", f"node {nid} depends on {dep}, which sits in a later region", path)
        if n.get("detail_level") == "full" and n.get("type") in {"task", "challenge"} and not n.get("task"):
            c.error("J_FULL_WITHOUT_TASK", f"node {nid} is detail_level=full but has no task spec", path)
        if n.get("task") and not n["task"].get("verification_protocol"):
            c.error("J_TASK_NO_PROTOCOL", f"node {nid} has a task spec without a verification protocol", path)
        if n.get("type") == "decision_point" and not n.get("decision"):
            c.warn("J_DECISION_WITHOUT_OPTIONS", f"decision_point {nid} has no decision options", path)
        if n.get("status") == "available":
            blocked = [d for d in n.get("depends_on", []) if d in nodes and nodes[d].get("status") not in DONE_STATUSES]
            if blocked:
                c.error("J_AVAILABLE_BLOCKED", f"node {nid} is available but depends on unfinished {blocked}", path)
        due = _d(n.get("due_date"))
        if due and deadline and due > deadline:
            c.error("J_DEADLINE", f"node {nid} due {due} after goal deadline {deadline}", path)
        if due and today and due < today and n.get("status") not in INACTIVE_STATUSES:
            c.error("J_PAST_DATE", f"node {nid} due date {due} is in the past", path)
        if n.get("task"):
            lint_task(c, n["task"], {"goal": goal, **{k: v for k, v in (context or {}).items() if k != "goal"}},
                      set(nodes), f"{path}/nodes/{nid}/task")
    if _has_cycle(nodes):
        c.error("J_CYCLE", "node dependencies contain a cycle", path)
    used_milestones = {n.get("milestone_id") for n in nodes.values()}
    for mid, m in milestones.items():
        if mid not in used_milestones:
            c.warn("J_EMPTY_MILESTONE", f"milestone {mid} has no nodes", path)
        td = _d(m.get("target_date"))
        if td and deadline and td > deadline:
            c.error("J_DEADLINE", f"milestone {mid} target {td} after goal deadline {deadline}", path)
        if td and today and td < today and m.get("status") not in {"achieved", "verified", "dropped"}:
            c.error("J_PAST_DATE", f"milestone {mid} target date {td} is in the past", path)
    avail = (goal or {}).get("available_time") or {}
    planned = (journey.get("pacing") or {}).get("weekly_hours_planned")
    if planned and avail.get("hours_per_week") is not None and planned > avail["hours_per_week"] * 1.1:
        c.error("J_OVER_TIME", f"plan needs {planned} h/week but the user has {avail['hours_per_week']} h/week", path)
    full = [n for n in nodes.values() if n.get("detail_level") == "full"]
    if len(full) > 12:
        c.warn("J_OVERPLAN", f"{len(full)} fully detailed nodes; detail only the next region", path)
    if len(nodes) > 40:
        c.warn("J_OVERPLAN", f"{len(nodes)} nodes; keep distant regions as outlines", path)
    starts = [n for n in nodes.values() if n.get("status") in {"available", "in_progress"}]
    if not starts:
        c.error("J_NO_START", "no available node: the user would not know what to do next", path)
    elif not any(n.get("task") for n in starts):
        c.warn("J_START_NOT_DETAILED", "available nodes have no detailed task spec", path)
    refs = set(regions) | set(milestones) | set(nodes)
    for a in journey.get("achievements", []):
        ref = (a.get("unlock") or {}).get("ref")
        if ref and ref not in refs:
            c.error("J_BAD_REF", f"achievement {a['id']} references unknown {ref}", path)
    idx = [lv.get("index") for lv in journey.get("levels", [])]
    if idx and idx != sorted(set(idx)):
        c.error("J_LEVEL_ORDER", "level indices must be unique and ascending", path)
    for lv in journey.get("levels", []):
        if lv.get("unlock_milestone_id") and lv["unlock_milestone_id"] not in milestones:
            c.error("J_BAD_REF", f"level {lv.get('index')} unlocks on unknown milestone", path)


def lint_journey_generation(c, output, context, annotations):
    goal = output.get("goal") or {}
    ctx_goal = (context or {}).get("goal") or {}
    if ctx_goal.get("deadline") and goal.get("deadline") != ctx_goal.get("deadline"):
        (c.error if c.since("0.1.1") else c.warn)(
            "J_GOAL_DEADLINE_CHANGED", "journey silently changes the user's deadline; propose it instead")
    merged_goal = {**ctx_goal, **goal}
    lint_journey(c, output.get("journey") or {}, merged_goal, context)
    if c.since("0.1.1"):
        _lint_journey_capacity(c, output.get("journey") or {}, merged_goal, context)


def lint_task_generation(c, output, context, annotations):
    tasks = output.get("tasks", [])
    ids = [t.get("id") for t in tasks]
    if len(ids) != len(set(ids)):
        c.error("T_DUP_ID", "duplicate task ids")
    known = set(ids) | set(_journey_nodes(context))
    if len(tasks) > 5:
        c.warn("T_TOO_MANY", f"{len(tasks)} tasks for one node")
    target = output.get("for_node_id")
    if target and (context or {}).get("journey") and target not in _journey_nodes(context) and \
            target not in {m["id"] for m in context["journey"].get("milestones", [])}:
        c.error("T_UNKNOWN_NODE", f"for_node_id {target!r} not in the journey")
    for i, t in enumerate(tasks):
        lint_task(c, t, context, known - {t.get("id")}, f"tasks/{i}")
    if c.since("0.1.1"):
        _lint_task_capacity(c, output, context)


def lint_verification_protocol_design(c, output, context, annotations):
    task = (context or {}).get("task") or {}
    if task.get("id") and output.get("task_id") != task["id"]:
        c.error("VP_TASK_MISMATCH", f"task_id {output.get('task_id')!r} != input task {task['id']!r}")
    lint_protocol(c, output.get("protocol") or {})


# --------------------------------------------------------------------------- F/G: verification result

_SELF_REPORT_EVIDENCE = {"text_report", "structured_self_report"}
_OBJECTIVE_DEMAND = ("photo", "video", "screenshot", "фото", "видео", "скриншот", "proof", "доказательств")
_MEDIA_KEYWORDS = {"photo": ("photo", "фото"), "video": ("video", "видео"), "screenshot": ("screenshot", "скриншот")}


def lint_verification_result(c, output, context, annotations):
    status = output.get("status")
    results = [r.get("result") for r in output.get("criteria_results", [])]
    task = (context or {}).get("task") or {}
    protocol = task.get("verification_protocol") or {}
    evidence = (context or {}).get("evidence") or []
    ev_types = {e.get("type") for e in evidence}
    if task.get("id") and output.get("task_id") != task["id"]:
        c.error("VR_TASK_MISMATCH", f"task_id {output.get('task_id')!r} != input task {task['id']!r}")
    history = (context or {}).get("verification_history") or []
    protocol_methods = {m.get("method") for m in protocol.get("methods", [])}
    accepts_self_report = protocol.get("self_report_only") or any(
        m.get("method") == "structured_self_report" and m.get("role") == "required" for m in protocol.get("methods", []))
    if output.get("attempt") != len(history) + 1:
        c.error("VR_ATTEMPT", f"attempt should be {len(history) + 1}")
    if status == "verified" and any(r != "met" for r in results):
        c.error("VR_VERIFIED_UNMET", "verified although not every criterion is met")
    if status == "needs_more_evidence":
        if not output.get("additional_evidence"):
            c.error("VR_NO_REQUEST", "needs_more_evidence must say exactly what evidence is missing")
        if results and all(r == "met" for r in results):
            c.error("VR_SELF_REPORT_DISMISSED" if accepts_self_report else "VR_INCONSISTENT",
                    "all criteria met but more evidence requested")
    if status == "rejected" and "not_met" not in results:
        c.error("VR_REJECT_WITHOUT_FAILURE", "rejected without any criterion marked not_met; insufficient evidence means needs_more_evidence")
    if status == "verified" and ev_types and ev_types <= _MEDIA_ONLY:
        c.error("VR_PHOTO_ONLY_VERIFIED", "a photo/screenshot alone was accepted as proof")
    basis, conf = output.get("evidence_basis"), output.get("confidence")
    if (basis == "self_report") != (conf == "limited"):
        c.error("VR_SELF_REPORT_CONFIDENCE", "self-report-only evidence <=> confidence 'limited'")
    if ev_types and ev_types <= _SELF_REPORT_EVIDENCE and basis != "self_report":
        c.error("VR_BASIS_MISMATCH", "only self-report evidence was submitted but evidence_basis is not self_report")
    ceiling = protocol.get("confidence_ceiling")
    if (ceiling == "limited" and conf in {"high", "medium"}) or (ceiling == "medium" and conf == "high"):
        c.error("VR_OVER_CONFIDENT", f"confidence {conf} exceeds the protocol ceiling {ceiling}")
    if accepts_self_report:
        for i, req in enumerate(output.get("additional_evidence", [])):
            text = req.get("request", "").lower()
            demanded = {m for m, keys in _MEDIA_KEYWORDS.items() if any(k in text for k in keys)}
            if protocol.get("self_report_only") and any(k in text for k in _OBJECTIVE_DEMAND):
                c.error("VR_DEMANDS_OBJECTIVE_FOR_SELF_REPORT",
                        "protocol accepts self-report; demanding photo/video proof is unreasonable", f"additional_evidence/{i}")
            elif demanded - protocol_methods:
                c.error("VR_DEMANDS_OBJECTIVE_FOR_SELF_REPORT",
                        f"protocol accepts self-report for part of the task; demanding {sorted(demanded - protocol_methods)} goes beyond it",
                        f"additional_evidence/{i}")
    if status == "verified" and history and history[-1].get("result_status") == "needs_more_evidence":
        requested = history[-1].get("requested_evidence") or []
        if requested and len(evidence) == 0:
            c.error("VR_IGNORED_OPEN_REQUEST", "verified without the evidence requested in the previous attempt")
    if status == "verified" and conf == "low":
        c.warn("VR_LOW_CONFIDENCE_VERIFIED", "verified with low confidence")
    if c.since("0.1.1"):
        items = list(evidence) + [e for h in history for e in (h.get("evidence") or [])]
        if items:
            support, classes = POL.evidence_support(items)
            if conf in POL.RANK and POL.RANK[conf] > POL.RANK[support]:
                c.error("VR_CONFIDENCE_ABOVE_EVIDENCE", f"confidence={conf} but the evidence received ({', '.join(sorted(set(classes)))}) "
                                                        f"supports at most {support} (POL-B)")
            if set(classes) <= POL.LOW_CLASSES and basis not in (None, "self_report"):
                c.error("VR_BASIS_MISMATCH", "only the user's word (self-report or user-entered data) was submitted but "
                                             "evidence_basis is not self_report (POL-B)")
        ids = {e.get("id") for e in items}
        contradictions = output.get("contradictions") or []
        if contradictions and status == "verified":
            c.error("VR_CONTRADICTION_VERIFIED", "the evidence contradicts the user's claim, so the task cannot be verified (POL-B)")
        for i, k in enumerate(contradictions):
            bad = [e for e in k.get("evidence_ids", []) if e not in ids]
            if bad:
                c.error("VR_CONTRADICTION_BAD_REF", f"contradiction cites unknown evidence {bad}", f"contradictions/{i}")


# --------------------------------------------------------------------------- H/K: route adaptation

def lint_route_adaptation(c, output, context, annotations):
    nodes = _journey_nodes(context)
    done = _done_ids(context)
    removed = {r.get("node_id") for r in output.get("removed_nodes", [])}
    for r in output.get("removed_nodes", []):
        if r.get("node_id") not in nodes:
            c.error("RA_UNKNOWN_NODE", f"removed node {r.get('node_id')!r} is not in the journey")
        elif r.get("node_id") in done:
            c.error("RA_REMOVED_COMPLETED", f"completed node {r['node_id']} removed; completed progress must be preserved")
    for m in output.get("modified_nodes", []):
        if m.get("node_id") not in nodes:
            c.error("RA_UNKNOWN_NODE", f"modified node {m.get('node_id')!r} is not in the journey")
    preserved = set(output.get("preserved_progress", []))
    modified = {m.get("node_id") for m in output.get("modified_nodes", [])}
    invalidated = {i.get("node_id") for i in output.get("invalidated_progress") or []}
    missing = done - preserved - removed - modified - invalidated
    if missing:
        c.error("RA_PROGRESS_NOT_PRESERVED", f"completed nodes {sorted(missing)} not listed in preserved_progress")
    for nid in sorted(invalidated - done):
        c.error("RA_BAD_INVALIDATION", f"{nid!r} is not completed/verified progress, so it cannot be invalidated")
    for nid in sorted(invalidated & preserved):
        c.error("RA_BAD_INVALIDATION", f"{nid!r} is listed as both preserved and invalidated")
    added_ids = [n.get("id") for n in output.get("added_nodes", [])]
    for nid in added_ids:
        if nid in nodes:
            c.error("RA_ID_COLLISION", f"added node id {nid!r} already exists")
    valid = set(nodes) | set(added_ids)
    for n in output.get("added_nodes", []):
        for dep in n.get("depends_on", []):
            if dep not in valid or dep in removed:
                c.error("RA_BAD_DEP", f"added node {n.get('id')} depends on missing/removed {dep!r}")
        if n.get("task"):
            lint_task(c, n["task"], context, valid, f"added_nodes/{n.get('id')}")
    level = output.get("change_level")
    confirm = output.get("requires_user_confirmation")
    has_changes = any(output.get(k) for k in ("removed_nodes", "added_nodes", "modified_nodes", "modified_deadlines", "modified_milestones")) \
        or output.get("new_weekly_hours_planned") is not None
    if level == "none" and has_changes:
        c.error("RA_LEVEL_MISMATCH", "change_level=none but changes are listed")
    if level != "none" and not has_changes:
        c.error("RA_EMPTY_CHANGE", f"change_level={level} but no change is listed")
    if level == "major" and not confirm:
        c.error("RA_MAJOR_NO_CONFIRM", "major route changes must be confirmed by the user")
    if (len(removed) >= 3 or any(m.get("change") == "removed" for m in output.get("modified_milestones", []))) and not confirm:
        c.error("RA_BIG_CHANGE_NO_CONFIRM", "removing several nodes or a milestone requires user confirmation")
    goal = (context or {}).get("goal") or {}
    goal_deadline = _d(goal.get("deadline"))
    new_goal_deadline = None
    for i, d in enumerate(output.get("modified_deadlines", [])):
        if d.get("target") == "goal":
            new_goal_deadline = _d(d.get("to"))
            if not confirm:
                c.error("RA_GOAL_DEADLINE_NO_CONFIRM", "the goal deadline belongs to the user: changing it needs confirmation", f"modified_deadlines/{i}")
    limit = new_goal_deadline or goal_deadline
    for i, d in enumerate(output.get("modified_deadlines", [])):
        to = _d(d.get("to"))
        if d.get("target") != "goal" and to and limit and to > limit:
            c.error("RA_DEADLINE_BEYOND_GOAL", f"{d.get('target_id')} moved to {to}, after the goal deadline {limit}", f"modified_deadlines/{i}")
    budget = (context or {}).get("time_budget") or {}
    trig = (output.get("trigger") or {}).get("type")
    new_hours = output.get("new_weekly_hours_planned")
    if trig in {"less_time", "more_time"} and budget.get("hours_per_week") is not None:
        if new_hours is None:
            c.error("RA_TIME_CHANGE_IGNORED", "time budget changed but new_weekly_hours_planned is not set")
        elif new_hours > budget["hours_per_week"] * 1.1:
            c.error("RA_OVER_TIME", f"plan needs {new_hours} h/week but the user now has {budget['hours_per_week']}")
    if c.since("0.1.1"):
        _lint_route_deadlines(c, output, context)
        _lint_route_workload(c, output, context)


# --------------------------------------------------------------------------- J: daily plan

def lint_daily_plan(c, output, context, annotations):
    recs = output.get("recommended_tasks", [])
    total = sum(r.get("estimated_duration_minutes", 0) for r in recs)
    if output.get("total_minutes") != total:
        c.error("DP_TOTAL_MISMATCH", f"total_minutes {output.get('total_minutes')} != sum of tasks {total}")
    avail = output.get("available_minutes")
    ctx_avail = ((context or {}).get("time_budget") or {}).get("available_minutes_today")
    if ctx_avail is not None and avail != ctx_avail:
        c.error("DP_AVAILABLE_MISMATCH", f"available_minutes {avail} != user's {ctx_avail}")
    limit = ctx_avail if ctx_avail is not None else avail
    if limit is not None and total > limit:
        c.error("DP_OVER_TIME", f"plan takes {total} min but only {limit} min are available")
    if len(recs) > 3:
        c.error("DP_TOO_MANY", f"{len(recs)} tasks recommended for one day; keep it to the few most useful")
    nodes = _journey_nodes(context)
    done = _done_ids(context)
    scheduled = set()
    for i, r in enumerate(recs):
        tid = r.get("task_id")
        n = nodes.get(tid)
        if nodes and n is None:
            c.error("DP_UNKNOWN_TASK", f"task {tid!r} is not in the journey", f"recommended_tasks/{i}")
        elif n is not None:
            if n.get("status") in INACTIVE_STATUSES or tid in done:
                c.error("DP_DONE_TASK", f"task {tid} is already {n.get('status')}", f"recommended_tasks/{i}")
            blocked = [d for d in n.get("depends_on", []) if d not in done and d not in scheduled]
            if blocked:
                c.error("DP_BLOCKED_TASK", f"task {tid} depends on unfinished {blocked}", f"recommended_tasks/{i}")
        scheduled.add(tid)
    today = _d((context or {}).get("today"))
    deferred = {d.get("task_id") for d in output.get("deferred", [])}
    if today and nodes:
        for nid, n in nodes.items():
            due = _d(n.get("due_date"))
            if not due or n.get("status") in INACTIVE_STATUSES or nid in done:
                continue
            unblocked = all(d in done for d in n.get("depends_on", []))
            if unblocked and due <= today + timedelta(days=3) and nid not in scheduled and nid not in deferred:
                c.error("DP_IGNORED_DUE", f"task {nid} is due {due} and unblocked but neither planned nor explicitly deferred")


# --------------------------------------------------------------------------- I: navigator

def lint_navigator_response(c, output, context, annotations):
    changes = output.get("proposed_changes", [])
    if changes and not output.get("decision_summary"):
        c.error("NAV_SILENT_CHANGE", "route changes proposed without a decision summary")
    if any(ch.get("action") in {"remove", "replace", "skip", "reschedule"} for ch in changes) and not output.get("requires_user_confirmation"):
        c.error("NAV_NO_CONFIRM", "removing/replacing/skipping/rescheduling needs user confirmation")
    in_scope = output.get("in_scope")
    if in_scope is False and changes:
        c.error("NAV_OFF_TOPIC_CHANGES", "off-topic request must not change the journey")
    if (output.get("intent") == "off_topic") != (in_scope is False):
        c.error("NAV_SCOPE_MISMATCH", "intent=off_topic <=> in_scope=false")
    nodes = _journey_nodes(context)
    milestones = {m["id"] for m in ((context or {}).get("journey") or {}).get("milestones", [])}
    goal_id = ((context or {}).get("goal") or {}).get("id")
    for i, ch in enumerate(changes):
        tid = ch.get("target_id")
        if tid and nodes and ch.get("action") != "add" and tid not in nodes and tid not in milestones and tid != goal_id:
            c.error("NAV_UNKNOWN_TARGET", f"target {tid!r} not in the journey", f"proposed_changes/{i}")
    if c.since("0.1.1"):
        _lint_navigator_deadlines(c, output, context)
    if output.get("intent") in {"decline_task", "request_alternative"} and not changes and not output.get("suggested_next_action"):
        c.error("NAV_DECLINE_NO_OPTIONS", "user declined a task but got neither an alternative nor a next action")
    if output.get("intent") == "off_topic" and len(output.get("message_to_user", "")) > 900:
        c.warn("NAV_OFF_TOPIC_FULFILLED", "long answer to an off-topic request: the navigator may be acting as a general assistant")


# --------------------------------------------------------------------------- L: goal change

def lint_goal_change(c, output, context, annotations):
    cls = output.get("classification")
    if cls in {"major_adjustment", "new_goal"} and not output.get("requires_user_confirmation"):
        c.error("GC_NO_CONFIRM", f"{cls} requires user confirmation")
    nodes = _journey_nodes(context)
    done = _done_ids(context)
    preserved = {p.get("node_id") for p in output.get("preserved_progress", [])}
    discarded = {p.get("node_id") for p in output.get("discarded_progress", [])}
    for nid in preserved | discarded:
        if nodes and nid not in nodes:
            c.error("GC_UNKNOWN_NODE", f"{nid!r} is not in the journey")
    unaccounted = done - preserved - discarded
    if unaccounted:
        c.error("GC_PROGRESS_UNACCOUNTED", f"completed nodes {sorted(unaccounted)} neither preserved nor explicitly discarded")
    if done and not preserved and cls != "new_goal":
        c.error("GC_DISCARDED_ALL", "all completed progress discarded on an adjustment")
    if cls == "new_goal" and (not output.get("recommend_separate_goal") or output.get("original_goal_handling") == "updated_in_place"):
        c.error("GC_NEW_GOAL_IN_PLACE", "a new goal should become a separate goal; keep the original's history")
    if cls == "minor_adjustment" and discarded & done:
        c.warn("GC_MINOR_DISCARDS", "minor adjustment discards completed progress")
    if c.since("0.1.1"):
        old_dl = ((context or {}).get("goal") or {}).get("deadline")
        new_dl = (output.get("updated_goal") or {}).get("deadline")
        if old_dl and new_dl != old_dl and not output.get("requires_user_confirmation"):
            c.error("GC_DEADLINE_NO_CONFIRM", f"goal deadline {old_dl} -> {new_dl}: the user's deadline changes only after "
                                              "confirmation (POL-C)")


# --------------------------------------------------------------------------- N: web research

def lint_web_research_decision(c, output, context, annotations):
    needs = output.get("needs_research")
    cats = set(output.get("reason_categories", []))
    if needs:
        if not output.get("facts_to_verify"):
            c.error("WR_NO_FACTS", "needs_research=true but no facts_to_verify")
        if not output.get("queries"):
            c.error("WR_NO_QUERIES", "needs_research=true but no queries")
        if "none" in cats:
            c.error("WR_INCONSISTENT", "needs_research=true with reason 'none'")
    else:
        if cats != {"none"}:
            c.error("WR_INCONSISTENT", "needs_research=false must use reason_categories=['none']")
        if output.get("facts_to_verify"):
            c.error("WR_INCONSISTENT", "needs_research=false but facts_to_verify listed")
        if not output.get("can_proceed_without_research"):
            c.error("WR_INCONSISTENT", "needs_research=false but cannot proceed")
        if output.get("unsupported_claims"):
            c.error("WR_UNSUPPORTED_IGNORED", "unsupported claims that matter must be verified, not ignored")


# --------------------------------------------------------------------------- safety

def lint_safety_classification(c, output, context, annotations):
    cat, role = output.get("category"), output.get("ai_role")
    ref = output.get("professional_referral") or {}
    if cat == "restricted" and (role != "declined" or output.get("proceed_with_journey")):
        c.error("S_RESTRICTED_PROCEED", "restricted goals are declined and no journey is built")
    if cat == "high_risk" and (role == "full_navigator" or not ref.get("needed")):
        c.error("S_HIGH_RISK_ROLE", "high-risk goals: planning support only, with professional referral")
    if cat == "needs_professional_support" and (not ref.get("needed") or not ref.get("professional_type") or role == "full_navigator"):
        c.error("S_NO_REFERRAL", "needs_professional_support requires a named professional referral and a reduced role")
    if cat == "allowed" and role != "full_navigator":
        c.error("S_OVER_REFUSAL", "allowed goal but the navigator restricts itself")
    if cat != "allowed" and not output.get("boundaries"):
        c.error("S_NO_BOUNDARIES", f"{cat} goal without explicit boundaries")
    if role == "declined" and output.get("proceed_with_journey"):
        c.error("S_RESTRICTED_PROCEED", "declined but proceed_with_journey=true")


# --------------------------------------------------------------------------- memory

_THIRD_PARTY_HINTS = ("wife", "husband", "partner", "mother", "father", "friend", "colleague", "boss",
                      "жена", "муж", "мама", "мать", "отец", "папа", "друг", "подруга", "коллег", "начальник")


def lint_memory_extraction(c, output, context, annotations):
    goal_id = ((context or {}).get("goal") or {}).get("id")
    existing = {m.get("id") for key in ("user_memory", "goal_memory", "retrieved_memory")
                for m in (context or {}).get(key, []) if m.get("id")}
    for i, item in enumerate(output.get("items", [])):
        if item.get("scope") == "goal" and goal_id and item.get("goal_id") != goal_id:
            c.error("MEM_WRONG_GOAL", f"goal-scoped item bound to {item.get('goal_id')!r}, current goal is {goal_id!r}", f"items/{i}")
        if item.get("scope") == "user" and (item.get("category") == "health" or item.get("sensitive")):
            c.error("MEM_SENSITIVE_USER_SCOPE", "sensitive/health information must not be stored at user level (it would reach every goal)", f"items/{i}")
        content = item.get("content", "").lower()
        if item.get("sensitive") and any(h in content for h in _THIRD_PARTY_HINTS):
            c.error("MEM_THIRD_PARTY_STORED", "sensitive information about another person stored", f"items/{i}")
    for i, u in enumerate(output.get("updates", [])):
        if u.get("memory_id") not in existing:
            c.error("MEM_UNKNOWN_ID", f"update references unknown memory {u.get('memory_id')!r}", f"updates/{i}")
    if c.since("0.1.1"):
        for code, i, message in PROV.memory_source_issues(output.get("items"), context):
            c.error(code, message, f"items/{i}")


# --------------------------------------------------------------------------- progress

def lint_progress_update(c, output, context, annotations):
    verified = _verified_refs(context)
    progress = (context or {}).get("progress") or {}
    journey = (context or {}).get("journey") or {}
    known_ach = {a["id"] for a in journey.get("achievements", [])}
    unlocked = set(progress.get("unlocked_achievement_ids", []))
    for i, a in enumerate(output.get("achievements_unlocked", [])):
        bad = [r for r in a.get("evidence_refs", []) if r not in verified]
        if bad:
            c.error("PU_UNVERIFIED_EVIDENCE", f"achievement backed by unverified {bad}", f"achievements_unlocked/{i}")
        if known_ach and a.get("achievement_id") not in known_ach:
            c.error("PU_UNKNOWN_ACHIEVEMENT", f"{a.get('achievement_id')!r} not defined for this goal", f"achievements_unlocked/{i}")
        if a.get("achievement_id") in unlocked:
            c.error("PU_DUPLICATE_ACHIEVEMENT", f"{a.get('achievement_id')!r} already unlocked", f"achievements_unlocked/{i}")
        if T.mentions_app_activity(a.get("reason", "")):
            c.error("PU_ACTIVITY_BASED", "achievement justified by app activity", f"achievements_unlocked/{i}")
    lvl = output.get("level") or {}
    prev = progress.get("current_level_index")
    if prev is not None and lvl.get("changed") != (lvl.get("current_index") != prev):
        c.error("PU_LEVEL_INCONSISTENT", f"level.changed={lvl.get('changed')} but index {prev} -> {lvl.get('current_index')}")
    if lvl.get("changed"):
        based = set(lvl.get("based_on", []))
        if not based or not based <= verified:
            c.error("PU_LEVEL_UNSUPPORTED", "level change must be based on verified nodes/milestones")
    if T.mentions_app_activity(lvl.get("reason", "")) and lvl.get("changed"):
        c.error("PU_ACTIVITY_BASED", "level change justified by app activity")
    gp = output.get("goal_progress") or {}
    if gp.get("percent", 0) > 0 and not verified:
        c.error("PU_PROGRESS_WITHOUT_VERIFICATION", "goal progress > 0 without any verified progress")
    for m in gp.get("verified_milestones", []):
        if m not in verified:
            c.error("PU_UNVERIFIED_EVIDENCE", f"milestone {m} reported as verified but it is not")


# --------------------------------------------------------------------------- v0.1.1: deadlines & workload (POL-C)

_AUTONOMY = {"node": "auto", "milestone": "adapt_with_summary", "goal": "confirm_required"}
_OVERBOOK_TOLERANCE = 1.1   # plans may use up to 110 % of the nominal capacity before they count as infeasible


def _weekly_pace(context, output=None):
    """The pace a plan runs at: explicit workload > new steady pace > current budget > goal > journey pacing."""
    output = output or {}
    ctx = context or {}
    for v in ((output.get("workload") or {}).get("weekly_hours"), output.get("new_weekly_hours_planned"),
              (ctx.get("time_budget") or {}).get("hours_per_week"),
              ((ctx.get("goal") or {}).get("available_time") or {}).get("hours_per_week"),
              ((ctx.get("journey") or {}).get("pacing") or {}).get("weekly_hours_planned")):
        if isinstance(v, (int, float)) and v > 0:
            return float(v)
    return None


def _need_vs_capacity(nodes, mdates, target, target_id, until, today, weekly, phases=None):
    """(hours needed, hours available) for the work due by a target, or None if too few estimates."""
    scope = W.in_horizon(nodes, mdates, target, target_id)
    total, missing = W.total_minutes(scope)
    if not scope or len(missing) > 0.2 * len(scope) or not (today and until and weekly):
        return None
    return total / 60, W.capacity_hours(today, until, weekly, phases)


def _summary_text(output):
    ds = output.get("decision_summary") or {}
    return " ".join(str(ds.get(k, "")) for k in ("what_changed", "why", "impact"))


def _lint_route_deadlines(c, output, context):
    confirm = output.get("requires_user_confirmation")
    today = _d((context or {}).get("today"))
    journey = (context or {}).get("journey") or {}
    ms_titles = {m["id"]: m.get("title", "") for m in journey.get("milestones", [])}
    declared = set()
    for i, d in enumerate(output.get("modified_deadlines", [])):
        path = f"modified_deadlines/{i}"
        target, autonomy, state = d.get("target"), d.get("autonomy"), d.get("state")
        declared.add((target, d.get("target_id")))
        if not autonomy or not state:
            c.error("RA_DEADLINE_AUTONOMY_MISSING", "every deadline change declares autonomy and state (POL-C)", path)
            continue
        if _AUTONOMY.get(target) != autonomy:
            c.error("RA_DEADLINE_AUTONOMY_WRONG", f"a {target} deadline has autonomy {_AUTONOMY.get(target)!r}, not {autonomy!r} (POL-C)", path)
        if confirm and state != "proposed":
            c.error("RA_DEADLINE_STATE_INCONSISTENT", "the change waits for the user's confirmation, so nothing is applied yet: state must be 'proposed'", path)
        if not confirm and state != "applied":
            c.error("RA_DEADLINE_STATE_INCONSISTENT", "state 'proposed' needs requires_user_confirmation=true", path)
        if target == "milestone" and state == "applied":
            text = _summary_text(output)
            title = ms_titles.get(d.get("target_id"), "")
            named = d.get("target_id") in text or (title and title.lower() in text.lower()) or \
                CAL.mentions_date(text, _d(d.get("to")), today)
            if not named:
                c.error("RA_MILESTONE_NO_SUMMARY", f"milestone {d.get('target_id')} moves to {d.get('to')} but decision_summary "
                                                   "names neither the milestone nor the new date (POL-C)", path)
    for m in output.get("modified_nodes", []):
        for ch in m.get("changes", []):
            if ch.get("field") == "due_date" and ("node", m.get("node_id")) not in declared:
                c.error("RA_UNDECLARED_DEADLINE_CHANGE", f"due_date of {m.get('node_id')} changes in modified_nodes but is not declared "
                                                         "in modified_deadlines (POL-C)", f"modified_nodes/{m.get('node_id')}")
    for m in output.get("modified_milestones", []) or []:
        if m.get("change") == "moved" and ("milestone", m.get("milestone_id")) not in declared:
            c.error("RA_UNDECLARED_DEADLINE_CHANGE", f"milestone {m.get('milestone_id')} is moved but its date change is not in "
                                                     "modified_deadlines (POL-C)", "modified_milestones")
    # Every new milestone/goal date must leave room for the work due by it.
    if not today:
        return
    nodes, mdates, _ = W.apply_route_changes(context, output)
    weekly = _weekly_pace(context, output)
    phases = (output.get("workload") or {}).get("pace_phases")
    for i, d in enumerate(output.get("modified_deadlines", [])):
        to = _d(d.get("to"))
        if d.get("target") not in ("milestone", "goal") or not to:
            continue
        nc = _need_vs_capacity(nodes, mdates, d.get("target"), d.get("target_id"), to, today, weekly, phases)
        if nc and nc[0] > nc[1] * _OVERBOOK_TOLERANCE + 0.5:
            c.error("MILESTONE_DATE_INFEASIBLE", f"{d.get('target')} {d.get('target_id')} moved to {to}: {nc[0]:.1f} h of unfinished "
                                                 f"work due by then, {nc[1]:.1f} h available at {weekly:g} h/week", f"modified_deadlines/{i}")


def _lint_route_workload(c, output, context):
    today = _d((context or {}).get("today"))
    trig = (output.get("trigger") or {}).get("type")
    wl = output.get("workload")
    if trig in {"less_time", "more_time"} and not wl:
        c.error("RA_WORKLOAD_MISSING", "a time change needs the workload arithmetic (remaining work, pace, horizon) (POL-C)")
    if wl and today:
        _check_workload(c, wl, output, context, today)
    if today:
        vals = Q.derivable(context, output)
        texts = [("message_to_user", output.get("message_to_user", "")),
                 ("decision_summary", _summary_text(output))]
        ds = output.get("decision_summary") or {}
        texts += [(f"decision_summary/alternatives_considered/{i}", f"{a.get('option', '')}. {a.get('why_not', '')}")
                  for i, a in enumerate(ds.get("alternatives_considered") or [])]
        for path, text in texts:
            for value, unit, snippet in Q.underivable(text, vals):
                c.error("ARITH_TEXT_UNDERIVABLE", f"«{snippet}»: {value:g} {unit} does not follow from the plan "
                                                  "(remaining work, pace, dates) (POL-C)", path)


def _check_workload(c, wl, output, context, today):
    horizon = wl.get("horizon") or {}
    ht, hid, hdate = horizon.get("target"), horizon.get("target_id"), _d(horizon.get("date"))
    before_nodes = W.unfinished_nodes(context)
    before_dates = W.milestone_dates(context)
    after_nodes, after_dates, goal_after = W.apply_route_changes(context, output)
    goal_before = _d(((context or {}).get("goal") or {}).get("deadline"))
    valid = {goal_before, goal_after} if ht == "goal" else {before_dates.get(hid), after_dates.get(hid)}
    if hdate not in valid - {None}:
        c.error("ARITH_HORIZON_DATE", f"workload horizon {ht} {hid} dated {hdate}, but that target is due "
                                      f"{', '.join(sorted(str(v) for v in valid if v)) or 'on no known date'}", "workload/horizon")
    before, miss_b = W.total_minutes(W.in_horizon(before_nodes, before_dates, ht, hid))
    after, miss_a = W.total_minutes(W.in_horizon(after_nodes, after_dates, ht, hid))
    if wl.get("remaining_minutes_before") != before:
        c.error("ARITH_REMAINING_BEFORE", f"remaining_minutes_before={wl.get('remaining_minutes_before')} but the unfinished work "
                                          f"due by the horizon adds up to {before} min", "workload")
    if wl.get("remaining_minutes_after") != after:
        c.error("ARITH_REMAINING_AFTER", f"remaining_minutes_after={wl.get('remaining_minutes_after')} but after this change the "
                                         f"unfinished work due by the horizon adds up to {after} min", "workload")
    missing, listed = set(miss_b) | set(miss_a), set(wl.get("unestimated_node_ids") or [])
    if missing != listed:
        c.error("ARITH_UNESTIMATED", f"unestimated nodes {sorted(missing)} but unestimated_node_ids lists {sorted(listed)}", "workload")
    weekly = wl.get("weekly_hours")
    new_hours = output.get("new_weekly_hours_planned")
    if new_hours is not None and weekly != new_hours:
        c.error("ARITH_PACE", f"workload.weekly_hours={weekly} but new_weekly_hours_planned={new_hours}", "workload")
    budget = ((context or {}).get("time_budget") or {}).get("hours_per_week")
    if budget is not None and weekly and weekly > budget * 1.1:
        c.error("ARITH_PACE", f"workload runs at {weekly} h/week but the user has {budget} h/week", "workload")
    if not weekly or not hdate:
        return
    needed = W.weeks_needed(today, after / 60, weekly, wl.get("pace_phases"))
    available = (hdate - today).days / 7
    if needed is None:
        return
    if not W.close(wl.get("weeks_needed"), needed):
        c.error("ARITH_WEEKS_NEEDED", f"weeks_needed={wl.get('weeks_needed')} but {after} min at this pace takes {needed:.1f} weeks", "workload")
    if not W.close(wl.get("weeks_available"), available, rel=0.03, abs_=0.3):
        c.error("ARITH_WEEKS_AVAILABLE", f"weeks_available={wl.get('weeks_available')} but {today} -> {hdate} is {available:.1f} weeks", "workload")
    fits = needed <= available
    if wl.get("fits") != fits and abs(needed - available) > 0.5:
        c.error("ARITH_FITS", f"fits={wl.get('fits')} but {needed:.1f} weeks are needed and {available:.1f} are available", "workload")
    if not fits and abs(needed - available) > 0.5 and not output.get("requires_user_confirmation"):
        c.error("RA_UNFIT_NO_DECISION", f"the remaining work needs {needed:.1f} weeks but only {available:.1f} remain until {hdate}: "
                                        "the user has to choose (move the date, cut scope or add time) (POL-C)")


def _lint_navigator_deadlines(c, output, context):
    today = _d((context or {}).get("today"))
    confirm = output.get("requires_user_confirmation")
    nodes, mdates = W.unfinished_nodes(context), W.milestone_dates(context)
    weekly = _weekly_pace(context)
    for i, ch in enumerate(output.get("proposed_changes", [])):
        path = f"proposed_changes/{i}"
        if ch.get("action") == "reschedule" and not (ch.get("target_type") and ch.get("new_date")):
            c.error("NAV_RESCHEDULE_UNDECLARED", "a reschedule declares target_type and new_date (POL-C)", path)
        if ch.get("target_type") == "goal" and not confirm:
            c.error("NAV_GOAL_DEADLINE_NO_CONFIRM", "the goal deadline changes only after the user confirms (POL-C)", path)
        new = _d(ch.get("new_date"))
        if ch.get("target_type") in ("milestone", "goal") and new and today:
            dates = dict(mdates)
            if ch["target_type"] == "milestone":
                dates[ch.get("target_id")] = new
            nc = _need_vs_capacity(nodes, dates, ch["target_type"], ch.get("target_id"), new, today, weekly)
            if nc and nc[0] > nc[1] * _OVERBOOK_TOLERANCE + 0.5:
                c.error("MILESTONE_DATE_INFEASIBLE", f"{ch['target_type']} {ch.get('target_id')} moved to {new}: {nc[0]:.1f} h of "
                                                     f"unfinished work due by then, {nc[1]:.1f} h available at {weekly:g} h/week", path)


def _lint_journey_capacity(c, journey, goal, context):
    today = _d((context or {}).get("today"))
    weekly = ((journey.get("pacing") or {}).get("weekly_hours_planned")
              or ((goal or {}).get("available_time") or {}).get("hours_per_week"))
    if not (today and weekly):
        return
    nodes = {n["id"]: n for n in journey.get("nodes", []) if n.get("status") not in W.INACTIVE_STATUSES}
    mdates = {m["id"]: _d(m.get("target_date")) for m in journey.get("milestones", [])}
    for mid, md in sorted(mdates.items(), key=lambda kv: (kv[1] or date.max, kv[0])):
        if not md:
            continue
        nc = _need_vs_capacity(nodes, mdates, "milestone", mid, md, today, weekly)
        if nc and nc[0] > nc[1] * _OVERBOOK_TOLERANCE + 0.5:
            c.error("J_MILESTONE_OVERBOOKED", f"milestone {mid} ({md}): {nc[0]:.1f} h of work due by then, {nc[1]:.1f} h available "
                                              f"at {weekly:g} h/week (POL-C)", "journey/milestones")


def _lint_task_capacity(c, output, context):
    today = _d((context or {}).get("today"))
    weekly = _weekly_pace(context)
    journey = (context or {}).get("journey") or {}
    target = output.get("for_node_id") or (context or {}).get("target_node_id")
    node = next((n for n in journey.get("nodes", []) if n.get("id") == target), {})
    mdates = W.milestone_dates(context)
    until = mdates.get(node.get("milestone_id")) or mdates.get(target) or _d(((context or {}).get("goal") or {}).get("deadline"))
    if not (today and weekly and until):
        return
    total_h = sum(t.get("estimated_duration_minutes") or 0 for t in output.get("tasks", [])) / 60
    cap = W.capacity_hours(today, until, weekly)
    if total_h > cap * _OVERBOOK_TOLERANCE + 0.5:
        c.error("T_OVER_CAPACITY", f"the tasks need {total_h:.1f} h but {weekly:g} h/week until {until} gives {cap:.1f} h (POL-C)", "tasks")


def lint_input(context, version=None):
    """Request-side checks (v0.1.1+): what the product could not have sent, and wording the model
    would learn from. Reported separately from output lint; a model is never scored on its input."""
    c = _Collector(version)
    if not c.since("0.1.1") or not isinstance(context, dict):
        return c.issues
    items = [(f"input/evidence/{i}", e) for i, e in enumerate(context.get("evidence") or [])]
    for h, att in enumerate(context.get("verification_history") or []):
        items += [(f"input/verification_history/{h}/evidence/{i}", e) for i, e in enumerate(att.get("evidence") or [])]
    for path, e in items:
        un = POL.unavailable_evidence(e)
        if un:
            c.error("EVIDENCE_SOURCE_UNAVAILABLE", f"evidence {e.get('id')!r} ({e.get('type')}) needs {un[0]}, which is {un[1]} (POL-A)", path)
    vp = (context.get("task") or {}).get("verification_protocol")
    if vp:
        lint_protocol(c, vp, "input/task/verification_protocol")
    for n in (context.get("journey") or {}).get("nodes") or []:
        vp = (n.get("task") or {}).get("verification_protocol")
        if vp and n.get("status") not in DONE_STATUSES:
            lint_protocol(c, vp, f"input/journey/nodes/{n.get('id')}/task/verification_protocol")
    for key in ("user_memory", "goal_memory", "retrieved_memory"):
        for i, m in enumerate(context.get(key) or []):
            text = m.get("content") or ""
            if T.cyrillic_ratio(text) >= 0.5:
                hit = RU.memory_gendered(text)
                if hit:
                    c.error("RU_GENDERED_MEMORY", f"stored memory describes the user with a gendered form «{hit.group(0)}» (POL-D)",
                            f"input/{key}/{i}")
    today = _d(context.get("today"))
    if today:
        texts = [(f"input/conversation/{i}", m.get("content", "")) for i, m in enumerate(context.get("conversation") or [])
                 if m.get("role") == "assistant"]
        texts += [(f"input/decision_log/{i}", d.get("summary", "")) for i, d in enumerate(context.get("decision_log") or [])]
        for path, text in texts:
            for mm in CAL.weekday_mismatches(text, today):
                c.error("DATE_WEEKDAY_MISMATCH", mm.message(), path)
    return c.issues


# --------------------------------------------------------------------------- dispatch

_RULES = {
    "goal_clarification": lint_goal_clarification,
    "feasibility_assessment": lint_feasibility,
    "journey_generation": lint_journey_generation,
    "task_generation": lint_task_generation,
    "verification_protocol_design": lint_verification_protocol_design,
    "verification_result": lint_verification_result,
    "route_adaptation": lint_route_adaptation,
    "daily_plan": lint_daily_plan,
    "navigator_response": lint_navigator_response,
    "goal_change": lint_goal_change,
    "web_research_decision": lint_web_research_decision,
    "safety_classification": lint_safety_classification,
    "memory_extraction": lint_memory_extraction,
    "progress_update": lint_progress_update,
}


def lint_output(operation, output, context=None, annotations=None, language=None, safety_category=None, version=None):
    """Lint one output. `language` is the user's language; `safety_category` the expected category;
    `version` the output contract (schema_version) whose rules apply (default: current)."""
    c = _Collector(version)
    if not isinstance(output, dict):
        c.error("NOT_AN_OBJECT", "output is not a JSON object")
        return c.issues
    _lint_common(c, operation, output, context or {}, annotations or {}, language)
    rule = _RULES.get(operation)
    if rule:
        rule(c, output, context or {}, annotations or {})
    if operation == "safety_classification" and safety_category and output.get("category") != safety_category:
        c.error("S_CATEGORY_MISMATCH", f"category {output.get('category')!r}, expected {safety_category!r}")
    return c.issues
