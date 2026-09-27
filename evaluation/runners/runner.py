"""Evaluation runner: predict -> score -> report (automated metrics only) + human review sheets.

Predictors:
  reference  the cases' own reference outputs (sanity: every check must pass)
  naive      evaluation/runners/baselines.py (sanity: checks must discriminate)
  model      any provider (configs/evaluation.yaml), prompted exactly like SFT export
"""
import json
from datetime import datetime, timezone

import yaml

from gjcore.config import load_config, versions
from gjcore.io import dump_json, load_yaml, read_jsonl, write_jsonl
from gjcore.paths import EVALUATION_DIR, rel, repo_path
from gjcore.prompting import prompt_messages
from gjcore.records import load_eval_cases
from evaluation.metrics.scoring import aggregate, extract_json, score_case

from .baselines import naive_output


def _cases(cases_dir=None):
    cfg = load_config("evaluation")
    return [c for c, _ in load_eval_cases(repo_path(cases_dir or cfg["cases_dir"]))]


def _predict(predictor, cases, provider=None, model=None):
    preds = []
    if predictor == "model":
        from generation.generators.providers import ProviderError, make_provider
        prov = make_provider(provider, model, config_name="evaluation")
    for case in cases:
        row = {"case_id": case["id"], "predictor": predictor}
        if predictor == "reference":
            row["raw"] = json.dumps(case["reference_output"], ensure_ascii=False) if "reference_output" in case else None
        elif predictor == "naive":
            row["raw"] = json.dumps(naive_output(case), ensure_ascii=False)
        else:
            system, user = prompt_messages(case["input"])
            try:
                row["raw"] = prov.complete(system["content"], user["content"])
            except ProviderError as e:
                row["raw"], row["error"] = None, str(e)
            row["model"] = prov.describe()
        preds.append(row)
    return preds


def score_predictions(preds, cases):
    by_id = {p["case_id"]: p for p in preds}
    scored = []
    for case in cases:
        p = by_id.get(case["id"])
        if p is None or p.get("raw") is None:
            scored.append(score_case(case, None, parse_error=(p or {}).get("error") or "no prediction"))
            continue
        output, err = extract_json(p["raw"])
        scored.append(score_case(case, output, parse_error=err))
    return scored, aggregate(scored)


def _write_report(run_id, predictor, scored, agg, out_dir, meta):
    out = repo_path(out_dir or load_config("evaluation")["reports_dir"]) / run_id
    report = {"run_id": run_id, "predictor": predictor, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "versions": versions(), **meta, "summary": agg, "cases": scored,
              "note": "Automated metrics only. Human review is reported separately; there is no overall score by design."}
    dump_json(report, out / "report.json")
    lines = [f"# Evaluation report — {run_id}", "", f"Predictor: `{predictor}`  ",
             f"Evaluation version: {versions()['evaluation_version']}  ",
             f"Cases: {agg['cases']} (passing every check: {agg['cases_passing_all_checks']})", "",
             "Automated metrics only; human review is separate. No overall score by design.", "",
             "## Metrics", "", "| metric | value | direction | bad / total | failed checks | cases |", "|---|---|---|---|---|---|"]
    for name, m in agg["metrics"].items():
        val = "n/a" if m["value"] is None else f"{m['value']:.3f}"
        lines.append(f"| {name} | {val} | {m['direction'].replace('_', ' ')} | {m['numerator_bad']} / {m['denominator']} | "
                     f"{m['failed_checks']} / {m['checks']} | {m['cases']} |")
    lines += ["", "## Dimensions (check pass rate)", "", "| dimension | pass rate | checks | cases |", "|---|---|---|---|"]
    for name, d in agg["dimensions"].items():
        lines.append(f"| {name} | {d['check_pass_rate']:.3f} | {d['checks']} | {d['cases']} |")
    failures = [(s["case_id"], c) for s in scored for c in s["checks"] if not c["passed"]]
    lines += ["", f"## Failed checks ({len(failures)})", ""]
    for cid, c in failures:
        lines.append(f"- `{cid}` {c['check']} → {c['metric']}: {c['detail'] or 'failed'}")
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _print_summary(agg, out):
    print(f"Cases: {agg['cases']}  passing all checks: {agg['cases_passing_all_checks']}")
    for name, m in agg["metrics"].items():
        val = "n/a" if m["value"] is None else f"{m['value']:.3f}"
        print(f"  {name:32s} {val:>6s}  ({m['direction'].replace('_', ' ')}; failed checks {m['failed_checks']}/{m['checks']})")
    print(f"Report: {rel(out / 'report.md')}")


def run(predictor, provider=None, model=None, cases_dir=None, out_dir=None, limit=None):
    cases = _cases(cases_dir)[: limit or None]
    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{predictor}"
    preds = _predict(predictor, cases, provider, model)
    scored, agg = score_predictions(preds, cases)
    out = _write_report(run_id, predictor, scored, agg, out_dir, {"predictions_file": "predictions.jsonl"})
    write_jsonl(preds, out / "predictions.jsonl")
    _print_summary(agg, out)
    return 0


def score_file(predictions, cases_dir=None, out_dir=None):
    preds = read_jsonl(repo_path(predictions))
    cases = _cases(cases_dir)
    scored, agg = score_predictions(preds, cases)
    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-scored"
    out = _write_report(run_id, "external", scored, agg, out_dir, {"predictions_file": rel(repo_path(predictions))})
    _print_summary(agg, out)
    return 0


def review_sheet(predictions, cases_dir=None, out=None):
    """YAML sheet for human reviewers of model outputs (model_output_rubric.yaml)."""
    rubric = load_yaml(EVALUATION_DIR / "rubrics" / "model_output_rubric.yaml")
    preds = {p["case_id"]: p for p in read_jsonl(repo_path(predictions))}
    entries = []
    for case in _cases(cases_dir):
        p = preds.get(case["id"]) or {}
        output, err = extract_json(p.get("raw"))
        entries.append({"case_id": case["id"], "title": case.get("title"), "language": case["language"],
                        "human_review_focus": case["human_review_focus"],
                        "user_messages": [m["content"] for m in case["input"].get("conversation", []) if m["role"] == "user"],
                        "model_output": output if output is not None else (p.get("raw") or err),
                        "scores": {d: None for d in case["dimensions"] if d in rubric["dimensions"]},
                        "notes": ""})
    path = repo_path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Human review of model outputs — score 1–4 per evaluation/rubrics/model_output_rubric.yaml.\n"
                    "# Human scores are reported separately from automated metrics.\n"
                    + yaml.safe_dump({"entries": entries}, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
    print(f"Wrote review sheet for {len(entries)} case(s) -> {rel(path)}")
    return 0
