"""Structural validation of evaluation cases + self-test of their checks on reference outputs.

Every unit (an atomic case, or one step of a composite/longitudinal case) is checked:
input.operation matches its task_type, every check is well-formed, the request side passes
`lint_input` for the case's schema version, and a reference output (when present) passes every
check of its own unit. The expected `eval_version` is the version in the directory name
(evaluation/cases/v<version>/), so older case sets keep validating after a version bump.
"""
import re
from collections import Counter

from gjcore import schemas
from gjcore.config import load_config, versions
from gjcore.paths import rel, repo_path
from gjcore.records import flow_style_issues, load_eval_cases
from evaluation.metrics.checks import check_spec_errors
from evaluation.metrics.scoring import expand_units, score_case
from generation.validators import semantic


def _dir_version(path):
    m = re.search(r"v(\d+\.\d+\.\d+)$", str(path))
    return m.group(1) if m else versions()["evaluation_version"]


def validate_cases(cases_dir=None):
    cfg = load_config("evaluation")
    cases_dir = repo_path(cases_dir or cfg["cases_dir"])
    loaded = load_eval_cases(cases_dir)
    ev_version = _dir_version(cases_dir)
    invalid, dims, with_ref, n_units, n_checks = [], Counter(), 0, 0, 0
    types = Counter()
    ids = Counter(c.get("id") for c, _ in loaded)
    for case, path in loaded:
        version = case.get("schema_version", "0.1.0")
        if version not in schemas.available_versions():
            invalid.append({"id": case.get("id"), "file": rel(path), "errors": [f"schema_version {version!r} unknown"]})
            continue
        errs = [f"ENVELOPE {e}" for e in schemas.validate("eval_case", case, version)]
        if case.get("eval_version") != ev_version:
            errs.append(f"eval_version {case.get('eval_version')!r} != {ev_version!r}")
        if ids[case.get("id")] > 1:
            errs.append("duplicate case id")
        if errs:
            invalid.append({"id": case.get("id"), "file": rel(path), "errors": errs})
            continue
        units = expand_units(case)
        step_ids = [u["step_id"] for u in units if u["step_id"]]
        if len(step_ids) != len(set(step_ids)):
            errs.append("duplicate step ids")
        types[case.get("case_type", "atomic")] += 1
        for unit in units:
            tag = f"[{unit['step_id']}] " if unit["step_id"] else ""
            n_units += 1
            n_checks += len(unit["checks"])
            if (unit.get("input") or {}).get("operation") != unit.get("task_type"):
                errs.append(f"{tag}input.operation != task_type")
            for issue in semantic.lint_input(unit["input"], version):
                if issue.level == "error":
                    errs.append(f"{tag}INPUT {issue}")
            for chk in unit["checks"]:
                errs += [f"{tag}{e}" for e in check_spec_errors(chk)]
            if "reference_output" in unit and not errs:
                with_ref += 1
                scored = score_case(unit, unit["reference_output"])
                if not scored["schema_ok"]:
                    errs += [f"{tag}REFERENCE schema: {e}" for e in scored["schema_errors"]]
                for r in scored["checks"]:
                    if not r["passed"]:
                        errs.append(f"{tag}REFERENCE fails its own check {r['check']}/{r['metric']}: {r['detail']}")
        for d in case.get("dimensions", []):
            dims[d] += 1
        if errs:
            invalid.append({"id": case.get("id"), "file": rel(path), "errors": errs})
    style = [f"{rel(f)}:{no}: {msg}" for f in sorted(cases_dir.rglob("*.yaml")) for no, msg in flow_style_issues(f)]
    if style:
        invalid.append({"id": "<yaml style>", "file": rel(cases_dir), "errors": style})
    return {
        "path": rel(cases_dir),
        "eval_version": ev_version,
        "cases": len(loaded),
        "units": n_units,
        "case_types": dict(sorted(types.items())),
        "with_reference": with_ref,
        "invalid": invalid,
        "dimensions": dict(sorted(dims.items())),
        "checks": n_checks,
    }


def print_case_summary(s):
    print(f"Cases: {s['cases']} ({', '.join(f'{k}={v}' for k, v in s['case_types'].items())})  model calls: {s['units']}  "
          f"checks: {s['checks']}  units with reference output: {s['with_reference']}  invalid: {len(s['invalid'])}  ({s['path']})")
    for inv in s["invalid"]:
        print(f"  ✗ {inv['id']}  [{inv['file']}]")
        for e in inv["errors"]:
            print(f"      - {e}")
    print("Dimension coverage: " + ", ".join(f"{k}={v}" for k, v in s["dimensions"].items()))
