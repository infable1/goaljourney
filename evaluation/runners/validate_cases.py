"""Structural validation of evaluation cases + self-test of their checks on reference outputs."""
from collections import Counter

from gjcore import schemas
from gjcore.config import load_config, versions
from gjcore.paths import rel, repo_path
from gjcore.records import flow_style_issues, load_eval_cases
from evaluation.metrics.checks import check_spec_errors
from evaluation.metrics.scoring import score_case


def validate_cases(cases_dir=None):
    cfg = load_config("evaluation")
    cases_dir = repo_path(cases_dir or cfg["cases_dir"])
    loaded = load_eval_cases(cases_dir)
    ev_version = versions()["evaluation_version"]
    invalid, dims, with_ref = [], Counter(), 0
    ids = Counter(c.get("id") for c, _ in loaded)
    for case, path in loaded:
        errs = [f"ENVELOPE {e}" for e in schemas.validate("eval_case", case)]
        if case.get("eval_version") != ev_version:
            errs.append(f"eval_version {case.get('eval_version')!r} != {ev_version!r}")
        if (case.get("input") or {}).get("operation") != case.get("task_type"):
            errs.append("input.operation != task_type")
        for chk in case.get("checks", []):
            errs += check_spec_errors(chk)
        if ids[case.get("id")] > 1:
            errs.append("duplicate case id")
        if "reference_output" in case and not errs:
            with_ref += 1
            scored = score_case(case, case["reference_output"])
            if not scored["schema_ok"]:
                errs += [f"REFERENCE schema: {e}" for e in scored["schema_errors"]]
            for r in scored["checks"]:
                if not r["passed"]:
                    errs.append(f"REFERENCE fails its own check {r['check']}/{r['metric']}: {r['detail']}")
        for d in case.get("dimensions", []):
            dims[d] += 1
        if errs:
            invalid.append({"id": case.get("id"), "file": rel(path), "errors": errs})
    style = [f"{rel(f)}:{no}: {msg}" for f in sorted(cases_dir.rglob("*.yaml")) for no, msg in flow_style_issues(f)]
    if style:
        invalid.append({"id": "<yaml style>", "file": rel(cases_dir), "errors": style})
    return {
        "path": rel(cases_dir),
        "cases": len(loaded),
        "with_reference": with_ref,
        "invalid": invalid,
        "dimensions": dict(sorted(dims.items())),
        "checks": sum(len(c.get("checks", [])) for c, _ in loaded),
    }


def print_case_summary(s):
    print(f"Cases: {s['cases']}  checks: {s['checks']}  with reference output: {s['with_reference']}  "
          f"invalid: {len(s['invalid'])}  ({s['path']})")
    for inv in s["invalid"]:
        print(f"  ✗ {inv['id']}  [{inv['file']}]")
        for e in inv["errors"]:
            print(f"      - {e}")
    print("Dimension coverage: " + ", ".join(f"{k}={v}" for k, v in s["dimensions"].items()))
