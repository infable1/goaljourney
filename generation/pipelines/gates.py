"""`gj gates`: may this release be called `training_ready`? (configs/release_gates.yaml)

Gates are evaluated live: review decisions, known issues and leakage dispositions change after a
release is built, while the release content itself is immutable.
"""
import json
from collections import Counter
from dataclasses import asdict, dataclass

from gjcore.config import load_config, versions
from gjcore.io import load_yaml, read_jsonl
from gjcore.paths import rel, repo_path
from gjcore.records import content_hash, load_eval_cases

from . import review_store as RS


@dataclass
class GateResult:
    id: str
    passed: bool
    detail: str
    rationale: str
    blocking: bool = True

    def to_dict(self):
        return asdict(self)


def load_gates():
    return load_config("release_gates")


def release_rows(version=None):
    from .split import release_paths
    paths = release_paths(version or versions()["dataset_version"])
    rows = {}
    for split in ("train", "validation"):
        if not paths[split].exists():
            return None
        rows[split] = read_jsonl(paths[split])
    return rows


def _share(n, d):
    return n / d if d else 0.0


def evaluate(version=None, rows=None, purpose="sft", events=None, manifest=None):
    """rows: {"train": [...], "validation": [...]} (defaults to the built release)."""
    version = version or versions()["dataset_version"]
    cfg = load_gates()["gates"]
    rows = rows if rows is not None else release_rows(version)
    if rows is None:
        return [GateResult("release_built", False, f"release v{version} is not built — run `gj split`", "", True)]
    all_rows = rows["train"] + rows["validation"]
    events = RS.ReviewStore.default().events() if events is None else events
    infos = {r["id"]: RS.resolve(r, events) for r in all_rows}
    results = []

    def add(gid, passed, detail):
        g = cfg[gid]
        results.append(GateResult(gid, bool(passed), detail, " ".join(str(g.get("rationale", "")).split()), g.get("blocking", True)))

    # validation_strict
    from generation.validators.records import validate_example
    bad = [r["id"] for r in all_rows if not validate_example({k: v for k, v in r.items() if k not in ("review_status", "content_hash")},
                                                             strict=True).ok]
    add("validation_strict", not bad, f"{len(all_rows) - len(bad)}/{len(all_rows)} rows clean" + (f"; failing: {bad[:5]}" if bad else ""))

    # review_all_approved
    st = Counter(i["status"] for i in infos.values())
    approved = st.get("approved", 0)
    need = cfg["review_all_approved"]["min_approved_share"]
    add("review_all_approved", all_rows and _share(approved, len(all_rows)) >= need,
        f"{approved}/{len(all_rows)} approved ({dict(sorted(st.items()))})")

    # findings_acknowledged
    from .review import open_blocking_findings
    missing = []
    for r in all_rows:
        if infos[r["id"]]["status"] != "approved":
            continue
        rec = {k: v for k, v in r.items() if k not in ("review_status", "content_hash")}
        blocking = set(open_blocking_findings(rec, version))
        acked = set()
        for e in events:
            if e["example_id"] == r["id"] and e["content_hash"] == infos[r["id"]]["content_hash"] and e["action"] == "approve":
                acked |= set(e.get("acknowledged_findings") or [])
        if blocking - acked:
            missing.append(f"{r['id']}: {sorted(blocking - acked)}")
    add("findings_acknowledged", approved > 0 and not missing,
        "no approved rows yet" if approved == 0 else (f"{len(missing)} approved row(s) with unacknowledged findings: {missing[:3]}"
                                                      if missing else "all high findings on approved rows acknowledged"))

    # known_issues_closed
    from .audit import load_known_issues
    ids = {r["id"] for r in all_rows}
    open_ki = [k for k in load_known_issues(version) if k["status"] == "open" and k["severity"] in ("medium", "high")
               and ids & set(k["records"])]
    add("known_issues_closed", not open_ki, f"{len(open_ki)} open medium/high known issue(s) on released rows"
        + (f": {[k['id'] for k in open_ki][:10]}" if open_ki else ""))

    # reviewer_diversity
    approvers = Counter()
    for r in all_rows:
        if infos[r["id"]]["status"] != "approved":
            continue
        for e in events:
            if e["example_id"] == r["id"] and e["content_hash"] == infos[r["id"]]["content_hash"] and e["action"] == "approve":
                approvers[e["reviewer_id"]] += 1
    g = cfg["reviewer_diversity"]
    top = _share(max(approvers.values()), approved) if approvers and approved else 1.0
    add("reviewer_diversity", len(approvers) >= g["min_distinct_reviewers"] and top <= g["max_share_single_reviewer"],
        f"{len(approvers)} distinct approving reviewer(s); largest share {top:.0%}")

    # calibration_agreement
    from .review import load_manifest
    manifest = manifest if manifest is not None else load_manifest(version)
    g = cfg["calibration_agreement"]
    if not manifest:
        add("calibration_agreement", False, "no review manifest — run `gj review sample --write`")
    else:
        calib = set(manifest["calibration"]["items"])
        calib_ids = {it["example_id"] for it in manifest["items"] if it["review_item_id"] in calib}
        ag = RS.agreement(events, restrict_to=calib_ids)
        eligible = [p for p in ag["pairs"] if p["items"] >= g["min_shared_items"]]
        ok = bool(eligible) and all(p["decision_agreement"] >= g["min_decision_agreement"]
                                    and (p["decision_kappa"] or 0) >= g["min_decision_kappa"] for p in eligible)
        add("calibration_agreement", ok,
            f"{ag['items_with_2plus_reviewers']}/{len(calib_ids)} calibration items double-reviewed; "
            + (", ".join(f"{p['reviewers'][0]}~{p['reviewers'][1]} n={p['items']} agree={p['decision_agreement']} "
                         f"kappa={p['decision_kappa']}" for p in eligible) or "no reviewer pair with enough shared items"))

    # leakage
    from .leakage import build as leakage_build
    rep, summary, problems = leakage_build(version)
    add("leakage_hard_clean", not rep.hard and not problems,
        f"{len(rep.hard)} hard finding(s)" + (f"; metadata problems: {problems}" if problems else ""))
    meta_open = summary["open_dispositions"]
    from .leakage import load_eval_metadata
    meta, _ = load_eval_metadata()
    pending_rewrites = [o["eval"] for o in meta.get("template_overlaps") or [] if o["disposition"].startswith("rewrite_")]
    add("leakage_dispositions", meta_open == 0 and not pending_rewrites and not summary["unreviewed_auto_candidates"],
        f"{meta_open} overlap(s) without a disposition, {len(pending_rewrites)} decided rewrite(s) pending, "
        f"{len(summary['unreviewed_auto_candidates'])} unreviewed automated candidate(s)")

    # coverage_minimums (approved rows only)
    g = cfg["coverage_minimums"]
    appr = [r for r in all_rows if infos[r["id"]]["status"] == "approved"]
    appr_train = [r for r in rows["train"] if infos[r["id"]]["status"] == "approved"]
    by_tt = Counter(r["task_type"] for r in appr)
    from gjcore.schemas import OPERATION_SCHEMAS
    thin = {op: by_tt.get(op, 0) for op in OPERATION_SCHEMAS if by_tt.get(op, 0) < g["min_per_task_type"]}
    lang = Counter(r["language"] for r in appr)
    lang_bad = {k: round(_share(lang.get(k, 0), len(appr)), 2) for k, v in g["min_language_share"].items()
                if _share(lang.get(k, 0), len(appr)) < v}
    mixed = _share(sum(1 for r in appr if r["input_language"] == "mixed"), len(appr))
    risky = _share(sum(1 for r in appr if r["safety_category"] != "allowed"), len(appr))
    ok = (len(appr_train) >= g["min_approved_train"] and not thin and not lang_bad
          and mixed >= g["min_mixed_input_share"] and risky >= g["min_non_allowed_safety_share"])
    add("coverage_minimums", ok,
        f"approved train {len(appr_train)}/{g['min_approved_train']}; operations below {g['min_per_task_type']}: "
        f"{len(thin)}/{len(OPERATION_SCHEMAS)}; language shares below floor: {lang_bad or 'none'}; "
        f"mixed input {mixed:.0%}; non-allowed safety {risky:.0%}")

    # preference_minimums
    if purpose == "preference":
        g = cfg["preference_minimums"]
        modes = Counter(m for r in appr for c in r.get("contrastive") or [] for m in c["failure_modes"])
        from generation.validators.semantic import FAILURE_MODE_CODES
        low = {m: modes.get(m, 0) for m in FAILURE_MODE_CODES if modes.get(m, 0) < g["min_per_failure_mode"]}
        add("preference_minimums", not low, f"{len(low)} failure mode(s) below {g['min_per_failure_mode']} approved rejected outputs")

    # eval_readiness
    g = cfg["eval_readiness"]
    cases = [c for c, _ in load_eval_cases(repo_path(load_config("evaluation")["cases_dir"]))]
    from .leakage import _units
    units = _units(cases)
    # min_cases counts cases (steps of one case are correlated); the per-operation floor counts model calls
    per_op = Counter(u["task_type"] for u in units)
    thin_ops = sum(1 for op in OPERATION_SCHEMAS if per_op.get(op, 0) < g["min_cases_per_task_type"])
    ok = len(cases) >= g["min_cases"] and not thin_ops and not summary["eval_cases_without_metadata"]
    add("eval_readiness", ok, f"{len(cases)}/{g['min_cases']} cases ({len(units)} model calls); {thin_ops} operation(s) "
        f"below {g['min_cases_per_task_type']} model calls; {len(summary['eval_cases_without_metadata'])} without leakage metadata")

    # licensing_resolved
    lic = load_yaml(repo_path(cfg["licensing_resolved"]["file"])) or {}
    open_items = [i["id"] for i in lic.get("items") or [] if i.get("status") != "resolved"]
    add("licensing_resolved", not open_items, f"{len(open_items)} unresolved: {open_items}" if open_items else "all resolved")
    return results


def training_ready(results) -> bool:
    return all(r.passed for r in results if r.blocking)


def run(version=None, purpose="sft", as_json=False):
    version = version or versions()["dataset_version"]
    results = evaluate(version, purpose=purpose)
    ready = training_ready(results)
    if as_json:
        print(json.dumps({"dataset_version": version, "purpose": purpose, "training_ready": ready,
                          "gates": [r.to_dict() for r in results]}, ensure_ascii=False, indent=2))
    else:
        print(f"Release gates for v{version} ({purpose}): {'TRAINING_READY' if ready else 'NOT training_ready'} "
              f"({sum(r.passed for r in results)}/{len(results)} passed)\n")
        for r in results:
            print(f"  {'PASS' if r.passed else 'FAIL'}  {r.id:24} {r.detail}")
        print("\nThresholds and rationale: configs/release_gates.yaml")
    return 0 if ready else 1
