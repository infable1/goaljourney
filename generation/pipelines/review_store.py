"""Human review store (review log v0.3): append-only events, preserved snapshots, status resolution.

* Every decision is one line in data/reviewed/review_events.jsonl. Lines are never edited or removed:
  each event carries the hash of the previous one (`prev_event_hash`) and its own `event_hash`, so
  `gj review verify-log` detects edits, deletions and reordering.
* A decision applies to exact content (`content_hash`). The reviewed content is written once to
  data/reviewed/snapshots/<content_hash>.json, so every historical version stays readable after
  the example is edited.
* Status is derived, never stored on the example. There are four canonical statuses (Milestone 1.6);
  `detail` says why a pending example is pending:
    status          detail            meaning
    pending         not_reviewed      no qualifying decision on the current content
    pending         content_changed   decided on an earlier version; the current content has not been reviewed
    approved        decided           a qualified human approval of the current content, no open objection
    needs_revision  decided           a reviewer asked for a revision of the current content
    rejected        decided           a reviewer rejected the current content
  Only `approved` is training-eligible. With several reviewers, the latest decision of each counts and
  the most conservative wins (reject > revise > approve); an adjudicator's latest decision overrides everyone.
  With one reviewer this reduces to: their latest decision on the content hash is final.
  Log v0.2 (statuses `stale`, `approved_pending_expert`) was never written to; v0.3 events record the
  canonical status plus `new_status_detail`.
* Owner-only approval (D-030): an approval by a registered, active human reviewer who reads the example's
  languages approves it, whatever its risk tier. No domain-expert sign-off is required. The pre-D-030 detail
  `awaiting_expert` is no longer produced, and no recorded event ever carried it.
* Governance mode (configs/review.yaml `governance.mode`, D-026): `solo_owner` or `multi_reviewer`. The mode
  decides which release gates apply; it never changes status resolution, so historical events keep their meaning.
* Training eligibility (`training_eligibility`) separates "human-reviewed" (a decision exists on the current
  content) from "training-eligible" (status approved); every ineligible example gets a reason, which release
  manifests list.
"""
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from gjcore import schemas
from gjcore.config import load_config
from gjcore.io import append_jsonl, canonical_json, dump_json, load_json, load_yaml, read_jsonl, sha256_text
from gjcore.paths import rel, repo_path
from gjcore.records import HASHED_FIELDS, content_hash

LOG_VERSION = "0.3.0"
STATUSES = ("pending", "approved", "needs_revision", "rejected")
DETAILS = ("not_reviewed", "content_changed", "decided")
TRAINING_ELIGIBLE = {"approved"}
ACTIONS = ("approve", "revise", "reject")
# `domain_expert` stays a valid registry role so registries and the reviewer snapshots in recorded events remain
# readable; since D-030 it grants nothing extra and no decision needs it.
ROLES = ("dataset_reviewer", "domain_expert", "adjudicator")
RATINGS = ("good", "minor_issues", "major_issues", "unacceptable", "not_applicable")
OVERALL = ("excellent", "acceptable", "needs_revision", "incorrect")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,40}$")


class ReviewError(ValueError):
    """A review action was refused; the message says why."""


def review_config():
    return load_config("review")


REVIEW_MODES = ("solo_owner", "multi_reviewer")


def review_mode(cfg=None) -> str:
    """The governance mode in force. A config without `governance.mode` predates D-026: multi_reviewer."""
    mode = ((cfg if cfg is not None else review_config()).get("governance") or {}).get("mode", "multi_reviewer")
    if mode not in REVIEW_MODES:
        raise ReviewError(f"configs/review.yaml governance.mode must be one of {REVIEW_MODES} (got {mode!r})")
    return mode


def load_rubric(path=None):
    return load_yaml(repo_path(path or review_config()["rubric"]))


# ---------------------------------------------------------------------------------------------
# Reviewer registry

def load_registry(path=None) -> dict:
    path = repo_path(path or review_config()["paths"]["reviewers"])
    data = (load_yaml(path) if path.exists() else None) or {}
    reg, problems = {}, []
    for entry in data.get("reviewers") or []:
        rid = entry.get("id", "")
        if not _ID_RE.match(rid):
            problems.append(f"reviewer id {rid!r} must match {_ID_RE.pattern}")
            continue
        roles = entry.get("roles") or []
        bad = [r for r in roles if r not in ROLES]
        if bad or not roles:
            problems.append(f"{rid}: roles must be a non-empty subset of {list(ROLES)} (got {roles})")
            continue
        langs = entry.get("languages") or []
        if not langs:
            problems.append(f"{rid}: list the languages you review in (e.g. [en, ru])")
            continue
        reg[rid] = {"id": rid, "roles": roles, "languages": langs, "expert_domains": entry.get("expert_domains") or [],
                    "human": entry.get("human") is True, "active": entry.get("active", True) is not False}
    if problems:
        raise ReviewError("review/reviewers.yaml: " + "; ".join(problems))
    return reg


# ---------------------------------------------------------------------------------------------
# Tiers and required qualifications

def required_languages(record) -> list:
    langs = {record.get("language")}
    il = record.get("input_language")
    langs |= {"ru", "en"} if il == "mixed" else {il}
    return sorted(l for l in langs if l in {"ru", "en"})


def required_expert_domains(record, cfg=None) -> list:
    """The risk domains of an expert-tier example ([] = human tier).

    The tier is triggered by risk (a non-'allowed' safety category or an explicit risk tag); the record's
    domain and the safety output only decide WHICH domains. Since D-030 the tier is a risk label (review
    sampling, review focus, the review sheets and the `review_tier` / `required_expert_domains` fields every
    event records); no decision needs a domain expert's sign-off. The name is kept because those event fields,
    the frozen v0.1.0 review manifest and the schemas use it."""
    t = (cfg or review_config())["tiers"]["expert_review_required"]
    tags = set(record.get("tags") or [])
    if record.get("safety_category") not in t["safety_categories"] and not tags & set(t["tags"]):
        return []
    doms = {t["tags"][x] for x in tags if x in t["tags"]}
    if record.get("domain") in t["record_domains"]:
        doms.add(t["record_domains"][record["domain"]])
    if record.get("task_type") == "safety_classification":
        for d in (record.get("expected_output") or {}).get("domains") or []:
            if d in t["safety_output_domains"]:
                doms.add(t["safety_output_domains"][d])
    return sorted(doms or {t["fallback_expert_domain"]})


def review_tier(record, cfg=None) -> str:
    return "expert_review_required" if required_expert_domains(record, cfg) else "human_review_required"


# ---------------------------------------------------------------------------------------------
# Rubric applicability and decision checks

def _has_user_text(record):
    out = record.get("expected_output") or {}
    return bool(out.get("message_to_user") or out.get("questions") or out.get("decision_summary"))


def _conditions(record):
    out = record.get("expected_output") or {}
    inp = record.get("input") or {}
    tt = record.get("task_type")
    return {
        "has_user_text": _has_user_text(record),
        "asks_questions": bool(out.get("questions")) or "?" in (out.get("message_to_user") or ""),
        "proposes_changes": tt in ("route_adaptation", "goal_change") or bool(out.get("proposed_changes")),
        "has_contrastive": bool(record.get("contrastive")),
        "has_memory": tt == "memory_extraction" or bool(inp.get("user_memory") or inp.get("retrieved_memory")),
    }


def applicable_criteria(rubric, record) -> list:
    conds = _conditions(record)
    out = []
    for name, spec in rubric["criteria"].items():
        applies = spec.get("applies_to", "all")
        if applies == "all":
            out.append(name)
            continue
        items = applies if isinstance(applies, list) else [applies]
        if any(i == record.get("task_type") or conds.get(i) for i in items):
            out.append(name)
    return out


def hard_gates(rubric):
    return [n for n, s in rubric["criteria"].items() if s.get("hard_gate")]


def check_decision(rubric, record, action, ratings, overall, notes="", issues=()):
    """Return a list of problems; empty means the decision is internally consistent."""
    problems = []
    if action not in ACTIONS:
        return [f"action must be one of {ACTIONS}"]
    if overall not in OVERALL:
        problems.append(f"overall must be one of {OVERALL} (got {overall!r})")
    known = set(rubric["criteria"])
    for k, v in (ratings or {}).items():
        if k not in known:
            problems.append(f"unknown criterion {k!r}")
        elif v not in RATINGS:
            problems.append(f"{k}: rating must be one of {RATINGS} (got {v!r})")
    ratings = {k: v for k, v in (ratings or {}).items() if k in known and v in RATINGS}
    applicable = applicable_criteria(rubric, record)
    rules = rubric["decision_rules"]
    vals = set(ratings.values())
    gates = hard_gates(rubric)
    for i in issues or []:
        if i.get("criterion") not in known and i.get("criterion") != "overall":
            problems.append(f"issue criterion {i.get('criterion')!r} is not a rubric criterion")
        if i.get("severity") not in ("minor", "major", "critical"):
            problems.append(f"issue severity must be minor|major|critical (got {i.get('severity')!r})")
    if "unacceptable" in vals and overall not in ("incorrect", "needs_revision"):
        problems.append("a criterion rated 'unacceptable' requires overall 'incorrect' or 'needs_revision'")
    if overall == "excellent" and vals & {"major_issues", "unacceptable"}:
        problems.append("'excellent' is not allowed together with major issues")
    if action == "approve":
        missing = [c for c in applicable if c not in ratings]
        if missing:
            problems.append(f"approval needs a rating for every applicable criterion; missing {missing}")
        if overall not in rules["approve"]["overall"]:
            problems.append(f"approval needs overall in {rules['approve']['overall']}")
        bad = sorted(k for k, v in ratings.items() if v in rules["approve"]["forbidden_ratings"])
        if bad:
            problems.append(f"cannot approve with major issues / unacceptable ratings on {bad}")
        gate_bad = sorted(g for g in gates if ratings.get(g) not in rules["approve"]["hard_gates_must_be"] and g in ratings)
        if gate_bad:
            problems.append(f"hard-gate criteria {gate_bad} must be 'good' or 'not_applicable' to approve")
    elif action == "revise":
        if overall not in rules["revise"]["overall"]:
            problems.append(f"revise needs overall in {rules['revise']['overall']} ('incorrect' means reject)")
        if not issues and not (notes or "").strip():
            problems.append("revise needs at least one issue or a note saying what to change")
    elif action == "reject":
        if overall not in rules["reject"]["overall"]:
            problems.append(f"reject needs overall in {rules['reject']['overall']}")
        if not (notes or "").strip():
            problems.append("reject needs a note explaining why the example cannot be fixed in place")
    return problems


# ---------------------------------------------------------------------------------------------
# Store

@dataclass
class ReviewStore:
    events_path: Path
    snapshots_dir: Path
    legacy_log_path: Path | None = None

    @classmethod
    def default(cls):
        p = review_config()["paths"]
        return cls(repo_path(p["events"]), repo_path(p["snapshots"]), repo_path(p["legacy_log"]))

    def _check_legacy(self):
        if self.legacy_log_path and self.legacy_log_path.exists() and self.legacy_log_path.read_text(encoding="utf-8").strip():
            raise ReviewError(f"{rel(self.legacy_log_path)} contains v0.1 review records; migrate them to "
                              f"{rel(self.events_path)} before continuing (they are not read automatically).")

    def events(self) -> list:
        self._check_legacy()
        return read_jsonl(self.events_path) if self.events_path.exists() else []

    # snapshots ---------------------------------------------------------------------------------
    def snapshot_path(self, h) -> Path:
        return self.snapshots_dir / f"{h}.json"

    def write_snapshot(self, record) -> Path:
        h = content_hash(record)
        body = {"content_hash": h, "example_id": record["id"], **{k: record.get(k) for k in HASHED_FIELDS}}
        path = self.snapshot_path(h)
        if path.exists():
            if load_json(path) != body:
                raise ReviewError(f"snapshot {rel(path)} exists with different content — refusing to overwrite history")
        else:
            dump_json(body, path)
        return path

    def load_snapshot(self, h):
        path = self.snapshot_path(h)
        return load_json(path) if path.exists() else None

    # events ------------------------------------------------------------------------------------
    @staticmethod
    def _hash(event) -> str:
        return sha256_text(canonical_json({k: v for k, v in event.items() if k not in ("event_hash", "event_id")}))

    def append(self, event: dict) -> dict:
        events = self.events()
        ev = {k: v for k, v in event.items() if k not in ("event_hash", "event_id")}
        ev["log_version"] = LOG_VERSION
        ev["prev_event_hash"] = events[-1]["event_hash"] if events else None
        h = self._hash(ev)
        ev = {"event_id": "rev-" + h[:12], **ev, "event_hash": h}
        errs = schemas.validate("review_event", ev)
        if errs:
            raise ReviewError("invalid review event: " + "; ".join(errs[:5]))
        append_jsonl(ev, self.events_path)
        return ev

    def verify(self):
        """(errors, warnings) — errors mean the log was edited, truncated or reordered."""
        errors, warnings = [], []
        seen, prev = set(), None
        for i, ev in enumerate(self.events(), 1):
            for e in schemas.validate("review_event", ev):
                errors.append(f"line {i}: schema: {e}")
            h = self._hash(ev)
            if h != ev.get("event_hash"):
                errors.append(f"line {i}: event_hash does not match the content — the line was edited")
            if ev.get("event_id") != "rev-" + str(ev.get("event_hash", ""))[:12]:
                errors.append(f"line {i}: event_id does not match event_hash")
            p = ev.get("prev_event_hash")
            if p != prev:
                if p in seen or (p is None and i > 1):
                    warnings.append(f"line {i}: concurrent append (branch merge) — chain forks at {str(p)[:12]}; order kept")
                else:
                    errors.append(f"line {i}: predecessor {str(p)[:12]} missing — an event was removed or reordered")
            snap = self.load_snapshot(ev.get("content_hash"))
            if snap is None:
                errors.append(f"line {i}: snapshot for {ev.get('example_id')} {str(ev.get('content_hash'))[:12]} is missing")
            elif snap.get("content_hash") != ev.get("content_hash") or \
                    sha256_text(canonical_json({k: snap.get(k) for k in HASHED_FIELDS})) != ev.get("content_hash"):
                errors.append(f"line {i}: snapshot content does not match its hash")
            seen.add(ev.get("event_hash"))
            prev = ev.get("event_hash")
        return errors, warnings


# ---------------------------------------------------------------------------------------------
# Status resolution

def _qualifies_language(ev, langs):
    return set(langs) <= set(ev["reviewer"]["languages"])


def resolve(record, events, cfg=None) -> dict:
    cfg = cfg or review_config()
    h = content_hash(record)
    langs = required_languages(record)
    doms = required_expert_domains(record, cfg)
    info = {"status": "pending", "detail": "not_reviewed", "content_hash": h,
            "tier": "expert_review_required" if doms else "human_review_required",
            "required_languages": langs, "required_expert_domains": doms, "decisions": {}, "events": 0}
    evs = [e for e in events if e.get("example_id") == record.get("id")]
    info["events"] = len(evs)
    if not evs:
        return info
    cur = [e for e in evs if e.get("content_hash") == h]
    if not cur:
        info["detail"] = "content_changed"
        return info
    latest = {}
    for e in cur:
        latest[e["reviewer_id"]] = e
    info["decisions"] = {r: e["action"] for r, e in latest.items()}
    adj = [e for e in cur if "adjudicator" in e["reviewer"]["roles"]]
    decisive = [adj[-1]] if adj else list(latest.values())
    actions = {e["action"] for e in decisive}
    if "reject" in actions:
        info["status"], info["detail"] = "rejected", "decided"
    elif "revise" in actions:
        info["status"], info["detail"] = "needs_revision", "decided"
    else:
        # D-030: a qualified human approval of the current content is enough, whatever the risk tier
        approvals = [e for e in decisive if e["action"] == "approve" and e["reviewer"]["human"]
                     and (not cfg["approval"]["require_language_match"] or _qualifies_language(e, langs))]
        if approvals:
            info["status"], info["detail"] = "approved", "decided"
    return info


def statuses(records, events=None, cfg=None) -> dict:
    events = ReviewStore.default().events() if events is None else events
    return {r["id"]: resolve(r, events, cfg) for r in records}


# Why a content version is not training-eligible (release manifests list every such example with its reason).
INELIGIBILITY_REASONS = {
    "not_reviewed": "no human decision on the current content",
    "content_changed": "the content changed after its last decision; the current version needs review",
    "needs_revision": "a human reviewer asked for a revision",
    "rejected": "a human reviewer rejected it",
}


def training_eligibility(info) -> dict:
    """Separate the review states for one resolved example (see `resolve`).

    human_reviewed    a human decision exists on the current content hash
    training_eligible the exact current content is `approved` (qualified human approval, no objection; D-030)
    reason            why it is not training-eligible (a key of INELIGIBILITY_REASONS), else None

    Training eligibility is only the review half of a training release: the release gates
    (configs/release_gates.yaml) still decide whether a release is training_ready.
    """
    eligible = info["status"] in TRAINING_ELIGIBLE
    if eligible:
        reason = None
    elif info["status"] in ("needs_revision", "rejected"):
        reason = info["status"]
    else:
        reason = info["detail"]
    return {"human_reviewed": bool(info["decisions"]), "training_eligible": eligible, "reason": reason}


# ---------------------------------------------------------------------------------------------
# Recording a decision

def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_decision(store, registry, rubric, record, reviewer_id, action, ratings, overall, notes="", issues=(),
                    review_item_id=None, independent_rating=None, acknowledge=False, open_findings=(), timestamp=None,
                    cfg=None):
    """Validate and append one decision. `open_findings` = ids of automated findings / known issues at a
    severity that requires acknowledgement before approval (see configs/review.yaml)."""
    cfg = cfg or review_config()
    rev = registry.get(reviewer_id)
    if rev is None:
        raise ReviewError(f"unknown reviewer {reviewer_id!r} — add yourself to review/reviewers.yaml first")
    if not rev["active"]:
        raise ReviewError(f"reviewer {reviewer_id!r} is inactive")
    if not rev["human"]:
        raise ReviewError(f"reviewer {reviewer_id!r} is not marked human: true — automated agents cannot record review decisions")
    langs = required_languages(record)
    if cfg["approval"]["require_language_match"] and not set(langs) <= set(rev["languages"]):
        raise ReviewError(f"{record['id']} needs a reviewer who reads {langs}; {reviewer_id} lists {rev['languages']}")
    problems = check_decision(rubric, record, action, ratings, overall, notes, issues)
    if problems:
        raise ReviewError(f"{record['id']}: " + "; ".join(problems))
    open_findings = sorted(open_findings or [])
    if action == "approve" and open_findings and not acknowledge:
        raise ReviewError(
            f"{record['id']} has open high-severity findings {open_findings}. Rate it first, then read them with "
            f"`gj review show {record['id']} --show-automated` and re-run with --acknowledge-findings if you still approve.")
    events = store.events()
    before = resolve(record, events, cfg)
    doms = required_expert_domains(record, cfg)
    snap = store.write_snapshot(record)
    event = {
        "example_id": record["id"], "content_hash": content_hash(record), "reviewer_id": reviewer_id,
        "reviewer": {"roles": rev["roles"], "languages": rev["languages"], "expert_domains": rev["expert_domains"],
                     "human": True},
        "timestamp": timestamp or now_utc(), "action": action, "old_status": before["status"],
        "rubric_version": rubric["version"], "rubric": dict(sorted((ratings or {}).items())), "overall": overall,
        "notes": notes or "", "issues": list(issues or []),
        "review_tier": "expert_review_required" if doms else "human_review_required",
        "required_languages": langs, "required_expert_domains": doms, "review_item_id": review_item_id,
        "acknowledged_findings": open_findings if action == "approve" else [],
        "snapshot": rel(snap),
    }
    if independent_rating is not None:
        event["independent_rating"] = bool(independent_rating)
    provisional = dict(event, reviewer_id=reviewer_id)
    after = resolve(record, events + [provisional], cfg)
    event["new_status"] = after["status"]
    event["new_status_detail"] = after["detail"]
    return store.append(event)


# ---------------------------------------------------------------------------------------------
# Agreement statistics

def cohen_kappa(a, b):
    """Cohen's kappa for two raters over the same items (lists of labels). None if undefined."""
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    labels = set(a) | set(b)
    pe = sum((a.count(k) / n) * (b.count(k) / n) for k in labels)
    if pe >= 1.0:
        return 1.0 if po == 1.0 else None
    return round((po - pe) / (1 - pe), 3)


def agreement(events, restrict_to=None):
    """Pairwise agreement between reviewers on the same content (latest decision per reviewer)."""
    latest = {}
    for e in events:
        if restrict_to and e["example_id"] not in restrict_to:
            continue
        latest[(e["example_id"], e["content_hash"], e["reviewer_id"])] = e
    by_item = {}
    for (ex, h, r), e in latest.items():
        by_item.setdefault((ex, h), {})[r] = e
    reviewers = sorted({r for (_, _, r) in latest})
    pairs = []
    severe = {"major_issues", "unacceptable"}
    for i, ra in enumerate(reviewers):
        for rb in reviewers[i + 1:]:
            shared = [(v[ra], v[rb]) for v in by_item.values() if ra in v and rb in v]
            if not shared:
                continue
            act_a, act_b = [x["action"] for x, _ in shared], [y["action"] for _, y in shared]
            ov_a, ov_b = [x["overall"] for x, _ in shared], [y["overall"] for _, y in shared]
            crit_total = crit_same = crit_severe = 0
            for x, y in shared:
                for c in set(x["rubric"]) & set(y["rubric"]):
                    if "not_applicable" in (x["rubric"][c], y["rubric"][c]):
                        continue
                    crit_total += 1
                    crit_same += x["rubric"][c] == y["rubric"][c]
                    crit_severe += (x["rubric"][c] in severe) != (y["rubric"][c] in severe)
            pairs.append({
                "reviewers": [ra, rb], "items": len(shared),
                "decision_agreement": round(sum(p == q for p, q in zip(act_a, act_b)) / len(shared), 3),
                "decision_kappa": cohen_kappa(act_a, act_b),
                "overall_agreement": round(sum(p == q for p, q in zip(ov_a, ov_b)) / len(shared), 3),
                "overall_kappa": cohen_kappa(ov_a, ov_b),
                "criterion_exact_agreement": round(crit_same / crit_total, 3) if crit_total else None,
                "criterion_severity_disagreement": round(crit_severe / crit_total, 3) if crit_total else None,
            })
    multi = sum(1 for v in by_item.values() if len(v) >= 2)
    return {"reviewers": reviewers, "items_with_2plus_reviewers": multi, "pairs": pairs}
