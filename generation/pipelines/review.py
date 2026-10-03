"""`gj review …` — human review workflow (v0.2). Walkthrough: docs/HUMAN_REVIEW_GUIDE.md.

    sample      deterministic review sample -> review/review_manifest_v<ver>.json
    list        examples with tier, required qualifications and review status
    show        one example for review (automated findings hidden unless --show-automated)
    template    a decision file (YAML) with the applicable rubric criteria
    approve | revise | reject   record a decision (from a decision file and/or flags)
    apply       record every filled entry of a review sheet (batch)
    history     all decisions on an example + diffs between reviewed versions
    stats       status counts, reviewer activity, agreement (Cohen's kappa), pipeline funnel
    export      md (reading packet) | sheet (batch YAML) | json (statuses + events)
    verify-log  check the hash chain and snapshots of the review log
"""
import difflib
import json
from collections import Counter, defaultdict

import yaml

from gjcore.config import versions
from gjcore.io import load_json, load_yaml
from gjcore.paths import rel, repo_path
from gjcore.records import content_hash

from . import review_store as RS
from .pool import load_pool

SEVERE = ("major_issues", "unacceptable")


# ---------------------------------------------------------------------------------------------
# helpers

def _version(version=None):
    return version or versions()["dataset_version"]


def _path(key, version=None):
    return repo_path(RS.review_config()["paths"][key].format(version=_version(version)))


def sample_version(version=None):
    """The review sample in force for a dataset version: its own manifest if one was drawn, otherwise the
    frozen sample carried forward (configs/review.yaml sampling.sample_version)."""
    version = _version(version)
    if _path("manifest", version).exists():
        return version
    return RS.review_config()["sampling"].get("sample_version") or version


def load_manifest(version=None):
    p = _path("manifest", sample_version(version))
    return load_json(p) if p.exists() else None


def manifest_items(version=None) -> dict:
    return {it["example_id"]: it for it in (load_manifest(version) or {}).get("items", [])}


def _pool():
    return {r["id"]: (r, p, o) for r, p, o in load_pool()}


def _get(pool, example_id):
    if example_id not in pool:
        raise RS.ReviewError(f"unknown example id {example_id!r}")
    return pool[example_id]


def _dump(obj) -> str:
    return yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=110)


def live_findings(record, version=None):
    """Audit findings (heuristics, computed now) + open known issues for one example."""
    from . import audit
    findings = [f for f in audit.run_audit([record]) if f["scope"] in ("expected_output", "input", "contrastive")]
    known = [k for k in audit.load_known_issues(_version(version)) if record["id"] in k["records"]]
    return findings, known


def open_blocking_findings(record, version=None):
    sev = set(RS.review_config()["approval"]["acknowledge_severities"])
    findings, known = live_findings(record, version)
    ids = [f["finding_id"] for f in findings if f["severity"] in sev and f["scope"] in ("expected_output", "input")]
    ids += [k["id"] for k in known if k["status"] == "open" and k["severity"] in sev]
    return sorted(ids)


# ---------------------------------------------------------------------------------------------
# list / show / template

def cmd_list(status=None, tier=None, task_type=None, language=None, manifest_only=False, as_json=False):
    pool = _pool()
    events = RS.ReviewStore.default().events()
    items = manifest_items()
    rows = []
    order = [i for i in items] if manifest_only else sorted(pool)
    for rid in order:
        rec, path, origin = _get(pool, rid)
        info = RS.resolve(rec, events)
        it = items.get(rid)
        if status and info["status"] != status:
            continue
        if tier and info["tier"] != tier:
            continue
        if task_type and rec["task_type"] != task_type:
            continue
        if language and rec["language"] != language:
            continue
        rows.append({"id": rid, "item": (it or {}).get("review_item_id", ""), "calibration": bool((it or {}).get("calibration")),
                     "task_type": rec["task_type"], "language": rec["language"], "input_language": rec["input_language"],
                     "tier": info["tier"], "requires": info["required_languages"],
                     "risk_domains": info["required_expert_domains"],
                     "status": info["status"], "decisions": info["decisions"],
                     "changed_since_sampling": bool(it and it["content_hash"] != info["content_hash"]), "file": rel(path)})
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    print(f"{'example':18} {'item':14} {'task_type':29} {'lang':6} {'tier':7} {'status':24} reviewer reads / risk domains")
    for r in rows:
        flag = "*" if r["calibration"] else " "
        chg = "  [changed since sampling]" if r["changed_since_sampling"] else ""
        lang = r["language"] + ("+mx" if r["input_language"] == "mixed" else "")
        risk = f" / {','.join(r['risk_domains'])}" if r["risk_domains"] else ""
        print(f"{r['id']:18} {r['item']:13}{flag} {r['task_type']:29} {lang:6} {'risk' if r['tier'].startswith('expert') else 'human':7} "
              f"{r['status']:24} {','.join(r['requires'])}{risk}{chg}")
    print(f"\n{len(rows)} example(s); " + ", ".join(f"{k}={v}" for k, v in sorted(Counter(r['status'] for r in rows).items())))
    if manifest_only:
        print("* = calibration item (every reviewer reviews these first)")
    return 0


def _criteria_lines(rubric, record):
    lines = []
    for name in RS.applicable_criteria(rubric, record):
        spec = rubric["criteria"][name]
        gate = " [hard gate]" if spec.get("hard_gate") else ""
        lines.append(f"  {spec['code']} {name}{gate}: {spec['question']}")
    return lines


def cmd_show(example_id, show_automated=False, version=None):
    pool = _pool()
    rec, path, origin = _get(pool, example_id)
    events = RS.ReviewStore.default().events()
    info = RS.resolve(rec, events)
    rubric = RS.load_rubric()
    it = manifest_items(version).get(example_id)
    print(f"# {example_id}  ({rel(path)}, {origin})")
    print(f"task_type: {rec['task_type']}   behaviour: {', '.join(rec['behavior'])}")
    print(f"language: {rec['language']} (input: {rec['input_language']})   domain: {rec['domain']}   difficulty: {rec['difficulty']}"
          f"   goal_size: {rec['goal_size']}   safety: {rec['safety_category']}")
    print(f"tier: {info['tier']}   needs reviewer languages: {info['required_languages']}"
          + (f"   risk domains: {info['required_expert_domains']} (review with care; no expert sign-off needed, D-030)"
             if info['required_expert_domains'] else ""))
    print(f"status: {info['status']}   content_hash: {info['content_hash'][:16]}…   decisions: {info['decisions'] or '—'}")
    if it:
        print(f"review item: {it['review_item_id']} (stratum {it['stratum']}{', calibration' if it['calibration'] else ''})"
              + ("   ⚠ content changed since sampling" if it["content_hash"] != info["content_hash"] else ""))
    print("\nApplicable rubric criteria (rate each; O overall):")
    print("\n".join(_criteria_lines(rubric, rec)))
    print("\n## input\n" + _dump(rec["input"]))
    print("## expected_output\n" + _dump(rec["expected_output"]))
    for c in rec.get("contrastive") or []:
        print(f"## contrastive {c['id']} — tagged failure modes: {', '.join(c['failure_modes'])}")
        print(f"critique: {c['critique']}\n" + _dump(c["output"]))
    if not show_automated:
        print("(Author notes, validator results and audit findings are hidden so that your rating stays independent.\n"
              f" Rate first, then: gj review show {example_id} --show-automated)")
        return 0
    from generation.validators.records import validate_example
    rep = validate_example(rec)
    print("## automated — validation")
    print(f"errors: {rep.errors or 'none'}\nwarnings: {rep.warnings or 'none'}")
    findings, known = live_findings(rec, version)
    print("## automated — audit heuristics (review aids, not verdicts)")
    for f in findings:
        print(f"  [{f['severity']}] {f['finding_id']} {f['scope']} {f['location']}: {f['message']}\n      evidence: {f['evidence']}")
    if not findings:
        print("  none")
    print("## known issues register")
    for k in known:
        print(f"  {k['id']} [{k['severity']}, {k['status']}] {k['description']}\n      proposed: {k['proposed_revision']}")
    if not known:
        print("  none")
    print("## author annotations\n" + _dump(rec.get("annotations") or {}))
    return 0


def decision_template(record, rubric, info, item=None) -> str:
    lines = [
        f"# Decision for {record['id']} — fill in, then: gj review <approve|revise|reject> {record['id']} --reviewer YOU --from THIS_FILE",
        "# ratings: good | minor_issues | major_issues | unacceptable | not_applicable   (rubric: " + RS.review_config()["rubric"] + ")",
        "# overall: excellent | acceptable | needs_revision | incorrect",
        f"example_id: {record['id']}",
        f"content_hash: {info['content_hash']}",
        f"review_item_id: {(item or {}).get('review_item_id') or 'null'}",
        "action: null            # approve | revise | reject",
        "overall: null",
        "ratings:",
    ]
    for name in RS.applicable_criteria(rubric, record):
        spec = rubric["criteria"][name]
        gate = " [hard gate]" if spec.get("hard_gate") else ""
        lines.append(f"  {name}: null   # {spec['code']}{gate} {spec['question']}")
    lines += [
        "issues: []              # - {criterion: realism, severity: major, description: '...', proposed_fix: '...', location: '...'}",
        "notes: ''",
        "independent_rating: true   # set to false if you read automated findings before rating",
    ]
    return "\n".join(lines) + "\n"


def cmd_template(example_id, out=None):
    pool = _pool()
    rec, _, _ = _get(pool, example_id)
    info = RS.resolve(rec, RS.ReviewStore.default().events())
    text = decision_template(rec, RS.load_rubric(), info, manifest_items().get(example_id))
    if out:
        p = repo_path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print(f"Wrote {out}")
    else:
        print(text, end="")
    return 0


# ---------------------------------------------------------------------------------------------
# decisions

def _parse_issue(s):
    parts = s.split(":", 3)
    if len(parts) < 3:
        raise RS.ReviewError(f"--issue must be 'criterion:severity:description[:proposed fix]' (got {s!r})")
    issue = {"criterion": parts[0].strip(), "severity": parts[1].strip(), "description": parts[2].strip()}
    if len(parts) == 4 and parts[3].strip():
        issue["proposed_fix"] = parts[3].strip()
    return issue


def _parse_rate(s):
    if "=" not in s:
        raise RS.ReviewError(f"--rate must be criterion=rating (got {s!r})")
    k, v = s.split("=", 1)
    return k.strip(), v.strip()


def decide(action, example_id, reviewer, decision_file=None, rates=(), overall=None, notes=None, issues=(),
           acknowledge=False, item_id=None, independent=None, store=None, registry=None, pool=None):
    pool = pool or _pool()
    rec, _, _ = _get(pool, example_id)
    store = store or RS.ReviewStore.default()
    registry = registry if registry is not None else RS.load_registry()
    rubric = RS.load_rubric()
    ratings, iss, note, ov, indep, item = {}, [], "", None, None, item_id
    if decision_file:
        d = load_yaml(repo_path(decision_file)) or {}
        if d.get("example_id") not in (None, example_id):
            raise RS.ReviewError(f"decision file is for {d.get('example_id')}, not {example_id}")
        if d.get("content_hash") and d["content_hash"] != content_hash(rec):
            raise RS.ReviewError(f"{example_id} changed since the decision file was written — review the current content")
        if d.get("action") and d["action"] != action:
            raise RS.ReviewError(f"decision file says action {d['action']!r}, command is {action!r}")
        ratings = {k: v for k, v in (d.get("ratings") or {}).items() if v is not None}
        iss, note, ov = list(d.get("issues") or []), d.get("notes") or "", d.get("overall")
        indep = d.get("independent_rating")
        item = item or d.get("review_item_id")
    ratings.update(dict(_parse_rate(r) for r in rates))
    iss += [_parse_issue(i) for i in issues]
    ov = overall or ov
    note = notes if notes is not None else note
    indep = independent if independent is not None else indep
    item = item or (manifest_items().get(example_id) or {}).get("review_item_id")
    blocking = open_blocking_findings(rec) if action == "approve" else []
    ev = RS.record_decision(store, registry, rubric, rec, reviewer, action, ratings, ov, note, iss,
                            review_item_id=item, independent_rating=indep, acknowledge=acknowledge,
                            open_findings=blocking)
    print(f"Recorded {ev['event_id']}: {example_id} {ev['old_status']} -> {ev['new_status']} "
          f"({action} by {reviewer}, overall {ev['overall']})")
    return ev


def cmd_decide(action, example_id, reviewer, **kw):
    decide(action, example_id, reviewer, **kw)
    return 0


def cmd_apply(sheet, reviewer, acknowledge=False):
    data = load_yaml(repo_path(sheet)) or {}
    pool, store, registry = _pool(), RS.ReviewStore.default(), RS.load_registry()
    applied, errors = 0, []
    for entry in data.get("entries") or []:
        action = entry.get("action")
        if not action:
            continue
        tmp = dict(entry)
        try:
            rec, _, _ = _get(pool, entry.get("example_id"))
            if entry.get("content_hash") and entry["content_hash"] != content_hash(rec):
                raise RS.ReviewError(f"{rec['id']} changed since the sheet was exported — re-export and review again")
            ratings = {k: v for k, v in (tmp.get("ratings") or {}).items() if v is not None}
            blocking = open_blocking_findings(rec) if action == "approve" else []
            ev = RS.record_decision(store, registry, RS.load_rubric(), rec, reviewer, action, ratings, tmp.get("overall"),
                                    tmp.get("notes") or "", tmp.get("issues") or [],
                                    review_item_id=tmp.get("review_item_id"),
                                    independent_rating=tmp.get("independent_rating"),
                                    acknowledge=acknowledge, open_findings=blocking)
            applied += 1
            print(f"  ✓ {rec['id']}: {ev['old_status']} -> {ev['new_status']}")
        except RS.ReviewError as e:
            errors.append(str(e))
    print(f"Applied {applied} decision(s).")
    for e in errors:
        print(f"  ✗ {e}")
    return 1 if errors else 0


# ---------------------------------------------------------------------------------------------
# history / verify

def _version_text(snap_or_record):
    return _dump({k: snap_or_record.get(k) for k in ("task_type", "input", "expected_output", "contrastive")}).splitlines()


def cmd_history(example_id, diff=True):
    pool = _pool()
    rec, _, _ = _get(pool, example_id)
    store = RS.ReviewStore.default()
    events = [e for e in store.events() if e["example_id"] == example_id]
    cur = content_hash(rec)
    print(f"# history of {example_id} — current content {cur[:12]}; status {RS.resolve(rec, store.events())['status']}")
    if not events:
        print("No review decisions yet.")
        return 0
    versions_seen = []
    for e in events:
        if e["content_hash"] not in versions_seen:
            versions_seen.append(e["content_hash"])
        print(f"- {e['timestamp']} {e['event_id']} {e['reviewer_id']}: {e['action']} ({e['old_status']} -> {e['new_status']}), "
              f"overall {e['overall']}, content {e['content_hash'][:12]}")
        severe = {k: v for k, v in e["rubric"].items() if v in SEVERE}
        if severe:
            print(f"    severe ratings: {severe}")
        for i in e["issues"]:
            print(f"    issue [{i['severity']}] {i['criterion']}: {i['description']}"
                  + (f"  → fix: {i['proposed_fix']}" if i.get("proposed_fix") else ""))
        if e["notes"]:
            print(f"    notes: {e['notes']}")
    if cur not in versions_seen:
        versions_seen.append(cur)
    if diff:
        for a, b in zip(versions_seen, versions_seen[1:]):
            sa = store.load_snapshot(a)
            sb = store.load_snapshot(b) if b != cur else {**rec}
            if not sa or not sb:
                print(f"(snapshot missing for {a[:12]} or {b[:12]})")
                continue
            print(f"\n## diff {a[:12]} -> {b[:12]}{' (current, not reviewed yet)' if b == cur and b not in [e['content_hash'] for e in events] else ''}")
            for line in difflib.unified_diff(_version_text(sa), _version_text(sb), a[:12], b[:12], lineterm="", n=2):
                print(line)
    return 0


def cmd_verify_log():
    store = RS.ReviewStore.default()
    errors, warnings = store.verify()
    n = len(store.events())
    print(f"Review log {rel(store.events_path)}: {n} event(s); {len(errors)} error(s), {len(warnings)} warning(s)")
    for e in errors:
        print(f"  ✗ {e}")
    for w in warnings:
        print(f"  ! {w}")
    return 1 if errors else 0


# ---------------------------------------------------------------------------------------------
# stats

def compute_stats(version=None):
    version = _version(version)
    pool = _pool()
    records = [r for r, _, _ in pool.values()]
    store = RS.ReviewStore.default()
    events = store.events()
    infos = {r["id"]: RS.resolve(r, events) for r in records}
    manifest = load_manifest(version)
    items = manifest_items(version)
    by = lambda key: {k: dict(sorted(v.items())) for k, v in sorted(_group(records, infos, key).items())}
    reviewed_items = [i for i in items if infos.get(i, {}).get("decisions")]
    calib = set((manifest or {}).get("calibration", {}).get("items", []))
    calib_ids = {it["example_id"] for it in items.values() if it["review_item_id"] in calib}
    calib_multi = [i for i in calib_ids if len(infos.get(i, {}).get("decisions", {})) >= 2]
    per_reviewer = defaultdict(Counter)
    for e in events:
        per_reviewer[e["reviewer_id"]][e["action"]] += 1
    crit_issues = Counter()
    for e in events:
        for k, v in e["rubric"].items():
            if v in SEVERE:
                crit_issues[k] += 1
    from generation.validators.records import validate_example
    valid = sum(1 for r in records if validate_example(r).ok)
    from .split import release_paths
    from gjcore.io import read_jsonl
    rp = release_paths(version)
    released = set()
    for s in ("train", "validation"):
        if rp[s].exists():
            released |= {row["id"] for row in read_jsonl(rp[s]) if content_hash(row) == infos.get(row["id"], {}).get("content_hash")}
    errors, warnings = store.verify()
    mode = RS.review_mode()
    registry = RS.load_registry()
    active = [r for r in registry.values() if r["human"] and r["active"]]
    solo = mode == "solo_owner"
    return {
        "dataset_version": version,
        "review_mode": mode,
        "governance": {
            "active_human_reviewers": [{"id": r["id"], "roles": r["roles"]} for r in active],
            "active_dataset_reviewers": sum(1 for r in active if "dataset_reviewer" in r["roles"]),
            # inter-reviewer checks only mean something with several independent reviewers (configs/release_gates.yaml)
            "independent_pair_calibration": "N/A" if solo else "gate calibration_agreement (see `gj gates`)",
            "reviewer_diversity": "N/A" if solo else "gate reviewer_diversity (see `gj gates`)",
        },
        "review_state_pool": _review_state(records, infos),
        "review_state_sample": _review_state([pool[i][0] for i in items if i in pool], infos) if items else None,
        "status": dict(sorted(Counter(i["status"] for i in infos.values()).items())),
        "status_by_tier": by("tier"), "status_by_language": by("language"), "status_by_task_type": by("task_type"),
        "manifest": {"present": bool(manifest), "items": len(items), "items_with_decisions": len(reviewed_items),
                     "calibration_items": len(calib_ids), "calibration_items_with_2plus_reviewers": len(calib_multi)},
        "reviewers": {r: dict(c) for r, c in sorted(per_reviewer.items())},
        "severe_ratings_by_criterion": dict(crit_issues.most_common()),
        "agreement_all": RS.agreement(events),
        "agreement_calibration": RS.agreement(events, restrict_to=calib_ids) if calib_ids else None,
        "funnel": {
            "raw": len(records), "valid": valid,
            "decided": sum(1 for i in infos.values() if i["status"] != "pending"),
            "approved": sum(1 for i in infos.values() if i["status"] == "approved"),
            "in_release_train_validation": len(released),
            "approved_in_release": sum(1 for rid in released if infos[rid]["status"] == "approved"),
        },
        "log": {"events": len(events), "errors": len(errors), "warnings": len(warnings)},
    }


def _review_state(records, infos):
    """Human-reviewed / training-eligible / ineligibility reasons for a set of examples."""
    te = [RS.training_eligibility(infos[r["id"]]) for r in records]
    reasons = Counter(t["reason"] for t in te if not t["training_eligible"])
    return {"total": len(te), "human_reviewed": sum(t["human_reviewed"] for t in te),
            "training_eligible": sum(t["training_eligible"] for t in te),
            **{k: reasons.get(k, 0) for k in RS.INELIGIBILITY_REASONS}}


def _group(records, infos, key):
    out = defaultdict(Counter)
    for r in records:
        k = infos[r["id"]]["tier"] if key == "tier" else r[key]
        out[k][infos[r["id"]]["status"]] += 1
    return out


def cmd_stats(as_json=False, version=None):
    s = compute_stats(version)
    if as_json:
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0
    g, solo = s["governance"], s["review_mode"] == "solo_owner"
    print(f"Review mode: {s['review_mode']} (configs/review.yaml governance.mode)")
    print(f"Human reviewers (registered, active): {len(g['active_human_reviewers'])} — "
          + (", ".join(f"{r['id']} {r['roles']}" for r in g["active_human_reviewers"]) or "none")
          + "; one qualified human approval suffices for every tier (D-030)")
    if solo and g["active_dataset_reviewers"] > 1:
        print(f"  note: {g['active_dataset_reviewers']} active dataset reviewers in solo_owner mode. Their recorded decisions "
              "all count; set `active: false` for anyone no longer reviewing (past events keep their snapshot), or switch "
              "to multi_reviewer mode.")
    for label, key in (("Pool", "review_state_pool"), ("Review sample", "review_state_sample")):
        rs = s[key]
        if rs:
            print(f"{label} ({rs['total']}): human-reviewed {rs['human_reviewed']}/{rs['total']} · training-eligible "
                  f"{rs['training_eligible']}/{rs['total']} · needs revision "
                  f"{rs['needs_revision']} · rejected {rs['rejected']} · not reviewed {rs['not_reviewed']} · content changed "
                  f"{rs['content_changed']}")
    why = " (solo_owner mode — applies only with several independent reviewers)" if solo else ""
    print(f"Independent pair calibration: {g['independent_pair_calibration']}{why}")
    print(f"Reviewer diversity: {g['reviewer_diversity']}{why}\n")
    f = s["funnel"]
    print(f"Review status v{s['dataset_version']}: " + ", ".join(f"{k}={v}" for k, v in s["status"].items()))
    print(f"Pipeline funnel: raw {f['raw']} -> valid {f['valid']} -> decided {f['decided']} -> approved {f['approved']} "
          f"-> in release (train+val) {f['in_release_train_validation']} -> approved & released {f['approved_in_release']}")
    for title, key in (("by tier", "status_by_tier"), ("by language", "status_by_language"), ("by task type", "status_by_task_type")):
        print(f"\n{title}:")
        for k, v in s[key].items():
            print(f"  {k:30} " + ", ".join(f"{a}={b}" for a, b in v.items()))
    m = s["manifest"]
    if m["present"]:
        print(f"\nReview sample: {m['items_with_decisions']}/{m['items']} items decided; calibration "
              f"{m['calibration_items_with_2plus_reviewers']}/{m['calibration_items']} with 2+ reviewers")
    print(f"\nReviewers: {s['reviewers'] or 'none yet'}")
    if s["severe_ratings_by_criterion"]:
        print(f"Severe ratings (major/unacceptable) by criterion: {s['severe_ratings_by_criterion']}")
    for label, ag in (("all items", s["agreement_all"]), ("calibration items", s["agreement_calibration"])):
        if ag and ag["pairs"]:
            print(f"\n{'Historical reviewer-pair agreement — informational, not a gate in solo_owner mode' if solo else 'Agreement'} "
                  f"({label}, {ag['items_with_2plus_reviewers']} item(s) with 2+ reviewers):")
            for p in ag["pairs"]:
                print(f"  {p['reviewers'][0]} vs {p['reviewers'][1]}: n={p['items']} decision {p['decision_agreement']} "
                      f"(kappa {p['decision_kappa']}), overall {p['overall_agreement']} (kappa {p['overall_kappa']}), "
                      f"criteria exact {p['criterion_exact_agreement']}, severity disagreement {p['criterion_severity_disagreement']}")
    print(f"\nReview log: {s['log']['events']} event(s), {s['log']['errors']} integrity error(s)")
    return 0


# ---------------------------------------------------------------------------------------------
# export

def _select(pool, events, status=None, ids=None, manifest_only=False):
    items = manifest_items()
    order = list(items) if manifest_only else sorted(pool)
    for rid in order:
        if ids and rid not in ids:
            continue
        rec, path, origin = _get(pool, rid)
        info = RS.resolve(rec, events)
        if status and info["status"] != status:
            continue
        yield rec, path, info, items.get(rid)


def cmd_export(fmt, out, status=None, ids=None, manifest_only=False, with_automated=False):
    pool = _pool()
    events = RS.ReviewStore.default().events()
    rubric = RS.load_rubric()
    selected = list(_select(pool, events, status, ids, manifest_only))
    path = repo_path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "sheet":
        entries = []
        for rec, _, info, it in selected:
            entries.append({"example_id": rec["id"], "content_hash": info["content_hash"],
                            "review_item_id": (it or {}).get("review_item_id"), "task_type": rec["task_type"],
                            "language": rec["language"], "requires": info["required_languages"],
                            "risk_domains": info["required_expert_domains"],
                            "action": None, "overall": None,
                            "ratings": {c: None for c in RS.applicable_criteria(rubric, rec)},
                            "issues": [], "notes": "", "independent_rating": True})
        header = ("# Review sheet — for each entry set action (approve | revise | reject), overall, ratings, issues, notes.\n"
                  "# Read the examples with `gj review show ID` (or the md export). Record with: gj review apply THIS --reviewer YOU\n")
        path.write_text(header + _dump({"entries": entries}), encoding="utf-8")
    elif fmt == "json":
        rows = []
        for rec, p, info, it in selected:
            rows.append({"id": rec["id"], "file": rel(p), "review_item": it, **info,
                         "events": [e for e in events if e["example_id"] == rec["id"]]})
        path.write_text(json.dumps({"dataset_version": _version(), "examples": rows}, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    elif fmt == "md":
        out_lines = [f"# GoalJourney review packet — dataset v{_version()}", "",
                     f"{len(selected)} example(s). Rubric: `{RS.review_config()['rubric']}`. Record decisions with "
                     "`gj review template ID` + `gj review approve|revise|reject ID --from FILE`.", ""]
        if not with_automated:
            out_lines += ["Automated findings are deliberately not included (rate independently first).", ""]
        for rec, p, info, it in selected:
            title = f"{(it or {}).get('review_item_id', '') + ' — ' if it else ''}{rec['id']}"
            out_lines += [f"## {title}", "",
                          f"- task: `{rec['task_type']}` · language: {rec['language']} (input {rec['input_language']}) · "
                          f"domain: {rec['domain']} · safety: {rec['safety_category']}",
                          f"- tier: {info['tier']} · reviewer must read: {', '.join(info['required_languages'])}"
                          + (f" · risk domains: {', '.join(info['required_expert_domains'])}" if info['required_expert_domains'] else ""),
                          f"- status: {info['status']} · content `{info['content_hash'][:12]}`",
                          "", "Criteria to rate:", ""] + [f"- {l.strip()}" for l in _criteria_lines(rubric, rec)] + [
                          "", "### Input", "", "```yaml", _dump(rec["input"]).rstrip(), "```",
                          "", "### Expected output", "", "```yaml", _dump(rec["expected_output"]).rstrip(), "```", ""]
            for c in rec.get("contrastive") or []:
                out_lines += [f"### Rejected output {c['id']} ({', '.join(c['failure_modes'])})", "", f"> {c['critique']}", "",
                              "```yaml", _dump(c["output"]).rstrip(), "```", ""]
            if with_automated:
                findings, known = live_findings(rec)
                out_lines += ["### Automated findings (review aids)", ""]
                out_lines += [f"- [{f['severity']}] {f['rule']} @ {f['location']}: {f['evidence']}" for f in findings] or ["- none"]
                out_lines += [f"- {k['id']} [{k['severity']}] {k['description']}" for k in known]
                out_lines += [""]
        path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    else:
        raise RS.ReviewError(f"unknown export format {fmt!r}")
    print(f"Wrote {len(selected)} example(s) to {out}")
    return 0
