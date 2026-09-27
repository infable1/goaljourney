"""`gj validate`: schema + semantic + contrastive self-test + diversity over all raw examples,
plus structural validation of scenario seeds and evaluation cases."""
from collections import Counter

from gjcore import schemas
from gjcore.config import load_config
from gjcore.paths import repo_path, rel
from gjcore.records import flow_style_issues, load_examples, load_records
from generation.validators import semantic, similarity
from generation.validators.records import check_unique_ids, validate_example


def validate_examples(path=None, strict=None):
    cfg = load_config("dataset")
    path = repo_path(path or cfg["paths"]["raw_examples"])
    strict = cfg["validation"]["strict"] if strict is None else strict
    loaded = load_examples(path)
    records = [r for r, _ in loaded]
    src = {r.get("id"): rel(p) for r, p in loaded}
    reports = [validate_example(r, strict=strict) for r in records]

    dup_ids = check_unique_ids(records)
    lk = cfg["leakage"]
    near = similarity.pairwise_near_duplicates(
        [(r["id"], similarity.signature_text(r.get("input") or {})) for r in records if r.get("id")],
        lk["repetition_warning_threshold"], lk["shingle_size"])
    # Examples that share a scenario_group are expected to be similar.
    groups = {r.get("id"): r.get("scenario_group") for r in records}
    repetition = [p for p in near if groups.get(p[0]) != groups.get(p[1])]

    mode_total, mode_detected = Counter(), Counter()
    for rep in reports:
        for cr in rep.contrastive:
            for m in cr.failure_modes:
                mode_total[m] += 1
                if m in cr.detected_modes:
                    mode_detected[m] += 1

    style = [f"{rel(f)}:{no}: {msg}" for f in sorted(path.rglob("*.yaml")) for no, msg in flow_style_issues(f)]

    return {
        "path": rel(path),
        "examples": len(records),
        "style_errors": style,
        "valid": sum(r.ok for r in reports),
        "invalid": [{"id": r.id, "file": src.get(r.id), "errors": r.errors} for r in reports if not r.ok],
        "warnings": [{"id": r.id, "warnings": r.warnings} for r in reports if r.warnings],
        "duplicate_ids": dup_ids,
        "repetition_pairs": repetition,
        "contrastive": {
            "outputs": sum(len(r.contrastive) for r in reports),
            "by_failure_mode": {m: {"count": mode_total[m], "lint_detected": mode_detected[m],
                                    "always_detectable": m in semantic.ALWAYS_DETECTABLE}
                                for m in sorted(mode_total)},
        },
    }


def validate_scenarios(path="generation/scenarios"):
    loaded = load_records(repo_path(path), "scenarios")
    errors = []
    ids = Counter(r.get("id") for r, _ in loaded)
    for r, p in loaded:
        for e in schemas.validate("scenario", r):
            errors.append(f"{rel(p)} {r.get('id')}: {e}")
    errors += [f"duplicate scenario id {i}" for i, n in ids.items() if n > 1]
    return {"path": path, "scenarios": len(loaded), "errors": errors}


def print_example_summary(s, verbose=False):
    print(f"Examples: {s['examples']}  valid: {s['valid']}  invalid: {len(s['invalid'])}  ({s['path']})")
    for inv in s["invalid"]:
        print(f"  ✗ {inv['id']}  [{inv['file']}]")
        for e in inv["errors"]:
            print(f"      - {e}")
    if s["duplicate_ids"]:
        print(f"  ✗ duplicate ids: {s['duplicate_ids']}")
    for e in s["style_errors"]:
        print(f"  ✗ YAML style: {e}")
    n_warn = sum(len(w["warnings"]) for w in s["warnings"])
    print(f"Warnings: {n_warn} across {len(s['warnings'])} examples")
    if verbose:
        for w in s["warnings"]:
            for msg in w["warnings"]:
                print(f"  ! {w['id']}: {msg}")
    if s["repetition_pairs"]:
        print(f"Template repetition (near-duplicate inputs across scenario groups): {len(s['repetition_pairs'])}")
        for a, b, sim in s["repetition_pairs"]:
            print(f"  ~ {a} ~ {b}  jaccard={sim}")
    c = s["contrastive"]
    print(f"Contrastive outputs: {c['outputs']}")
    for m, v in c["by_failure_mode"].items():
        flag = "auto" if v["always_detectable"] else "human"
        print(f"  {m:34s} n={v['count']:<3d} lint-detected={v['lint_detected']:<3d} ({flag})")
