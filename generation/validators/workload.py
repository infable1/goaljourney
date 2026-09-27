"""Workload arithmetic (POL-C): remaining hours, pace and deadline feasibility, recomputed from the
journey instead of trusted.

Terms
  unfinished node   a journey node whose status is not completed/verified/skipped/removed and that is
                    not listed as completed/verified in `progress`
  remaining minutes sum of estimated_duration_minutes over unfinished nodes (optionally only those
                    scheduled up to a milestone horizon)
  capacity          hours available between two dates at the weekly pace, where temporary
                    `pace_phases` (inclusive date ranges) override the steady pace
"""
from datetime import date, timedelta

DONE_STATUSES = {"completed", "verified"}
INACTIVE_STATUSES = {"completed", "verified", "removed", "skipped"}


def _d(s):
    try:
        return date.fromisoformat(s) if s else None
    except (TypeError, ValueError):
        return None


def done_ids(context):
    journey = (context or {}).get("journey") or {}
    done = {n["id"] for n in journey.get("nodes", []) if n.get("status") in DONE_STATUSES}
    progress = (context or {}).get("progress") or {}
    return done | set(progress.get("completed_node_ids", [])) | set(progress.get("verified_node_ids", []))


def unfinished_nodes(context):
    """{id: node} of unfinished nodes in the input journey."""
    journey = (context or {}).get("journey") or {}
    done = done_ids(context)
    return {n["id"]: n for n in journey.get("nodes", [])
            if n.get("status") not in INACTIVE_STATUSES and n["id"] not in done}


def milestone_dates(context):
    journey = (context or {}).get("journey") or {}
    return {m["id"]: _d(m.get("target_date")) for m in journey.get("milestones", [])}


def apply_route_changes(context, output):
    """Unfinished nodes and milestone dates after a route_adaptation output is applied.

    Returns (nodes: {id: node-dict copy}, milestone_dates: {id: date}, goal_deadline: date)."""
    nodes = {nid: dict(n) for nid, n in unfinished_nodes(context).items()}
    for r in output.get("removed_nodes") or []:
        nodes.pop(r.get("node_id"), None)
    for m in output.get("modified_nodes") or []:
        n = nodes.get(m.get("node_id"))
        if n is None:
            continue
        for ch in m.get("changes") or []:
            n[ch.get("field")] = ch.get("to")
        if n.get("status") in INACTIVE_STATUSES:
            nodes.pop(m.get("node_id"))
    for n in output.get("added_nodes") or []:
        if n.get("status") not in INACTIVE_STATUSES:
            nodes[n.get("id")] = dict(n)
    mdates = milestone_dates(context)
    goal_deadline = _d(((context or {}).get("goal") or {}).get("deadline"))
    for d in output.get("modified_deadlines") or []:
        if d.get("target") == "milestone":
            mdates[d.get("target_id")] = _d(d.get("to"))
        elif d.get("target") == "goal":
            goal_deadline = _d(d.get("to"))
        elif d.get("target") == "node" and d.get("target_id") in nodes:
            nodes[d["target_id"]]["due_date"] = d.get("to")
    return nodes, mdates, goal_deadline


def in_horizon(nodes, mdates, horizon_target, horizon_id):
    """Nodes that must be finished by the horizon: for the goal, all; for a milestone, the nodes of
    that milestone and of every milestone dated no later than it."""
    if horizon_target != "milestone":
        return dict(nodes)
    limit = mdates.get(horizon_id)
    keep = {}
    for nid, n in nodes.items():
        mid = n.get("milestone_id")
        md = mdates.get(mid)
        if mid == horizon_id or (md and limit and md <= limit):
            keep[nid] = n
    return keep


def total_minutes(nodes):
    """(sum of estimates, [ids without an estimate])."""
    total, missing = 0, []
    for nid, n in sorted(nodes.items()):
        dur = n.get("estimated_duration_minutes")
        if dur is None and isinstance(n.get("task"), dict):
            dur = n["task"].get("estimated_duration_minutes")
        if dur:
            total += int(dur)
        else:
            missing.append(nid)
    return total, missing


def _phase_rate(day, weekly_hours, phases):
    for p in phases or []:
        a, b = _d(p.get("from")), _d(p.get("to"))
        if a and b and a <= day <= b:
            return float(p.get("weekly_hours", 0))
    return float(weekly_hours)


def capacity_hours(start, end, weekly_hours, phases=None):
    """Hours available from `start` (exclusive) to `end` (inclusive) at the given pace."""
    if not (start and end) or end <= start:
        return 0.0
    days = (end - start).days
    if not phases:
        return weekly_hours * days / 7
    return sum(_phase_rate(start + timedelta(days=i), weekly_hours, phases) / 7 for i in range(1, days + 1))


def finish_date(start, hours_needed, weekly_hours, phases=None, max_days=3660):
    """First date by which `hours_needed` fit at the pace; None if never within max_days."""
    if hours_needed <= 0:
        return start
    acc = 0.0
    for i in range(1, max_days + 1):
        day = start + timedelta(days=i)
        acc += _phase_rate(day, weekly_hours, phases) / 7
        if acc + 1e-9 >= hours_needed:
            return day
    return None


def weeks_needed(start, hours_needed, weekly_hours, phases=None):
    end = finish_date(start, hours_needed, weekly_hours, phases)
    return None if end is None else (end - start).days / 7


def close(a, b, rel=0.05, abs_=0.6):
    return a is not None and b is not None and abs(a - b) <= max(abs_, rel * abs(b))
