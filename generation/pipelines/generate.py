"""`gj generate`: produce synthetic candidates from scenario seeds with a teacher LLM.

Output: data/generated/<run_id>/{candidates.jsonl, rejected.jsonl, manifest.json}
Dry run: renders the stage-1 prompts to scratch/dry_runs/<run_id>/ without any API call or credentials.
Generated candidates enter a release only after human approval (gj review).
"""
from datetime import datetime, timezone
from pathlib import Path

from gjcore.config import load_config, versions
from gjcore.io import dump_json, write_jsonl
from gjcore.paths import REPO_ROOT, rel, repo_path
from gjcore.records import load_records
from generation.generators import prompting
from generation.generators.generator import StageError, generate_candidate, next_generated_number
from generation.generators.providers import ProviderError, make_provider, with_retries


def _plan(scenarios, scenario_ids, task_types, limit):
    plan = []
    for sc in scenarios:
        if scenario_ids and sc["id"] not in scenario_ids:
            continue
        for op in sc["task_types"]:
            if task_types and op not in task_types:
                continue
            plan.append((sc, op))
    return plan[:limit]


def run_generation(scenarios_path="generation/scenarios", scenario_ids=None, task_types=None, limit=5,
                   provider_name=None, model=None, dry_run=False, with_contrastive=False, run_id=None):
    gen_cfg = load_config("generation")
    cap = gen_cfg["run"]["max_candidates_per_run"]
    if limit > cap:
        print(f"✗ --limit {limit} exceeds max_candidates_per_run={cap} (configs/generation.yaml). "
              f"Generate in reviewed batches.")
        return 1
    scenarios = [s for s, _ in load_records(repo_path(scenarios_path), "scenarios")]
    plan = _plan(scenarios, scenario_ids, task_types, limit)
    if not plan:
        print("Nothing to generate (check --scenario / --task-type).")
        return 1
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    today = datetime.now(timezone.utc).date().isoformat()

    if dry_run:
        out = REPO_ROOT / "scratch" / "dry_runs" / run_id
        out.mkdir(parents=True, exist_ok=True)
        for i, (sc, op) in enumerate(plan, 1):
            (out / f"{i:03d}_{sc['id']}_{op}_stage1.md").write_text(prompting.stage1_prompt(sc, op, today), encoding="utf-8")
        print(f"Dry run: rendered {len(plan)} stage-1 prompt(s) to {rel(out)} (no API calls).")
        return 0

    provider = make_provider(provider_name, model)
    retries = gen_cfg["run"]["retries"]
    backoff = gen_cfg["run"]["backoff_seconds"]
    number = next_generated_number()
    candidates, rejected = [], []
    for sc, op in plan:
        try:
            rec, notes = generate_candidate(
                provider, sc, op, number, run_id, today, with_contrastive,
                call=lambda s, u: with_retries(lambda: provider.complete(s, u), retries, backoff))
            candidates.append(rec)
            number += 1
            print(f"  ✓ {rec['id']}  {sc['id']} / {op}" + (f"  ({len(notes)} note(s))" if notes else ""))
        except StageError as e:
            rejected.append({"scenario": sc["id"], "operation": op, "stage": e.stage, "reason": e.reason,
                             "raw": (e.raw or "")[:4000]})
            print(f"  ✗ {sc['id']} / {op}: {e}")
        except ProviderError as e:
            rejected.append({"scenario": sc["id"], "operation": op, "stage": "provider", "reason": str(e)})
            print(f"  ✗ {sc['id']} / {op}: provider error: {e}")

    out = repo_path(load_config("dataset")["paths"]["generated"]) / run_id
    write_jsonl(candidates, out / "candidates.jsonl")
    write_jsonl(rejected, out / "rejected.jsonl")
    dump_json({
        "run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versions": versions(), "provider": provider.describe(),
        "prompt_files_sha256": prompting.prompt_file_hashes(),
        "config": gen_cfg, "plan": [{"scenario": sc["id"], "operation": op} for sc, op in plan],
        "with_contrastive": with_contrastive,
        "counts": {"planned": len(plan), "candidates": len(candidates), "rejected": len(rejected)},
        "note": "Candidates are not training data until approved via `gj review`.",
    }, out / "manifest.json")
    print(f"Run {run_id}: {len(candidates)} candidate(s), {len(rejected)} rejected -> {rel(out)}")
    return 0 if candidates else 1
