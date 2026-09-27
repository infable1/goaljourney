"""Stated quantities (POL-C arithmetic): numbers of hours, weeks, months, days or minutes in
user-facing text must be derivable from the input and the plan.

This catches statements such as "about 140 hours of remaining work" when the unfinished tasks add up
to 115 hours. It is deliberately conservative: a quantity passes if it is close to *any* number the
input contains or the plan implies (remaining work before/after the change, weeks until any known
date, the pace, capacity until a date, buffers between them). A quantity introduced by a
"remaining" word ("осталось", "left", "of remaining work") must match the remaining work
specifically, and a "saving" ("экономия", "saves") must match the net change in remaining work.
Rates ("3 h/week") are paces, not quantities of work: they are left to the pace rules
(RA_OVER_TIME, ARITH_PACE), because weekly amounts built from frequencies ("3 times a week x 30
min") are not modelled. The check cannot
prove that the right number was used, only that the number is not invented.
"""
import json
import re
from datetime import date

from . import workload as W

_NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "a couple of": 2, "half an": 0.5,
    "один": 1, "одна": 1, "одну": 1, "одного": 1, "два": 2, "две": 2, "двух": 2, "три": 3, "трёх": 3, "трех": 3,
    "четыре": 4, "четырёх": 4, "четырех": 4, "пять": 5, "пяти": 5, "шесть": 6, "шести": 6, "семь": 7, "семи": 7,
    "восемь": 8, "восьми": 8, "девять": 9, "девяти": 9, "десять": 10, "десяти": 10, "одиннадцать": 11,
    "двенадцать": 12, "полтора": 1.5, "полторы": 1.5, "полутора": 1.5, "пару": 2, "пара": 2,
}
_UNIT = (r"(?P<unit>hours?|hrs?|h\b|weeks?|wks?|months?|days?|minutes?|mins?|"
         r"час(?:а|ов)?|ч\b|недел[ьяиюе]\w*|нед\b|месяц\w*|мес\b|дн(?:я|ей)|день|суток|минут\w*|мин\b)")
_APPROX = (r"(?P<approx>≈|~|about|around|roughly|approximately|nearly|almost|over|more than|less than|under|"
           r"около|примерно|почти|приблизительно|более|больше|меньше|свыше|порядка)?\s*")
_NUM = r"(?P<a>\d+(?:[.,]\d+)?)(?:\s*(?:–|-|—|to|до)\s*(?P<b>\d+(?:[.,]\d+)?))?"
_WORDS = "|".join(sorted((re.escape(w) for w in _NUM_WORDS), key=len, reverse=True))
_QTY_RE = re.compile(r"(?<![\w.,])" + _APPROX + r"(?:" + _NUM + r"|(?P<w>" + _WORDS + r"))\s*"
                     r"(?:extra\s+|more\s+|дополнительн\w+\s+|лишн\w+\s+)?" + _UNIT, re.IGNORECASE)
_THOUSANDS = re.compile(r"(?<=\d)[   ](?=\d{3}\b)")
_REMAINING_RE = re.compile(r"(remaining|left\b|to go\b|outstanding|остал\w*|оста[её]тся|оставш\w*|впереди)", re.IGNORECASE)
_RATE_RE = re.compile(r"^\s*(?:/\s*|per\s+|a\s+|в\s+|за\s+)(?:week|wk|неделю|нед)", re.IGNORECASE)

TOLERANCE_ABS = {"h": 0.5, "w": 0.6, "mo": 0.6, "d": 1.0, "min": 5.0}
_SAVING_RE = re.compile(r"(sav(e|es|ed|ing)|frees? up|экономи\w*|сэконом\w*|освобо\w*|выигрыш\w*)", re.IGNORECASE)


def _unit(u):
    u = u.lower()
    if u.startswith(("hour", "hr", "час")) or u in ("h", "ч"):
        return "h"
    if u.startswith(("week", "wk", "недел", "нед")):
        return "w"
    if u.startswith(("month", "месяц", "мес")):
        return "mo"
    if u.startswith(("day", "дн", "день", "сут")):
        return "d"
    return "min"


def _f(s):
    return float(s.replace(",", "."))


def extract(text, with_context=False):
    """Yield (value, unit, approx, snippet[, near]) for each quantity with a time unit. `near` is the
    clause text within 30 characters around the quantity, or None for a rate ("3 h/week")."""
    flat = _THOUSANDS.sub("", text or "")
    for m in _QTY_RE.finditer(flat):
        unit = _unit(m.group("unit"))
        approx = bool(m.group("approx"))
        snippet = flat[max(0, m.start() - 20):m.end() + 5].strip()
        rate = bool(_RATE_RE.match(flat[m.end():m.end() + 12]))
        left = re.split(r"[.!?;:,\n—]", flat[max(0, m.start() - 30):m.start()])[-1]
        right = re.split(r"[.!?;:,\n—]", flat[m.end():m.end() + 30])[0]
        extra = ((None if rate else left + " " + right),) if with_context else ()
        if m.group("w"):
            yield (_NUM_WORDS[m.group("w").lower()], unit, approx, snippet) + extra
            continue
        yield (_f(m.group("a")), unit, approx, snippet) + extra
        if m.group("b"):
            yield (_f(m.group("b")), unit, approx, snippet) + extra


_UNIT_KEYS = (("minutes", "min"), ("hours", "h"), ("weeks", "w"), ("days", "d"), ("months", "mo"))


def _base_quantities(obj, vals, key=""):
    """Quantities stated in the input/plan: numeric fields whose key names a unit
    (estimated_duration_minutes, hours_per_week, horizon_weeks, ...) and quantities with a unit
    inside strings. Unitless numbers (counts, indices, ids like n7) never justify a time claim."""
    if isinstance(obj, dict):
        field = obj.get("field") if isinstance(obj.get("field"), str) else None
        for k, v in obj.items():
            # a change record {field: estimated_duration_minutes, from: 900, to: 480} carries the unit in `field`
            _base_quantities(v, vals, field if field and k in ("from", "to") else k)
    elif isinstance(obj, list):
        for v in obj:
            _base_quantities(v, vals, key)
    elif isinstance(obj, bool):
        return
    elif isinstance(obj, (int, float)):
        for hint, unit in _UNIT_KEYS:
            if hint in key:
                vals[unit].add(float(obj))
    elif isinstance(obj, str):
        for value, unit, _, _ in extract(obj):
            vals[unit].add(value)


def _dates(obj):
    out = set()
    for s in re.findall(r"20\d\d-\d\d-\d\d", json.dumps(obj, ensure_ascii=False)):
        try:
            out.add(date.fromisoformat(s))
        except ValueError:
            pass
    return out


def derivable(context, output):
    """{unit: set(values)} of quantities the input and plan support; key 'remaining' holds the
    subset that describes remaining work (hours before/after the change and the weeks they need)."""
    vals = {"h": set(), "w": set(), "mo": set(), "d": set(), "min": set()}
    _base_quantities(context, vals)
    _base_quantities({k: v for k, v in output.items() if k not in ("message_to_user", "decision_summary", "user_options")}, vals)
    vals["h"] |= {m / 60 for m in vals["min"]}
    vals["min"] |= {h * 60 for h in vals["h"]}
    today = W._d((context or {}).get("today"))
    wl = output.get("workload") or {}
    weekly = wl.get("weekly_hours") or output.get("new_weekly_hours_planned") or \
        ((context or {}).get("time_budget") or {}).get("hours_per_week")
    phases = wl.get("pace_phases") or []
    all_dates = _dates(context) | _dates(output)
    weeks = set()
    if today:
        for d in all_dates:
            weeks.add(abs((d - today).days) / 7)
            vals["d"].add(abs((d - today).days))
    for p in phases:
        a, b = W._d(p.get("from")), W._d(p.get("to"))
        if a and b:
            weeks.add(((b - a).days + 1) / 7)
            vals["d"].add((b - a).days + 1)
            vals["h"].add(p.get("weekly_hours", 0) * ((b - a).days + 1) / 7)
    unfinished = W.unfinished_nodes(context)
    before_all, _ = W.total_minutes(unfinished)
    nodes_after, mdates, _ = W.apply_route_changes(context, output)
    after_all, _ = W.total_minutes(nodes_after)
    hours = {before_all / 60, after_all / 60, (before_all - after_all) / 60}
    horizon = wl.get("horizon") or {}
    if horizon:
        before_h, _ = W.total_minutes(W.in_horizon(unfinished, W.milestone_dates(context),
                                                   horizon.get("target"), horizon.get("target_id")))
        after_h, _ = W.total_minutes(W.in_horizon(nodes_after, mdates, horizon.get("target"), horizon.get("target_id")))
        hours |= {before_h / 60, after_h / 60, (before_h - after_h) / 60}
        net_h = abs(before_h - after_h) / 60
    # work due by each milestone, before and after the change
    for mid in set(W.milestone_dates(context)) | set(mdates):
        b, _ = W.total_minutes(W.in_horizon(unfinished, W.milestone_dates(context), "milestone", mid))
        a, _ = W.total_minutes(W.in_horizon(nodes_after, mdates, "milestone", mid))
        hours |= {b / 60, a / 60}
    remaining_h = {h for h in hours if h > 0}
    net = {abs(before_all - after_all) / 60}
    for r in output.get("removed_nodes") or []:
        n = unfinished.get(r.get("node_id")) or {}
        if n.get("estimated_duration_minutes"):
            hours.add(n["estimated_duration_minutes"] / 60)
    # per-task changes and the added work, e.g. "cutting the review saves 7.5 h, the sessions take 2 h"
    for m in output.get("modified_nodes") or []:
        for ch in m.get("changes") or []:
            if ch.get("field") == "estimated_duration_minutes" and isinstance(ch.get("from"), int) and isinstance(ch.get("to"), int):
                hours.add(abs(ch["from"] - ch["to"]) / 60)
    added, _ = W.total_minutes({n.get("id"): n for n in output.get("added_nodes") or []})
    if added:
        hours.add(added / 60)
    remaining_w = set()
    if weekly and today:
        for h in remaining_h:
            for ph in (phases, None):
                wn = W.weeks_needed(today, h, weekly, ph)
                if wn is not None:
                    remaining_w.add(wn)
        weeks |= remaining_w
        for d in all_dates:
            if d > today:
                hours.add(W.capacity_hours(today, d, weekly, phases))
                hours.add(W.capacity_hours(today, d, weekly))
    for key in ("weeks_needed", "weeks_available"):
        if isinstance(wl.get(key), (int, float)):
            weeks.add(float(wl[key]))
    wlist = sorted(weeks)
    weeks |= {a - b for a in wlist for b in wlist if a > b}
    vals["h"] |= hours
    vals["w"] |= weeks
    vals["mo"] |= {w / 4.345 for w in weeks}
    vals["d"] |= {w * 7 for w in weeks}
    vals["min"] |= {h * 60 for h in hours}
    if horizon:
        net.add(net_h)
    vals["saving"] = {"h": net, "min": {h * 60 for h in net}}
    vals["remaining"] = {"h": remaining_h, "w": remaining_w, "mo": {w / 4.345 for w in remaining_w},
                         "min": {h * 60 for h in remaining_h}, "d": {w * 7 for w in remaining_w}}
    return vals


def underivable(text, vals):
    """Quantities in `text` that match no derivable value: [(value, unit, snippet)]."""
    bad = []
    for value, unit, approx, snippet, near in extract(text, with_context=True):
        if near is None:
            continue  # a rate ("2.5 h/week") is a pace; paces are checked on the structured fields
        rel = 0.12 if approx else 0.07
        tol_abs = TOLERANCE_ABS[unit] if not (unit == "mo" and approx) else 1.0
        pool = vals.get(unit, set())
        remaining = (vals.get("remaining") or {}).get(unit)
        saving = (vals.get("saving") or {}).get(unit)
        if remaining and near and _REMAINING_RE.search(near):
            pool = remaining
        elif saving and near and _SAVING_RE.search(near):
            pool = saving
        if not any(abs(value - v) <= max(tol_abs, rel * abs(v)) for v in pool):
            bad.append((value, unit, snippet))
    return bad
