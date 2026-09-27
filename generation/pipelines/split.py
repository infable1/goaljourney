"""`gj split`: build an immutable, versioned dataset release.

Steps (the build aborts on any failure — nothing is written half-way):
  1. every example in the pool validates (schema + semantic + contrastive self-test), ids unique;
  2. evaluation cases validate (their reference outputs pass their own checks);
  3. selection by review policy: `approved` examples always; `pending` *authored* examples only under
     `allow_pending` (release marked draft_unreviewed); everything else (needs_revision, rejected) and
     unapproved generated candidates are excluded. Under allow_pending, `pending` includes content changed
     since a decision and approvals still awaiting an expert — they are released only as draft rows;
  4. leakage guard: any hard finding of the layered checks (exact, near-duplicate, lexical paraphrase,
     scenario group, seed id, decision pattern — see docs/LEAKAGE_CHECKS.md) aborts the build; multi-step
     evaluation cases are checked per step;
  4b. revision ledger: a version derived from an earlier release (data/revisions/v<version>.yaml) is built only
     if the ledger accounts for every change (`gj revisions check`); each revised row's manifest entry names
     its revision ids;
  5. deterministic group split: whole scenario groups go to train or validation, stratified by task type;
  6. files written to data/{train,validation,test}/goaljourney-v<version>.jsonl plus a manifest.
     release_status: draft_unreviewed (pending rows) | reviewed_not_training_ready (gates fail) |
     training_ready (all release gates pass, configs/release_gates.yaml).
     An existing version is never overwritten: identical data files are a no-op (the manifest is kept
     as built), different data fails.
"""
import hashlib
import math
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone

from gjcore.config import load_config, versions
from gjcore.io import canonical_json, dump_json, load_json, sha256_text
from gjcore.paths import REPO_ROOT, rel, repo_path
from gjcore.records import content_hash, load_eval_cases
from generation.validators import leakage as L
from generation.validators.records import check_unique_ids, validate_example

from .pool import load_pool, load_review_events, review_status

VOLATILE_MANIFEST_KEYS = ("created_at", "git_commit")


def release_paths(version):
    cfg = load_config("dataset")["paths"]
    name = f"goaljourney-v{version}"
    return {
        "train": repo_path(cfg["train"]) / f"{name}.jsonl",
        "validation": repo_path(cfg["validation"]) / f"{name}.jsonl",
        "test": repo_path(cfg["test"]) / f"{name}.jsonl",
        "manifest": repo_path(cfg["manifests"]) / f"{name}.json",
    }


def _git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True,
                              text=True, check=True).stdout.strip() or None
    except Exception:
        return None


def _group_rank(seed, group):
    return hashlib.sha256(f"{seed}:{group}".encode()).hexdigest()


def assign_splits(records, seed, fraction, min_stratum):
    """records: list of dicts with id, scenario_group, task_type. Returns {scenario_group: split}."""
    groups = defaultdict(list)
    for r in records:
        groups[r["scenario_group"]].append(r)
    strata = defaultdict(list)
    for g, recs in groups.items():
        stratum = Counter(r["task_type"] for r in recs).most_common(1)[0][0]
        strata[stratum].append(g)
    assignment = {}
    for stratum, gs in sorted(strata.items()):
        gs = sorted(gs, key=lambda g: _group_rank(seed, g))
        n_records = sum(len(groups[g]) for g in gs)
        n_val = max(1, math.floor(len(gs) * fraction)) if n_records >= min_stratum and len(gs) > 1 else 0
        for i, g in enumerate(gs):
            assignment[g] = "validation" if i < n_val else "train"
    return assignment


def _jsonl_text(rows):
    return "".join(canonical_json(r) + "\n" for r in rows)


def build_release(version=None, review_policy=None, dry_run=False):
    vers = versions()
    cfg = load_config("dataset")
    version = version or vers["dataset_version"]
    policy = review_policy or cfg["split"]["review_policy"]
    split_cfg, leak_cfg = cfg["split"], cfg["leakage"]

    pool = load_pool()
    records = [r for r, _, _ in pool]
    invalid = [(rep.id, rep.errors) for rep in (validate_example(r) for r in records) if not rep.ok]
    if invalid:
        print(f"✗ {len(invalid)} invalid example(s); run `gj validate`. First: {invalid[0]}")
        return 1
    dups = check_unique_ids(records)
    if dups:
        print(f"✗ duplicate example ids: {dups}")
        return 1

    from evaluation.runners.validate_cases import validate_cases
    ec = validate_cases()
    if ec["invalid"]:
        print(f"✗ {len(ec['invalid'])} invalid evaluation case(s); run `gj validate`.")
        return 1
    cases = [c for c, _ in load_eval_cases(repo_path(load_config("evaluation")["cases_dir"]))]

    events = load_review_events()
    selected, excluded = [], Counter()
    for rec, _, origin in pool:
        st = review_status(rec, events)
        if st == "approved" or (policy == "allow_pending" and origin == "authored" and st == "pending"):
            selected.append({**rec, "review_status": st, "content_hash": content_hash(rec)})
        else:
            excluded[f"{origin}/{st}"] += 1

    from .leakage import _units, load_eval_metadata, load_registry, load_seeds
    meta, meta_problems = load_eval_metadata()
    units = _units(cases)
    rep = L.run_checks(selected, units, leak_cfg, eval_meta=meta.get("cases") or {}, seeds=load_seeds(),
                       registry=load_registry())
    if rep.hard or meta_problems:
        print(f"✗ leakage: {len(rep.hard)} hard finding(s){'; metadata problems ' + str(meta_problems) if meta_problems else ''}:")
        for f in rep.hard:
            print(f"    [{f.layer}] {f.a} ~ {f.b} ({f.score}): {f.detail}")
        return 1

    from .revisions import check as revisions_check, ledger_path, load_ledger, revision_info
    ledger = load_ledger(version)
    rev_errors = revisions_check(version)[0] if ledger else []
    if rev_errors:
        print(f"✗ revision ledger: {len(rev_errors)} problem(s); run `gj revisions check`. First: {rev_errors[0]}")
        return 1
    rinfo = revision_info(version)

    assignment = assign_splits(selected, split_cfg["seed"], split_cfg["validation_fraction"],
                               split_cfg["min_stratum_size_for_validation"])
    train = sorted((r for r in selected if assignment[r["scenario_group"]] == "train"), key=lambda r: r["id"])
    val = sorted((r for r in selected if assignment[r["scenario_group"]] == "validation"), key=lambda r: r["id"])
    test = sorted(cases, key=lambda c: c["id"])
    overlap = {r["scenario_group"] for r in train} & {r["scenario_group"] for r in val}
    assert not overlap, f"scenario groups in both train and validation: {overlap}"

    paths = release_paths(version)
    texts = {"train": _jsonl_text(train), "validation": _jsonl_text(val), "test": _jsonl_text(test)}
    pending = sum(1 for r in selected if r["review_status"] != "approved")
    if pending:
        release_status, failing = "draft_unreviewed", None
    else:
        from .gates import evaluate, training_ready
        results = evaluate(version, rows={"train": train, "validation": val}, events=events)
        failing = [r.id for r in results if r.blocking and not r.passed]
        release_status = "training_ready" if training_ready(results) else "reviewed_not_training_ready"

    def dist(rows, key):
        return dict(sorted(Counter(r[key] for r in rows).items()))

    manifest = {
        "dataset": "GoalJourney Dataset",
        "dataset_version": version,
        "release_status": release_status,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "versions": vers,
        "review_policy": policy,
        "split_config": split_cfg,
        "leakage_check": {"layers": sorted({f.layer for f in rep.findings} | {"exact_input", "char_near_dup", "lexical_para"}),
                          "thresholds": rep.thresholds, "hard_findings": 0, "warnings": len(rep.warnings),
                          "max_scores": rep.max_scores},
        "failing_gates": failing,
        "revisions": ({"ledger": rel(ledger_path(version)), "base_version": ledger.get("base_version"),
                       "revised_examples": sum(1 for r in selected if r["id"] in rinfo),
                       "revision_entries": sum(len(i["revision_ids"]) for i in rinfo.values())} if ledger else None),
        "counts": {
            "train": len(train), "validation": len(val), "test_eval_cases": len(test), "test_eval_units": len(units),
            "train_contrastive_outputs": sum(len(r.get("contrastive") or []) for r in train),
            "pending_review": pending, "excluded": dict(excluded),
        },
        "distribution": {
            "train": {"task_type": dist(train, "task_type"), "language": dist(train, "language")},
            "validation": {"task_type": dist(val, "task_type"), "language": dist(val, "language")},
            "test": {"task_type": dist(units, "task_type"), "language": dist(test, "language"),
                     "case_type": dict(sorted(Counter(c.get("case_type", "atomic") for c in test).items()))},
        },
        "files": {split: {"path": rel(paths[split]), "sha256": sha256_text(texts[split]),
                          "records": {"train": len(train), "validation": len(val), "test": len(test)}[split]}
                  for split in ("train", "validation", "test")},
        "examples": [{"id": r["id"], "split": assignment[r["scenario_group"]], "scenario_group": r["scenario_group"],
                      "content_hash": r["content_hash"], "review_status": r["review_status"],
                      **({"revision_ids": rinfo[r["id"]]["revision_ids"],
                          "previous_content_hash": rinfo[r["id"]]["previous_content_hash"]} if r["id"] in rinfo else {})}
                     for r in sorted(selected, key=lambda r: r["id"])],
    }

    print(f"Release v{version} ({release_status}, policy={policy}): "
          f"train={len(train)} validation={len(val)} test={len(test)} excluded={dict(excluded) or 0}"
          + (f"; leakage warnings {len(rep.warnings)} (see `gj leakage`)" if rep.warnings else ""))
    if dry_run:
        print("(dry run — nothing written)")
        return 0

    existing = [p for p in paths.values() if p.exists()]
    if existing:
        same_data = all(paths[s].exists() and paths[s].read_text(encoding="utf-8") == texts[s] for s in texts)
        if same_data:
            note = ""
            if paths["manifest"].exists():
                old = {k: v for k, v in load_json(paths["manifest"]).items() if k not in VOLATILE_MANIFEST_KEYS}
                new = {k: v for k, v in manifest.items() if k not in VOLATILE_MANIFEST_KEYS}
                diff = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
                if diff:
                    note = (f" The stored manifest was built by an earlier pipeline and differs in {diff}; it is kept as "
                            f"built (releases are immutable). `gj gates` reports the live state.")
            print(f"Release v{version} already exists with identical data — nothing to do.{note}")
            return 0
        print(f"✗ release v{version} already exists with different content ({', '.join(rel(p) for p in existing)}). "
              f"Releases are immutable: bump dataset_version in configs/versions.yaml.")
        return 1

    for split, text in texts.items():
        paths[split].parent.mkdir(parents=True, exist_ok=True)
        paths[split].write_text(text, encoding="utf-8")
    dump_json(manifest, paths["manifest"])
    print(f"Wrote {', '.join(rel(p) for p in paths.values())}")
    return 0
