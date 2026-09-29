#!/usr/bin/env python3
"""GoalJourney dataset pipeline CLI.

    python scripts/gj.py validate            # schemas + semantic lint + contrastive self-test + eval cases
    python scripts/gj.py stats               # dataset distribution
    python scripts/gj.py coverage            # current pool vs. scale-up targets
    python scripts/gj.py generate ...        # synthetic candidates via a teacher LLM (needs credentials)
    python scripts/gj.py review sample|sample-status|list|show|template|approve|revise|reject|apply|history|stats|export|verify-log
    python scripts/gj.py audit               # heuristic audits (Problems 1-9) + known issues register
    python scripts/gj.py revisions check|sync|diff   # revision ledger vs. the base release (no silent edits)
    python scripts/gj.py leakage             # layered train/eval/seed leakage report
    python scripts/gj.py split               # immutable train/validation/test release + manifest
    python scripts/gj.py gates               # is the release training_ready? (configs/release_gates.yaml)
    python scripts/gj.py export --format sft|preference|eval
    python scripts/gj.py eval build-cases [--check]   # render evaluation/cases/v0.2.0 from evaluation/builders/
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
    from gjcore.paths import REPO_ROOT
    from gjcore.schemas import version_key
    ec = {}
    # every case set is validated: the current one and the frozen earlier versions
    for d in sorted((REPO_ROOT / "evaluation" / "cases").glob("v*"), key=lambda p: version_key(p.name[1:])):
        res = validate_cases(str(d))
        print_case_summary(res)
        ok &= not res["invalid"]
        ec[d.name] = res

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
    from generation.pipelines import review, sampling
    c = args.review_cmd
    if c == "sample":
        return sampling.run(write=args.write, check=args.check, as_json=args.json)
    if c == "sample-status":
        from generation.pipelines import sample_status
        return sample_status.run(write=args.write, check=args.check, as_json=args.json)
    if c == "list":
        return review.cmd_list(status=args.status, tier=args.tier, task_type=args.task_type, language=args.language,
                               manifest_only=args.manifest, as_json=args.json)
    if c == "show":
        return review.cmd_show(args.id, show_automated=args.show_automated)
    if c == "template":
        return review.cmd_template(args.id, out=args.out)
    if c in ("approve", "revise", "reject"):
        independent = None if args.independent_rating is None else args.independent_rating == "yes"
        return review.cmd_decide(c, args.id, args.reviewer, decision_file=args.from_file, rates=args.rate or [],
                                 overall=args.overall, notes=args.notes, issues=args.issue or [],
                                 acknowledge=args.acknowledge_findings, item_id=args.item, independent=independent)
    if c == "apply":
        return review.cmd_apply(args.file, reviewer=args.reviewer, acknowledge=args.acknowledge_findings)
    if c == "history":
        return review.cmd_history(args.id, diff=not args.no_diff)
    if c in ("stats", "status"):
        return review.cmd_stats(as_json=getattr(args, "json", False))
    if c == "export":
        return review.cmd_export(args.format, args.out, status=args.status, ids=args.id, manifest_only=args.manifest,
                                 with_automated=args.with_automated)
    if c == "verify-log":
        return review.cmd_verify_log()
    return 2


def cmd_audit(args):
    from generation.pipelines import audit
    return audit.run(write=args.write, as_json=args.json, record=args.record)


def cmd_revisions(args):
    from generation.pipelines import revisions
    return revisions.run(args.rev_cmd, version=args.version, example=getattr(args, "example", None))


def cmd_leakage(args):
    from generation.pipelines import leakage
    return leakage.run(as_json=args.json, distribution=args.distribution, out=args.out)


def cmd_gates(args):
    from generation.pipelines import gates
    return gates.run(version=args.version, purpose=args.purpose, as_json=args.json)


def cmd_split(args):
    from generation.pipelines.split import build_release
    return build_release(version=args.version, review_policy=args.review_policy, dry_run=args.dry_run)


def cmd_export(args):
    from generation.pipelines.export import export
    return export(fmt=args.format, version=args.version, out_dir=args.out, review_policy=args.review_policy,
                  allow_draft=args.allow_draft)


def cmd_eval(args):
    from evaluation.runners import runner
    if args.eval_cmd == "build-cases":
        from evaluation.builders import build
        return build.run(check=args.check)
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

    r = sub.add_parser("review", help="human review workflow (docs/HUMAN_REVIEW_GUIDE.md)")
    rs = r.add_subparsers(dest="review_cmd", required=True)
    rsa = rs.add_parser("sample", help="deterministic review sample -> review/review_manifest_v<ver>.json")
    rsa.add_argument("--write", action="store_true", help="write the manifest (refuses to change an existing one)")
    rsa.add_argument("--check", action="store_true", help="verify the committed manifest equals a fresh regeneration")
    rsa.add_argument("--json", action="store_true")
    rss = rs.add_parser("sample-status", help="the review sample in force at this version: per-item change, known "
                                              "issues and human status -> review/review_sample_status_v<ver>.json")
    rss.add_argument("--write", action="store_true")
    rss.add_argument("--check", action="store_true", help="verify the committed status file is current")
    rss.add_argument("--json", action="store_true")
    rl = rs.add_parser("list", help="examples with tier, required qualifications and status")
    rl.add_argument("--status", choices=["pending", "approved", "needs_revision", "rejected"])
    rl.add_argument("--tier", choices=["human_review_required", "expert_review_required"])
    rl.add_argument("--task-type")
    rl.add_argument("--language", choices=["ru", "en"])
    rl.add_argument("--manifest", action="store_true", help="only the review sample, in manifest order")
    rl.add_argument("--json", action="store_true")
    rsh = rs.add_parser("show", help="one example for review")
    rsh.add_argument("id")
    rsh.add_argument("--show-automated", action="store_true",
                     help="also show validator results, audit findings, known issues and author notes (after rating!)")
    rt = rs.add_parser("template", help="decision file (YAML) with the applicable rubric criteria")
    rt.add_argument("id")
    rt.add_argument("--out")
    for name, helptext in (("approve", "approve the current content"), ("revise", "request a revision"),
                           ("reject", "reject the current content")):
        d = rs.add_parser(name, help=helptext)
        d.add_argument("id")
        d.add_argument("--reviewer", required=True, help="your id in review/reviewers.yaml")
        d.add_argument("--from", dest="from_file", help="decision file from `gj review template`")
        d.add_argument("--rate", action="append", help="criterion=rating (repeatable)")
        d.add_argument("--overall", choices=["excellent", "acceptable", "needs_revision", "incorrect"])
        d.add_argument("--notes")
        d.add_argument("--issue", action="append", help="criterion:severity:description[:proposed fix] (repeatable)")
        d.add_argument("--item", help="review item id (defaults to the manifest's)")
        d.add_argument("--acknowledge-findings", action="store_true",
                       help="approve although high-severity findings are open (after reading them)")
        d.add_argument("--independent-rating", choices=["yes", "no"],
                       help="no = you changed a rating after reading automated findings or AI-copilot critique "
                            "(recorded as independent_rating: false)")
    ra = rs.add_parser("apply", help="record every filled entry of a review sheet")
    ra.add_argument("file")
    ra.add_argument("--reviewer", required=True)
    ra.add_argument("--acknowledge-findings", action="store_true")
    rh = rs.add_parser("history", help="decisions on an example and diffs between reviewed versions")
    rh.add_argument("id")
    rh.add_argument("--no-diff", action="store_true")
    rst = rs.add_parser("stats", help="status counts, reviewers, agreement, pipeline funnel")
    rst.add_argument("--json", action="store_true")
    rs.add_parser("status", help="alias of stats")
    rex = rs.add_parser("export", help="md reading packet | sheet (batch YAML) | json (statuses + events)")
    rex.add_argument("--format", required=True, choices=["md", "sheet", "json"])
    rex.add_argument("--out", required=True)
    rex.add_argument("--status", choices=["pending", "approved", "needs_revision", "rejected"])
    rex.add_argument("--id", action="append")
    rex.add_argument("--manifest", action="store_true", help="only the review sample, in manifest order")
    rex.add_argument("--with-automated", action="store_true", help="md only: include audit findings (breaks independence)")
    rs.add_parser("verify-log", help="check the review log hash chain and snapshots")
    r.set_defaults(func=cmd_review)

    au = sub.add_parser("audit", help="heuristic audits (Problems 1-9) + known issues register")
    au.add_argument("--write", action="store_true", help="write review/audit_findings_v<ver>.json")
    au.add_argument("--json", action="store_true")
    au.add_argument("--record", help="only findings for this example/case id (prefix match)")
    au.set_defaults(func=cmd_audit)

    rv = sub.add_parser("revisions", help="revision ledger of a dataset version (data/revisions/v<ver>.yaml)")
    rvs = rv.add_subparsers(dest="rev_cmd", required=True)
    rvs.add_parser("check", help="every difference from the base release is recorded (exit 1 if not)")
    rvs.add_parser("sync", help="fill computed fields (hashes, changed paths) and write snapshots")
    rvd = rvs.add_parser("diff", help="show the ledger entry and field-level diff for one example")
    rvd.add_argument("example")
    rv.add_argument("--version")
    rv.set_defaults(func=cmd_revisions)

    lk = sub.add_parser("leakage", help="layered leakage report (exits 1 on hard findings)")
    lk.add_argument("--json", action="store_true")
    lk.add_argument("--distribution", action="store_true", help="also print similarity distributions")
    lk.add_argument("--out", help="write the JSON report to this path")
    lk.set_defaults(func=cmd_leakage)

    gt = sub.add_parser("gates", help="release gates: is the release training_ready? (exit 1 if not)")
    gt.add_argument("--version")
    gt.add_argument("--purpose", choices=["sft", "preference"], default="sft")
    gt.add_argument("--json", action="store_true")
    gt.set_defaults(func=cmd_gates)

    sp = sub.add_parser("split", help="build an immutable train/validation/test release")
    sp.add_argument("--version", help="dataset version (default: configs/versions.yaml)")
    sp.add_argument("--review-policy", choices=["require_approved", "allow_pending"])
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_split)

    ex = sub.add_parser("export", help="export a release to training/eval formats")
    ex.add_argument("--format", required=True, choices=["sft", "preference", "eval"])
    ex.add_argument("--version")
    ex.add_argument("--out")
    ex.add_argument("--review-policy", choices=["require_approved", "allow_pending"], default="require_approved",
                    help="training formats: only currently approved rows (default) or all rows (draft only)")
    ex.add_argument("--allow-draft", action="store_true",
                    help="export although release gates fail; output is marked training_eligible: false")
    ex.set_defaults(func=cmd_export)

    e = sub.add_parser("eval", help="evaluation suite")
    es = e.add_subparsers(dest="eval_cmd", required=True)
    eb = es.add_parser("build-cases", help="render evaluation cases from evaluation/builders/ (v0.2.0)")
    eb.add_argument("--check", action="store_true", help="only report files that differ from the builder output")
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
    from generation.pipelines.review_store import ReviewError
    from generation.pipelines.revisions import RevisionError
    try:
        return args.func(args)
    except BrokenPipeError:
        # Output piped into a command that stopped reading early (e.g. `| head`): exit quietly.
        import os
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0
    except (RecordFileError, MissingCredentialsError, ProviderError, ReviewError, RevisionError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
