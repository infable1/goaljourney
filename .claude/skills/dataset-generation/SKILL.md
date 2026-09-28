---
name: dataset-generation
description: Synthetic scale-up workflow for GoalJourney training candidates (Milestone 2). Use when planning coverage gaps, adding scenario seeds, running `gj generate` (dry run or real), validating a generation run, or preparing generated candidates for human review. Generation never approves anything, and never uses evaluation material.
---
# Synthetic generation

Spec: `DATASET_SPEC.md` §18 (scale-up) and §19 (authoring). Pipeline: `generation/pipelines/generate.py`.
Config: `configs/generation.yaml`. Targets: `configs/coverage_targets.yaml`.

## Preconditions (check before any real API call)

- The active milestone calls for generation. The ROADMAP puts it in M2, after the first human-review
  calibration. Otherwise, confirm with the owner.
- The owner accepts the open licensing question **LIC-001**: may teacher-LLM outputs be used for
  training? It is recorded in `configs/licensing_status.yaml`. Generation may proceed while it is
  open, but a training-ready release may not.
- Credentials are set **by the user** in the environment or `.env`. Never read `.env` or ask for a
  key in chat.
- Install the extra dependencies: `pip install -r requirements-generation.txt`.

## 1. Find the gaps

```bash
python3 scripts/gj.py coverage       # gap per task type, language, domain, flags; "seeds" = seeds able to fill it
python3 scripts/gj.py stats
```

Choose a small, targeted batch.

- Four failure modes have no rejected (contrastive) example yet: `calendar_error`,
  `arithmetic_error`, `ignored_contradiction` and `gendered_language`. Use `--with-contrastive` on
  seeds that can exhibit them.
- Mixed-input, non-`allowed` safety and domain minimums are the other standing gaps.

## 2. Seeds

- Seeds live in `generation/scenarios/*.yaml`. Add new seed files rather than rewriting existing
  ones.
- **Never derive a seed from evaluation material**: `evaluation/seeds/`, `evaluation/cases/` or the
  eval side of `data/scenarios/`. A new scenario or decision pattern must not match an eval one
  (D-017). `gj leakage` checks this.
- Personas are synthetic. No real people, no inferred gender, and a realistic, varied RU/EN balance.
- Run `gj validate` after adding seeds. It validates scenario seeds too.

## 3. Dry run, then a small real run

```bash
python3 scripts/gj.py generate --scenario <id> --task-type <op> --limit 5 --dry-run   # prompts -> scratch/dry_runs/<run_id>/
python3 scripts/gj.py generate --scenario <id> --task-type <op> --limit 5 [--with-contrastive] --run-id <descriptive-id>
```

- Read a rendered dry-run prompt before the first real run of a new seed or operation.
- `max_candidates_per_run: 50` is a hard cap. Never raise it, and never loop runs to get around it.
  Start with 5–10, inspect them, then scale.
- Output: `data/generated/<run_id>/{candidates.jsonl, rejected.jsonl, manifest.json}`.
  - The manifest records versions, provider and model, prompt hashes and the config snapshot.
  - Never edit it.
  - `rejected.jsonl` holds candidates that failed a stage. Read the reasons, and fix the seed or
    prompt rather than hand-patching output.

## 4. Check the run

```bash
python3 scripts/gj.py validate            # the pool includes data/generated/*/candidates.jsonl
python3 scripts/gj.py leakage             # exits 1 on hard findings; template overlaps need a human disposition
python3 scripts/gj.py audit               # heuristic findings on the new candidates
python3 scripts/gj.py coverage            # did the gap move?
```

- A candidate that fails validation is dropped or regenerated, never hand-fixed into passing.
- Known heuristic false positives are listed in `.claude/rules/testing.md`. Change the seed or
  prompt wording rather than disabling a rule.
- Spot-read a few candidates in full, with `head -c` or a `python -c` one-liner on the JSONL. For a
  larger batch, brief the `dataset-auditor` subagent.

## 5. Hand over to human review

Generated candidates are in the pool but are **excluded from every release until a human approves
them** (`gj split`, `require_approved`).

1. Prepare a sheet: `gj review export --format sheet --status pending --out scratch/review/<run_id>.yaml`.
2. Follow `/dataset-review`. Never approve, and never move candidates into `data/raw/examples/` to
   make them count.

## 6. Version and record

- Adding a run to the pool changes the next release. Bump `dataset_version` in `configs/versions.yaml`
  and open the next ledger, `data/revisions/v<new>.yaml`, whose base is the last release.
- The ledger's `examples_added` must list the new ids: run `gj revisions sync`, then
  `gj revisions check`.
- `make check`. Commit the run directory together with its manifest.
- Update `docs/ACTIVE_MILESTONE.md` progress: runs, candidates, rejects, coverage change.

## Never

- Generate from, or paraphrase, evaluation cases.
- Commit credentials or print them in logs.
- Silently switch the teacher provider or model. The model is recorded per run; a new default goes
  in `configs/generation.yaml` with a decision entry.
- Treat a passing validation as quality approval.
