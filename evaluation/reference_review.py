"""Human review of evaluation reference outputs (D-028), stored inside the evaluation cases.

A case's `reference_review` block holds append-only review sessions. Each session is one sitting of one
registered human reviewer and lists decisions on reference outputs (the case's own, or one per step), each
bound to the content hash of the reference output it judged. `reference_status` is derived from the block:
* `draft_unreviewed` while a reference output has no decision on its current content hash (unreviewed,
  partly reviewed, or reviewed before the reference changed);
* `human_reviewed` when every reference output has a human decision on its current content hash.
The case's risk tier plays no part (D-030): the owner's review completes an expert-tier case too. The D-029
status `awaiting_expert` is no longer derived; envelopes stamped with schema 0.1.3 still validate against the
archived 0.1.3 schemas.

`gj eval build-cases` carries the block over when it re-renders the cases, so regeneration never erases a
human decision; `gj eval review-reference` records a new session. The AI copilot never records a decision.
Reference reviews never make an evaluation case a training example (D-017).
"""
from datetime import datetime

from gjcore.io import canonical_json, load_yaml, sha256_text
from gjcore.paths import repo_path

INTRODUCED_IN = "0.1.3"   # schema version whose eval_case.json defines `reference_review`
DRAFT, REVIEWED = "draft_unreviewed", "human_reviewed"
UNIT_KEYS = {"step_id", "action", "overall", "issues", "notes"}


class ReferenceReviewError(ValueError):
    """A reference review cannot be recorded; the message says why."""


def reference_hash(reference_output) -> str:
    """sha256 of the canonical JSON of one reference output."""
    return sha256_text(canonical_json(reference_output))


def reference_units(case) -> dict:
    """{step_id (None for an atomic case): reference_output} for every reference output, in case order."""
    if case.get("steps"):
        return {s["step_id"]: s["reference_output"] for s in case["steps"] if "reference_output" in s}
    return {None: case["reference_output"]} if "reference_output" in case else {}


def _sessions(case):
    return (case.get("reference_review") or {}).get("sessions") or []


def decided_units(case) -> dict:
    """{step_id: unit decision} — the latest decision on each reference output's CURRENT content hash."""
    current = {k: reference_hash(v) for k, v in reference_units(case).items()}
    out = {}
    for s in sorted(_sessions(case), key=lambda s: s["timestamp"]):   # stable: equal timestamps keep file order
        for u in s["units"]:
            key = u.get("step_id")
            if key in current and u["content_hash"] == current[key]:
                out[key] = {**u, "reviewer_id": s["reviewer_id"], "timestamp": s["timestamp"]}
    return out


def derive_status(case) -> str:
    """`human_reviewed` when every reference output has a human decision on its current content, else
    `draft_unreviewed`. No expert condition (D-030)."""
    refs = reference_units(case)
    decided = decided_units(case)
    if not refs or not all(k in decided for k in refs):
        return DRAFT
    return REVIEWED


def summary(case) -> dict:
    """Reference outputs, decided ones, stale ones (latest decision made on content that has since changed) and
    the derived status."""
    refs = reference_units(case)
    decided = decided_units(case)
    latest = {}
    for s in sorted(_sessions(case), key=lambda s: s["timestamp"]):
        for u in s["units"]:
            latest[u.get("step_id")] = u["content_hash"]
    stale = [k for k, h in latest.items() if k in refs and k not in decided]
    return {"units": len(refs), "decided": sum(1 for k in refs if k in decided), "stale": stale,
            "status": derive_status(case)}


def attach(case, review):
    """The case with `review` as its reference_review block (right after reference_status) and the derived
    reference_status. `review=None` removes the block. The input dict is not modified."""
    out = {}
    for k, v in case.items():
        if k == "reference_review":
            continue
        out[k] = v
        if k == "reference_status" and review:
            out["reference_review"] = review
    if review and "reference_review" not in out:
        out["reference_review"] = review
    if "reference_status" in out or review:
        out["reference_status"] = derive_status(out)
    return out


def _parse_ts(ts):
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def as_of(case, cutoff):
    """The case as it stood at `cutoff` (an aware datetime): sessions recorded later are dropped and the status is
    re-derived. A release snapshots reference reviews at build time, so rebuilding it uses this view."""
    review = case.get("reference_review")
    if not review:
        return case
    kept = [s for s in review["sessions"] if _parse_ts(s["timestamp"]) <= cutoff]
    return attach(case, {**review, "sessions": kept} if kept else None)


def semantic_errors(case, registry) -> list:
    """Problems the schema cannot express: unknown units, unregistered reviewers, out-of-order sessions, and a
    stored reference_status that is not the derived one."""
    errors = []
    refs = reference_units(case)
    multi = bool(case.get("steps"))
    last = None
    for i, s in enumerate(_sessions(case)):
        tag = f"session {i + 1} ({s['reviewer_id']}, {s['timestamp']})"
        r = registry.get(s["reviewer_id"])
        if r is None or not r["human"]:
            errors.append(f"{tag}: {s['reviewer_id']!r} is not a registered human reviewer (review/reviewers.yaml)")
        if last is not None and _parse_ts(s["timestamp"]) < last:
            errors.append(f"{tag}: sessions are append-only and must be in timestamp order")
        last = _parse_ts(s["timestamp"])
        seen = set()
        for u in s["units"]:
            key = u.get("step_id")
            if multi and key is None:
                errors.append(f"{tag}: a {case.get('case_type')} case needs a step_id on every unit")
            elif not multi and key is not None:
                errors.append(f"{tag}: an atomic case's unit has no step_id (got {key!r})")
            elif key not in refs:
                errors.append(f"{tag}: {key!r} has no reference output in this case")
            if key in seen:
                errors.append(f"{tag}: {key or 'the reference'} is decided twice in one session")
            seen.add(key)
    if "reference_status" in case and case["reference_status"] != derive_status(case):
        errors.append(f"reference_status is {case['reference_status']!r} but the recorded reviews make it "
                      f"{derive_status(case)!r} (it is derived; run `gj eval build-cases`)")
    return errors


# ---------------------------------------------------------------------------------------------
# Recording (`gj eval review-reference`)

def _unit_decisions(case, raw_units):
    """Validate the decision file's units against the case and bind each one to its reference output's hash."""
    refs = reference_units(case)
    multi = bool(case.get("steps"))
    if not isinstance(raw_units, list) or not raw_units:
        raise ReferenceReviewError("the decision file needs a non-empty `units` list")
    units, seen = [], set()
    for raw in raw_units:
        if not isinstance(raw, dict):
            raise ReferenceReviewError(f"each unit is a mapping, got {raw!r}")
        extra = set(raw) - UNIT_KEYS
        if extra:
            raise ReferenceReviewError(f"unknown unit field(s) {sorted(extra)}; allowed: {sorted(UNIT_KEYS)} "
                                       f"(the content hash is computed, never given)")
        key = raw.get("step_id")
        if multi and key is None:
            raise ReferenceReviewError(f"{case['id']} is {case['case_type']}: every unit needs a step_id")
        if not multi and key is not None:
            raise ReferenceReviewError(f"{case['id']} is atomic: its unit has no step_id")
        if key not in refs:
            raise ReferenceReviewError(f"{case['id']}: {key!r} has no reference output")
        if key in seen:
            raise ReferenceReviewError(f"{case['id']}: {key or 'the reference'} is listed twice")
        seen.add(key)
        for f in ("action", "overall"):
            if not raw.get(f):
                raise ReferenceReviewError(f"{case['id']} {key or 'unit'}: `{f}` is required")
        unit = {"step_id": key} if multi else {}
        unit.update({"content_hash": reference_hash(refs[key]), "action": raw["action"], "overall": raw["overall"],
                     "issues": list(raw.get("issues") or []), "notes": (raw.get("notes") or "").strip()})
        units.append(unit)
    order = list(refs)
    return sorted(units, key=lambda u: order.index(u.get("step_id")))


def record(case_id, reviewer_id, raw_units, independent_rating, *, replace=False, timestamp=None):
    """Record one review session by a registered human reviewer on a case's reference outputs. The case file is
    rewritten by the builder, so the generated YAML stays the builder's output. Returns the updated case."""
    from gjcore import schemas
    from generation.pipelines.review_store import (load_registry, now_utc, required_languages, review_config,
                                                   review_mode)
    from evaluation.builders import build

    if not isinstance(independent_rating, bool):
        raise ReferenceReviewError("independent_rating must be given (yes or no)")
    mode = review_mode()
    if mode != "solo_owner":
        raise ReferenceReviewError(f"governance mode is {mode!r}: reference review is defined for solo_owner only "
                                   "(D-028); one review would not provide reviewer agreement")
    reviewer = load_registry().get(reviewer_id)
    if reviewer is None:
        raise ReferenceReviewError(f"unknown reviewer {reviewer_id!r} — add yourself to review/reviewers.yaml first")
    if not reviewer["human"]:
        raise ReferenceReviewError(f"reviewer {reviewer_id!r} is not marked human: true — automated agents cannot "
                                   "record decisions")
    if not reviewer["active"]:
        raise ReferenceReviewError(f"reviewer {reviewer_id!r} is inactive")
    case = next((c for c, _ in build.committed_cases() if c["id"] == case_id), None)
    if case is None:
        raise ReferenceReviewError(f"no evaluation case {case_id!r} in evaluation/cases/v{build.VERSION}")
    langs = required_languages(case)
    if review_config()["approval"]["require_language_match"] and not set(langs) <= set(reviewer["languages"]):
        raise ReferenceReviewError(f"{case_id} needs a reviewer who reads {langs}; {reviewer_id} lists "
                                   f"{reviewer['languages']}")
    units = _unit_decisions(case, raw_units)
    # only a reviewer's own decision on the current content counts as a redecision; the session records the
    # reviewer's registry roles and domains as an audit snapshot, which since D-030 has no effect on the status
    current = {k: reference_hash(v) for k, v in reference_units(case).items()}
    mine = {u.get("step_id") for s in _sessions(case) if s["reviewer_id"] == reviewer_id for u in s["units"]
            if current.get(u.get("step_id")) == u["content_hash"]}
    redecided = [u.get("step_id") or "the reference" for u in units if u.get("step_id") in mine]
    if redecided and not replace:
        raise ReferenceReviewError(f"{case_id}: {redecided} already have {reviewer_id}'s decision on their current "
                                   "content; pass --replace to record a newer one (the earlier session stays in the "
                                   "history)")
    session = {"reviewer_id": reviewer_id, "reviewer_roles": sorted(reviewer["roles"]),
               "reviewer_expert_domains": sorted(reviewer["expert_domains"]), "timestamp": timestamp or now_utc(),
               "governance_mode": mode, "independent_rating": independent_rating, "units": units}
    review = case.get("reference_review") or {}
    sessions = list(review.get("sessions") or [])
    if sessions and _parse_ts(session["timestamp"]) < _parse_ts(sessions[-1]["timestamp"]):
        raise ReferenceReviewError("the new session is older than the case's latest session (append-only)")
    review = {"metadata_schema_version": schemas.current_version(), "sessions": sessions + [session]}
    updated = attach(case, review)
    problems = schemas.validate("eval_case", updated, review["metadata_schema_version"])
    if problems:
        raise ReferenceReviewError("eval_case schema: " + "; ".join(problems))
    files = build.render()
    drift = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if drift:
        raise ReferenceReviewError(f"{len(drift)} generated file(s) differ from the builder output; run "
                                   "`gj eval build-cases --check` and resolve that first")
    reviews = build.existing_reviews()
    reviews[case_id] = review
    build.run(reviews=reviews)
    return updated


def load_decision_file(path):
    data = load_yaml(repo_path(path)) or {}
    if set(data) - {"units"}:
        raise ReferenceReviewError(f"{path}: only a `units` list is read (got {sorted(data)})")
    return data.get("units")
