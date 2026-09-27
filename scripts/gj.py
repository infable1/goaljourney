#!/usr/bin/env python3
"""GoalJourney dataset pipeline CLI.

    python scripts/gj.py validate            # schemas + semantic lint + contrastive self-test + eval cases
    python scripts/gj.py stats               # dataset distribution
    python scripts/gj.py coverage            # current pool vs. scale-up targets
    python scripts/gj.py generate ...        # synthetic candidates via a teacher LLM (needs credentials)
    python scripts/gj.py review export|apply|status
    python scripts/gj.py split               # immutable train/validation/test release + manifest
    python scripts/gj.py export --format sft|preference|eval
    python scripts/gj.py eval run --predictor reference|naive|model
    python scripts/gj.py eval score --predictions file.jsonl
    python scripts/gj.py eval review-sheet --predictions file.jsonl

Every command exits non-zero on failure so it can gate CI.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def cmd_validate(args):
    from generation.pipelines.validate import print_example_summary, validate_examples, validate_scenarios
    from evaluation.runners.validate_cases import print_case_summary, validate_cases

    ok = True
    s = validate_examples(args.path, strict=args.strict or None)
    print("== Training examples ==")
    print_example_summary(s, verbose=args.verbose)
    ok &= not s["invalid"] and not s["duplicate_ids"] and not s["style_errors"]

    print("\n== Scenario seeds ==")
    sc = validate_scenarios()
    print(f"Scenarios: {sc['scenarios']}  errors: {len(sc['errors'])}")
    for e in sc["errors"]:
        print(f"  ✗ {e}")
    ok &= not sc["errors"]

    print("\n== Evaluation cases ==")
    ec = validate_cases()
    print_case_summary(ec)
    ok &= not ec["invalid"]

    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps({"examples": s, "scenarios": sc, "eval_cases": ec},
                                                ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nReport written to {args.report}")
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def cmd_stats(args):
    from generation.pipelines.stats import compute_stats, print_stats
    stats = compute_stats(args.path)
    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        print_stats(stats)
    return 0


def cmd_coverage(args):
    from generation.pipelines.coverage import coverage_report, print_coverage
    rep = coverage_report(args.target_total)
    print_coverage(rep)
    return 0


def cmd_generate(args):
    from generation.pipelines.generate import run_generation
    return run_generation(
        scenarios_path=args.scenarios, scenario_ids=args.scenario, task_types=args.task_type,
        limit=args.limit, provider_name=args.provider, model=args.model, dry_run=args.dry_run,
        with_contrastive=args.with_contrastive, run_id=args.run_id,
    )


def cmd_review(args):
    from generation.pipelines import review
    if args.review_cmd == "export":
        return review.export_sheet(args.out, status=args.status, ids=args.id)
    if args.review_cmd == "apply":
        return review.apply_reviews(args.file, reviewer=args.reviewer)
    if args.review_cmd == "status":
        return review.print_status()
    return 2


def cmd_split(args):
    from generation.pipelines.split import build_release
    return build_release(version=args.version, review_policy=args.review_policy, dry_run=args.dry_run)


def cmd_export(args):
    from generation.pipelines.export import export
    return export(fmt=args.format, version=args.version, out_dir=args.out)


def cmd_eval(args):
    from evaluation.runners import runner
    if args.eval_cmd == "run":
        return runner.run(predictor=args.predictor, provider=args.provider, model=args.model,
                          cases_dir=args.cases, out_dir=args.out, limit=args.limit)
    if args.eval_cmd == "score":
        return runner.score_file(args.predictions, cases_dir=args.cases, out_dir=args.out)
    if args.eval_cmd == "review-sheet":
        return runner.review_sheet(args.predictions, cases_dir=args.cases, out=args.out)
    return 2


def main(argv=None):
    p = argparse.ArgumentParser(prog="gj", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="validate examples, scenarios and evaluation cases")
    v.add_argument("--path", help="examples directory (default: data/raw/examples)")
    v.add_argument("--strict", action="store_true", help="treat semantic warnings as errors")
    v.add_argument("--verbose", "-v", action="store_true", help="print every warning")
    v.add_argument("--report", help="write a JSON report to this path")
    v.set_defaults(func=cmd_validate)

    s = sub.add_parser("stats", help="dataset distribution statistics")
    s.add_argument("--path")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_stats)

    c = sub.add_parser("coverage", help="compare the pool with configs/coverage_targets.yaml")
    c.add_argument("--target-total", type=int, default=None)
    c.set_defaults(func=cmd_coverage)

    g = sub.add_parser("generate", help="generate synthetic candidates with a teacher LLM")
    g.add_argument("--scenarios", default="generation/scenarios")
    g.add_argument("--scenario", action="append", help="scenario id (repeatable); default: all")
    g.add_argument("--task-type", action="append", help="operation (repeatable); default: scenario's list")
    g.add_argument("--limit", type=int, default=5, help="max candidates this run (hard-capped by config)")
    g.add_argument("--provider", help="anthropic | openai_compatible | replay (default from config)")
    g.add_argument("--model")
    g.add_argument("--with-contrastive", action="store_true", help="also generate a rejected output per candidate")
    g.add_argument("--dry-run", action="store_true", help="render prompts only; no API calls, no credentials needed")
    g.add_argument("--run-id")
    g.set_defaults(func=cmd_generate)

    r = sub.add_parser("review", help="human review workflow")
    rs = r.add_subparsers(dest="review_cmd", required=True)
    re_ = rs.add_parser("export", help="write a review sheet (YAML) for pending examples")
    re_.add_argument("--out", required=True)
    re_.add_argument("--status", default="pending", choices=["pending", "stale", "all"])
    re_.add_argument("--id", action="append")
    ra = rs.add_parser("apply", help="append a filled review sheet to the review log")
    ra.add_argument("file")
    ra.add_argument("--reviewer", required=True)
    rs.add_parser("status", help="review status per example")
    r.set_defaults(func=cmd_review)

    sp = sub.add_parser("split", help="build an immutable train/validation/test release")
    sp.add_argument("--version", help="dataset version (default: configs/versions.yaml)")
    sp.add_argument("--review-policy", choices=["require_approved", "allow_pending"])
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_split)

    ex = sub.add_parser("export", help="export a release to training/eval formats")
    ex.add_argument("--format", required=True, choices=["sft", "preference", "eval"])
    ex.add_argument("--version")
    ex.add_argument("--out")
    ex.set_defaults(func=cmd_export)

    e = sub.add_parser("eval", help="evaluation suite")
    es = e.add_subparsers(dest="eval_cmd", required=True)
    er = es.add_parser("run", help="produce predictions with a predictor and score them")
    er.add_argument("--predictor", required=True, choices=["reference", "naive", "model"])
    er.add_argument("--provider")
    er.add_argument("--model")
    er.add_argument("--cases")
    er.add_argument("--out")
    er.add_argument("--limit", type=int)
    esc = es.add_parser("score", help="score an existing predictions JSONL")
    esc.add_argument("--predictions", required=True)
    esc.add_argument("--cases")
    esc.add_argument("--out")
    erv = es.add_parser("review-sheet", help="human review sheet for model outputs")
    erv.add_argument("--predictions", required=True)
    erv.add_argument("--cases")
    erv.add_argument("--out", required=True)
    e.set_defaults(func=cmd_eval)

    args = p.parse_args(argv)
    from gjcore.env import MissingCredentialsError
    from gjcore.records import RecordFileError
    from generation.generators.providers import ProviderError
    try:
        return args.func(args)
    except (RecordFileError, MissingCredentialsError, ProviderError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
