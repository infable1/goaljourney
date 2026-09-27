# GoalJourney AI — Dataset & Evaluation Pipeline

Versioned, validated and extensible data pipeline for training **GoalJourney Navigator**, a
specialised ~4B open-weight model that helps a user reach one goal: it asks only useful questions,
builds a living route (Journey), verifies progress with task-specific evidence, and adapts the
route as reality changes — without becoming a general-purpose assistant.

**Milestone 1 (Dataset Foundation) — status:** schemas, validation, generation, review, split,
export and evaluation pipelines are in place; 93 training examples and 30 evaluation cases pass
all automated checks; release `v0.1.0` is built as `draft_unreviewed` (no human review yet).

| Document | What it is |
|---|---|
| [`DATASET_SPEC.md`](DATASET_SPEC.md) | The data contract: records, operations, policies, rules, splits, exports, evaluation |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Short architectural proposal and design decisions |
| [`DATA_SOURCES.md`](DATA_SOURCES.md) | Provenance, licensing, privacy |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |

## Quick start

Requires Python ≥ 3.10.

```bash
python3 -m pip install -r requirements.txt   # jsonschema, referencing, PyYAML, pytest
python3 scripts/gj.py validate               # everything must print RESULT: PASS
python3 -m pytest -q                         # 177 tests
python3 scripts/gj.py eval run --predictor reference   # sanity: 30/30 cases pass
python3 scripts/gj.py eval run --predictor naive       # sanity: checks discriminate
```

`make check` runs validate + tests + both evaluation sanity runs. All commands exit non-zero on
failure, so they can gate CI.

## Commands

All commands: `python3 scripts/gj.py <command> --help`.

| Command | Purpose |
|---|---|
| `validate [--strict] [-v] [--report out.json]` | Schema + semantic lint + contrastive self-test for all examples; YAML authoring guard; near-duplicate check; scenario seeds; evaluation cases (reference outputs must pass their checks) |
| `stats [--json]` | Distribution by operation, behaviour, language, domain, difficulty, size, safety, failure mode |
| `coverage` | Pool vs. scale-up targets (`configs/coverage_targets.yaml`), with the seed scenarios that can fill each gap |
| `generate --scenario ID --task-type OP --limit N [--with-contrastive] [--dry-run]` | Synthetic candidates from scenario seeds via a teacher LLM → `data/generated/<run_id>/` |
| `review export --out sheet.yaml` / `review apply sheet.yaml --reviewer NAME` / `review status` | Human review against the rubric; append-only log keyed by content hash |
| `split [--review-policy require_approved\|allow_pending] [--dry-run]` | Immutable release `data/{train,validation,test}/goaljourney-v<ver>.jsonl` + manifest; aborts on any invalid example or train/eval leakage |
| `export --format sft\|preference\|eval` | Training/eval files in `exports/v<ver>/` |
| `eval run --predictor reference\|naive\|model [--provider P --model M]` | Predict and score → `evaluation/reports/<run_id>/report.{json,md}` |
| `eval score --predictions file.jsonl` | Score predictions produced elsewhere (`{"case_id", "raw"}` per line) |
| `eval review-sheet --predictions file.jsonl --out sheet.yaml` | Human review sheet for model outputs (scored separately from automated metrics) |

## Typical workflows

**Add or edit examples by hand**
1. Edit/add YAML under `data/raw/examples/` (see `DATASET_SPEC.md` §19 for authoring rules).
2. `gj validate` until `PASS`.
3. `gj review export --out review.yaml`, review, `gj review apply review.yaml --reviewer you`.

**Generate synthetic candidates (scale-up)**
```bash
cp .env.example .env            # add ANTHROPIC_API_KEY (or configure an OpenAI-compatible endpoint)
python3 -m pip install -r requirements-generation.txt
python3 scripts/gj.py generate --scenario sc-edu-001 --limit 3 --dry-run   # inspect prompts, no API call
python3 scripts/gj.py generate --scenario sc-edu-001 --limit 3 --with-contrastive
python3 scripts/gj.py validate && python3 scripts/gj.py review export --out review.yaml --status pending
```
Candidates enter a release only after approval. Runs are capped at 50 candidates
(`configs/generation.yaml`) so every batch gets reviewed. Missing credentials fail with an
explicit message; secrets are read only from the environment or a git-ignored `.env`.

**Build a release and export for training**
```bash
# bump dataset_version in configs/versions.yaml first if content changed since the last release
python3 scripts/gj.py split --review-policy require_approved
python3 scripts/gj.py export --format sft          # {"messages": [system, user, assistant]}
python3 scripts/gj.py export --format preference   # chosen vs. rejected pairs from contrastive outputs
```

**Evaluate a fine-tuned model** (served by vLLM, Ollama, or any OpenAI-compatible server)
```bash
export OPENAI_COMPATIBLE_BASE_URL=http://localhost:8000/v1
python3 scripts/gj.py eval run --predictor model --provider openai_compatible --model my-navigator-4b
python3 scripts/gj.py eval review-sheet --predictions evaluation/reports/<run_id>/predictions.jsonl --out review_model.yaml
```
The model is prompted exactly as in SFT export (`prompts/navigator/v0.1.0/system.md` + request JSON).

## Current dataset (v0.1.0)

| | |
|---|---|
| Training pool | 93 examples → release: train 81 / validation 12 (split by scenario group) |
| Test | 30 evaluation cases, 173 automated checks, 12 dimensions |
| Languages | RU 41 / EN 52 answers; 3 mixed-language inputs |
| Coverage | all 14 operations, all behaviour families of the brief, 20 domains, 5 safety categories |
| Contrastive | 64 rejected outputs over 30 failure modes (every mode ≥ 2) |
| Review | 0 approved — release is `draft_unreviewed` |

`gj stats` and `gj coverage` print the live numbers.

## Repository map

```
schemas/          JSON Schema 2020-12 — single source of truth for every structure
gjcore/           paths, IO, config, env/credentials, schema registry, records, runtime prompt
generation/
  validators/     semantic lint, record validation, text heuristics, similarity/leakage
  generators/     providers (anthropic, openai_compatible, replay), teacher prompts, generator
  pipelines/      validate, stats, coverage, generate, review, split, export
  scenarios/      scenario seeds for scale-up
evaluation/
  cases/v0.1.0/   evaluation cases (+ reference outputs)
  metrics/        checks and aggregation
  runners/        predictors, runner, case validation, naive baseline
  rubrics/        dataset quality rubric, model output rubric
prompts/          navigator runtime prompt, teacher prompts, operation guides, failure-mode catalogue
data/             raw → generated → reviewed → train/validation/test (+ manifests)
configs/          versions, dataset, generation, evaluation, export, coverage targets
scripts/gj.py     CLI
tests/            pytest suite
```

## Principles the tooling enforces

* No photo-only verification; self-report accepted where proof is impossible and labelled `limited`.
* Insufficient evidence → `needs_more_evidence`, not rejection.
* Completed progress is never silently discarded; major changes and deadline changes need consent.
* Current external facts are cited only from provided research; otherwise marked for verification.
* Levels and achievements follow verified progress, never app activity.
* No leakage between training and evaluation; releases are immutable; nothing unreviewed is
  silently treated as ground truth.
