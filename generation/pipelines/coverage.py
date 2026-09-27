"""`gj coverage`: where the pool stands against the scale-up targets, and which seed scenarios
can fill each gap. Guides *what* to generate next instead of generating more of the same."""
from collections import Counter

from gjcore.config import load_config
from gjcore.paths import repo_path
from gjcore.records import load_records
from gjcore import schemas

from .pool import load_pool


def coverage_report(target_total=None):
    targets = load_config("coverage_targets")
    total = target_total or targets["target_total"]
    pool = [r for r, _, _ in load_pool()]
    n = len(pool) or 1
    scenarios = [s for s, _ in load_records(repo_path("generation/scenarios"), "scenarios")]
    by_op = Counter(r["task_type"] for r in pool)
    rows = []
    for op, share in targets["task_type_share"].items():
        want = round(total * share)
        seeds = [s["id"] for s in scenarios if op in s["task_types"]]
        rows.append({"task_type": op, "have": by_op.get(op, 0), "target": want,
                     "gap": max(0, want - by_op.get(op, 0)), "seed_scenarios": len(seeds)})
    modes = Counter(m for r in pool for c in r.get("contrastive") or [] for m in c["failure_modes"])
    all_modes = schemas.validator("common").schema["$defs"]["failure_mode"]["enum"]
    domains = Counter(r["domain"] for r in pool)
    shares = {
        "mixed_input_language": sum(r["input_language"] == "mixed" for r in pool) / n,
        "non_allowed_safety": sum(r["safety_category"] != "allowed" for r in pool) / n,
        "with_contrastive": sum(bool(r.get("contrastive")) for r in pool) / n,
        "tiny_goal": sum(r["goal_size"] == "tiny" for r in pool) / n,
    }
    return {
        "pool": len(pool), "target_total": total, "task_types": rows,
        "language": dict(Counter(r["language"] for r in pool)), "language_target": targets["language_share"],
        "shares": {k: {"have": round(v, 3), "min": targets["min_share"][k]} for k, v in shares.items()},
        "domains_below_min": {d: domains.get(d, 0) for d in schemas.validator("common").schema["$defs"]["domain"]["enum"]
                              if domains.get(d, 0) < targets["min_per_domain"]},
        "failure_modes_below_min": {m: modes.get(m, 0) for m in all_modes if modes.get(m, 0) < targets["min_per_failure_mode"]},
    }


def print_coverage(rep):
    print(f"Pool: {rep['pool']} examples; target: {rep['target_total']}")
    print(f"\n{'task_type':30s} {'have':>5s} {'target':>7s} {'gap':>5s} {'seeds':>6s}")
    for r in rep["task_types"]:
        print(f"{r['task_type']:30s} {r['have']:5d} {r['target']:7d} {r['gap']:5d} {r['seed_scenarios']:6d}")
    print(f"\nlanguage: {rep['language']} (target shares {rep['language_target']})")
    for k, v in rep["shares"].items():
        flag = "ok " if v["have"] >= v["min"] else "LOW"
        print(f"  [{flag}] {k:22s} {v['have']:.1%} (min {v['min']:.0%})")
    print(f"\nDomains below minimum ({len(rep['domains_below_min'])}): " +
          ", ".join(f"{d}={c}" for d, c in rep["domains_below_min"].items()))
    print(f"Failure modes below minimum ({len(rep['failure_modes_below_min'])}): " +
          ", ".join(f"{m}={c}" for m, c in rep["failure_modes_below_min"].items()))
