"""Fact provenance (POL-E): `facts_used` entries must point at what they claim to come from.

source_type        must reference                                             checked
user_provided      the conversation, the goal, stored user/goal memory,       ref exists; numbers in the fact appear in
                   progress, time budget, events, the task, submitted          the referenced text; at least one content
                   evidence, a journey node/milestone                          word overlaps; the referenced item is not
                                                                               itself marked as inferred
model_inferred     anything (or nothing)                                       ref exists if given
externally_verified research results, or evidence the system fetched itself   ref exists and is one of those
unknown            nothing                                                     —

The overlap test is lexical (5-letter stems), so a fact must stay close to the wording of its source;
paraphrases that share no content word are reported and should cite the source more faithfully.
"""
import json
import re
from datetime import date

from . import calendar as CAL

_REF_RE = re.compile(r"^(?:(?P<arr>conversation|decision_log|events)\[(?P<idx>\d+)\]|"
                     r"(?P<obj>goal|progress|time_budget|task)\.(?P<field>[a-z_]+)|"
                     r"(?P<coll>user_memory|goal_memory|retrieved_memory|research|evidence|node|milestone):(?P<id>[A-Za-z0-9_.-]+))$")
_WORD = re.compile(r"[A-Za-zА-Яа-яЁё]{4,}")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_STOP = {"that", "this", "with", "from", "have", "будет", "which", "about", "their", "they", "your", "what", "when",
         "user", "пользователь", "пользователя", "только", "может", "очень", "sometimes", "every", "каждый", "каждую",
         "week", "weeks", "неделю", "недели", "hours", "часа", "часов"}
_USER_SOURCES = {"conversation", "decision_log", "events", "goal", "progress", "time_budget", "task",
                 "user_memory", "goal_memory", "retrieved_memory", "evidence", "node", "milestone"}
_THOUSANDS = re.compile(r"(?<=\d)[   ](?=\d{3}\b)")
_SCALE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(тысяч\w*|тыс\.?|k\b|thousand|млн|million)", re.IGNORECASE)


_WORD_NUMBERS = None


def _word_numbers(text):
    """Cardinal number words ("три", "three", "полтора") as values."""
    global _WORD_NUMBERS
    if _WORD_NUMBERS is None:
        from .quantities import _NUM_WORDS
        words = sorted((w for w in _NUM_WORDS if " " not in w), key=len, reverse=True)
        _WORD_NUMBERS = (re.compile(r"\b(" + "|".join(map(re.escape, words)) + r")\b", re.IGNORECASE), _NUM_WORDS)
    rx, table = _WORD_NUMBERS
    return {float(table[m.group(1).lower()]) for m in rx.finditer(text or "")}


def _numbers(text):
    text = _THOUSANDS.sub("", text or "")
    vals = _word_numbers(text)
    for m in _SCALE.finditer(text):
        mult = 1_000_000 if m.group(2).lower().startswith(("млн", "million")) else 1000
        vals.add(float(m.group(1).replace(",", ".")) * mult)
    vals |= {float(x.replace(",", ".")) for x in _NUMBER.findall(text)}
    return vals


_ISO = re.compile(r"\b20\d\d-\d\d-\d\d\b")


def _today(context):
    try:
        return date.fromisoformat((context or {}).get("today"))
    except (TypeError, ValueError):
        return None


def ungrounded_numbers(value, source, today):
    """Numbers (and ISO dates) in `value` that `source` does not support. A date the navigator
    normalised ("March 14" -> 2027-03-14, "до пятницы" -> 2026-10-02) counts as supported."""
    missing = set()
    for iso in _ISO.findall(value or ""):
        try:
            d = date.fromisoformat(iso)
        except ValueError:
            continue
        if iso not in (source or "") and not CAL.date_grounded(source, d, today):
            missing.add(iso)
    rest = _ISO.sub(" ", value or "")
    src_nums = _numbers(_ISO.sub(" ", source or "")) | {float(x) for iso in _ISO.findall(source or "") for x in iso.split("-")}
    missing |= {n for n in _numbers(rest) if n not in src_nums}
    return missing


def _stems(text):
    return {w.lower()[:5] for w in _WORD.findall(text or "") if w.lower() not in _STOP}


def resolve_ref(ref, context):
    """(kind, item_or_text) the ref points to, or (None, None) if it does not exist."""
    m = _REF_RE.match(ref or "")
    ctx = context or {}
    if not m:
        return None, None
    if m.group("arr"):
        arr = ctx.get(m.group("arr")) or []
        i = int(m.group("idx"))
        return (m.group("arr"), arr[i]) if i < len(arr) else (None, None)
    if m.group("obj"):
        obj = ctx.get(m.group("obj")) or {}
        field = m.group("field")
        return (m.group("obj"), obj[field]) if isinstance(obj, dict) and field in obj and obj[field] not in (None, "", []) else (None, None)
    coll, iid = m.group("coll"), m.group("id")
    if coll in ("node", "milestone"):
        items = ((ctx.get("journey") or {}).get("nodes" if coll == "node" else "milestones")) or []
    elif coll == "research":
        items = ctx.get("research_results") or []
    else:
        items = ctx.get(coll) or []
    for it in items:
        if isinstance(it, dict) and it.get("id") == iid:
            return coll, it
    return None, None


def _text_of(item):
    return item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)


def check_facts(facts, context):
    """Return [(code, index, message)] for facts_used entries (POL-E)."""
    issues = []
    for i, f in enumerate(facts or []):
        st, ref, value = f.get("source_type"), f.get("source_ref"), f.get("value", "")
        kind, item = resolve_ref(ref, context) if ref else (None, None)
        if ref and kind is None:
            issues.append(("FACT_BAD_REF", i, f"source_ref {ref!r} does not exist in the input"))
            continue
        if st == "externally_verified":
            fetched = kind == "evidence" and isinstance(item, dict) and item.get("description_source") == "system_fetch"
            if kind != "research" and not fetched:
                issues.append(("FACT_VERIFIED_WITHOUT_SOURCE", i,
                               "externally_verified facts must cite research:<id> or system-fetched evidence:<id>"))
        elif st == "user_provided":
            if not ref:
                issues.append(("FACT_NOT_GROUNDED", i, "user_provided fact without source_ref"))
                continue
            if kind not in _USER_SOURCES:
                issues.append(("FACT_NOT_GROUNDED", i, f"user_provided fact cites {kind}, which is not a user source"))
                continue
            if kind == "conversation" and isinstance(item, dict) and item.get("role") != "user":
                issues.append(("FACT_NOT_GROUNDED", i, f"{ref} is an assistant turn, not something the user said"))
                continue
            if isinstance(item, dict) and item.get("source") == "inferred":
                issues.append(("FACT_PROVENANCE_UPGRADED", i,
                               f"{ref} is stored as inferred; citing it as user_provided upgrades an inference into a user fact"))
                continue
            if isinstance(item, dict) and item.get("basis") in ("inferred_from_context", "default_until_confirmed"):
                issues.append(("FACT_PROVENANCE_UPGRADED", i, f"{ref} is an assumption, not a user statement"))
                continue
            src = _text_of(item.get("content") if isinstance(item, dict) and "content" in item else item)
            missing = ungrounded_numbers(value, src, _today(context))
            if missing:
                issues.append(("FACT_NOT_GROUNDED", i, f"number(s) {sorted(map(str, missing))} in the fact do not appear in {ref}"))
            elif _stems(value) and not (_stems(value) & _stems(src)):
                issues.append(("FACT_NOT_GROUNDED", i, f"fact shares no content word with {ref}"))
    return issues


def memory_source_issues(items, context):
    """memory_extraction: an item stored as user_stated must be grounded in what the user wrote."""
    user_text = " ".join(m.get("content", "") for m in (context or {}).get("conversation") or [] if m.get("role") == "user")
    out = []
    for i, it in enumerate(items or []):
        if it.get("source") != "user_stated":
            continue
        content = it.get("content", "")
        missing = ungrounded_numbers(content, user_text, _today(context))
        if missing:
            out.append(("MEM_SOURCE_NOT_GROUNDED", i, f"user_stated memory contains {sorted(map(str, missing))}, which the user did not write"))
        elif _stems(content) and not (_stems(content) & _stems(user_text)):
            out.append(("MEM_SOURCE_NOT_GROUNDED", i, "user_stated memory shares no content word with the user's messages"))
    return out
