"""`gj stats`: distribution of the example pool across the axes that matter for diversity."""
from collections import Counter

from gjcore.config import load_config
from gjcore.paths import repo_path
from gjcore.records import load_examples

AXES = ["task_type", "language", "input_language", "domain", "difficulty", "goal_size", "safety_category"]


def compute_stats(path=None):
    cfg = load_config("dataset")
    records = [r for r, _ in load_examples(repo_path(path or cfg["paths"]["raw_examples"]))]
    stats = {"examples": len(records)}
    for ax in AXES:
        stats[ax] = dict(Counter(r.get(ax) for r in records).most_common())
    stats["behavior"] = dict(Counter(b for r in records for b in r.get("behavior", [])).most_common())
    stats["tags"] = dict(Counter(t for r in records for t in r.get("tags", [])).most_common())
    stats["scenario_groups"] = len({r.get("scenario_group") for r in records})
    stats["with_contrastive"] = sum(1 for r in records if r.get("contrastive"))
    stats["contrastive_outputs"] = sum(len(r.get("contrastive") or []) for r in records)
    stats["failure_modes"] = dict(Counter(m for r in records for c in r.get("contrastive") or [] for m in c["failure_modes"]).most_common())
    stats["with_decision_summary"] = sum(1 for r in records if (r.get("expected_output") or {}).get("decision_summary"))
    stats["provenance"] = dict(Counter(f"{r['provenance']['source']}/{r['provenance']['method']}" for r in records if r.get("provenance")))
    return stats


def print_stats(stats):
    print(f"Examples: {stats['examples']}   scenario groups: {stats['scenario_groups']}")
    print(f"With contrastive: {stats['with_contrastive']}   contrastive outputs: {stats['contrastive_outputs']}   "
          f"with decision_summary: {stats['with_decision_summary']}")
    for key in ["task_type", "behavior", "language", "input_language", "domain", "difficulty", "goal_size",
                "safety_category", "failure_modes", "provenance"]:
        print(f"\n{key}:")
        for k, v in stats[key].items():
            print(f"  {str(k):34s} {v}")
