"""Human review workflow.

1. `gj review export --out sheet.yaml` writes a YAML sheet: one entry per example with a readable
   rendering, the content hash at export time, and empty rubric fields.
2. A reviewer fills in decision / scores / notes.
3. `gj review apply sheet.yaml --reviewer NAME` validates the sheet against the rubric's acceptance
   rule and appends records to data/reviewed/reviews.jsonl (append-only). An entry whose example
   changed after export is refused (its hash no longer matches).
"""
from collections import Counter
from datetime import date

import yaml

from gjcore import schemas
from gjcore.config import load_config
from gjcore.io import append_jsonl, load_yaml
from gjcore.paths import EVALUATION_DIR, repo_path
from gjcore.records import content_hash

from .pool import load_pool, load_review_log, review_status

RUBRIC_PATH = EVALUATION_DIR / "rubrics" / "dataset_quality_rubric.yaml"


def _applicable(criteria, record):
    out = []
    for name, spec in criteria.items():
        applies = spec.get("applies_to", "all")
        if applies == "all" or (applies == "examples_with_contrastive" and record.get("contrastive")) \
                or (isinstance(applies, list) and record.get("task_type") in applies):
            out.append(name)
    return out


def export_sheet(out, status="pending", ids=None):
    rubric = load_yaml(RUBRIC_PATH)
    log = load_review_log()
    entries = []
    for rec, path, origin in load_pool():
        st = review_status(rec, log)
        if ids and rec["id"] not in ids:
            continue
        if not ids and status != "all" and st != status:
            continue
        crit = _applicable(rubric["criteria"], rec)
        entries.append({
            "example_id": rec["id"],
            "content_hash": content_hash(rec),
            "origin": origin,
            "current_status": st,
            "task_type": rec["task_type"],
            "language": rec["language"],
            "safety_category": rec["safety_category"],
            "input": rec["input"],
            "expected_output": rec["expected_output"],
            "contrastive": [{"id": c["id"], "failure_modes": c["failure_modes"], "critique": c["critique"]}
                            for c in rec.get("contrastive") or []],
            "review": {"decision": None, "scores": {c: None for c in crit}, "notes": ""},
        })
    header = (f"# Review sheet — fill in review.decision (approved | rejected | needs_revision), scores (1–4) and notes.\n"
              f"# Rubric: evaluation/rubrics/dataset_quality_rubric.yaml. Approval requires every listed score >= "
              f"{rubric['acceptance']['min_score']} and {rubric['acceptance']['hard_gates']} == 4.\n")
    path = repo_path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + yaml.safe_dump({"entries": entries}, allow_unicode=True, sort_keys=False, width=110),
                    encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {out}")
    return 0


def check_acceptance(scores: dict, rubric=None):
    rubric = rubric or load_yaml(RUBRIC_PATH)
    acc = rubric["acceptance"]
    problems = []
    for name, score in scores.items():
        if score is None:
            continue
        if name in acc["hard_gates"] and score != 4:
            problems.append(f"hard gate {name} must be 4 (got {score})")
        elif score < acc["min_score"]:
            problems.append(f"{name} below {acc['min_score']} (got {score})")
    return problems


def apply_reviews(file, reviewer):
    sheet = load_yaml(repo_path(file))
    rubric = load_yaml(RUBRIC_PATH)
    pool = {rec["id"]: rec for rec, _, _ in load_pool()}
    log_path = repo_path(load_config("dataset")["paths"]["review_log"])
    applied, errors = 0, []
    for entry in sheet.get("entries", []):
        rid, rev = entry["example_id"], entry.get("review") or {}
        if not rev.get("decision"):
            continue
        rec = pool.get(rid)
        if rec is None:
            errors.append(f"{rid}: not in the pool")
            continue
        if content_hash(rec) != entry["content_hash"]:
            errors.append(f"{rid}: example changed since the sheet was exported — re-export and review again")
            continue
        applicable = set(_applicable(rubric["criteria"], rec))
        scores = {k: v for k, v in (rev.get("scores") or {}).items() if k in applicable}
        if rev["decision"] == "approved":
            missing = [c for c in applicable if scores.get(c) is None]
            if missing:
                errors.append(f"{rid}: approval needs scores for {missing}")
                continue
            problems = check_acceptance(scores, rubric)
            if problems:
                errors.append(f"{rid}: cannot approve — {'; '.join(problems)}")
                continue
        record = {"example_id": rid, "content_hash": entry["content_hash"], "reviewer": reviewer,
                  "reviewed_at": date.today().isoformat(), "decision": rev["decision"],
                  "scores": scores, "notes": rev.get("notes") or ""}
        errs = schemas.validate("review_record", record)
        if errs:
            errors.append(f"{rid}: invalid review record: {errs}")
            continue
        append_jsonl(record, log_path)
        applied += 1
    print(f"Applied {applied} review(s) to {log_path.name}")
    for e in errors:
        print(f"  ✗ {e}")
    return 1 if errors else 0


def status_counts():
    log = load_review_log()
    return Counter((origin, review_status(rec, log)) for rec, _, origin in load_pool())


def print_status():
    counts = status_counts()
    if not counts:
        print("Pool is empty.")
    for (origin, st), n in sorted(counts.items()):
        print(f"  {origin:10s} {st:15s} {n}")
    return 0
