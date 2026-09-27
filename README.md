# GoalJourney AI — Dataset & Evaluation Pipeline

Versioned, validated and extensible data pipeline for training **GoalJourney Navigator**, a
specialised ~4B open-weight model that helps a user reach one goal: it asks only useful questions,
builds a living route (Journey), verifies progress with task-specific evidence, and adapts the
route as reality changes — without becoming a general-purpose assistant.

**Status (Milestone 1.5 — Human Review & Dataset Calibration):** 93 training examples and 30
evaluation cases pass every automated check. A human-review system, audits, layered leakage checks
and release gates are in place. The audit found concrete defects that the validators miss, so
**no example is approved yet and release `v0.1.0` is not training-ready** (2/11 release gates pass).
Next step: human review of the 30-item sample, starting with the 8 calibration items.

| Document | What it is |
|---|---|
| [`DATASET_SPEC.md`](DATASET_SPEC.md) | The data contract: records, operations, policies, rules, splits, exports, evaluation |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Short architectural proposal and design decisions |
| [`DATA_SOURCES.md`](DATA_SOURCES.md) | Provenance, licensing, privacy |
| [`docs/DATASET_AUDIT_v0.1.0.md`](docs/DATASET_AUDIT_v0.1.0.md) | Audit of v0.1.0: composition, gaps, Problems 1–9, schema/rule weaknesses |
| [`docs/HUMAN_REVIEW_GUIDE.md`](docs/HUMAN_REVIEW_GUIDE.md) | How to review: roles, independence, rubric A–Q, Russian neutrality, workflow |
| [`docs/EVALUATION_EXPANSION_PLAN.md`](docs/EVALUATION_EXPANSION_PLAN.md) | From 30 to 200–500 independent evaluation cases |
| [`docs/LEAKAGE_CHECKS.md`](docs/LEAKAGE_CHECKS.md) | What each leakage layer can and cannot establish |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |

## Quick start

Requires Python ≥ 3.10.

```bash
python3 -m pip install -r requirements.txt   # jsonschema, referencing, PyYAML, pytest
python3 scripts/gj.py validate               # everything must print RESULT: PASS
python3 -m pytest -q                         # 225 tests
python3 scripts/gj.py eval run --predictor reference   # sanity: 30/30 cases pass
python3 scripts/gj.py eval run --predictor naive       # sanity: checks discriminate
```

`make check` runs validate + tests + both evaluation sanity runs + the leakage report + review-log
verification. All commands exit non-zero on failure, so they can gate CI. `make gates` fails until the
release is training-ready (by design, it fails today).

## Commands

All commands: `python3 scripts/gj.py <command> --help`.

| Command | Purpose |
|---|---|
| `validate [--strict] [-v] [--report out.json]` | Schema + semantic lint + contrastive self-test for all examples; YAML authoring guard; near-duplicate check; scenario seeds; evaluation cases (reference outputs must pass their checks) |
| `stats [--json]` | Distribution by operation, behaviour, language, domain, difficulty, size, safety, failure mode |
| `coverage` | Pool vs. scale-up targets (`configs/coverage_targets.yaml`), with the seed scenarios that can fill each gap |
| `generate --scenario ID --task-type OP --limit N [--with-contrastive] [--dry-run]` | Synthetic candidates from scenario seeds via a teacher LLM → `data/generated/<run_id>/` |
| `review sample [--write\|--check]` | Deterministic 30-item review sample → `review/review_manifest_v<ver>.json` |
| `review list [--manifest] [--status S]` / `review show ID [--show-automated]` | Examples with tier, required qualifications and status / one example for review (automated findings hidden by default) |
| `review template ID` → `review approve\|revise\|reject ID --reviewer ME --from FILE` | Record a decision (categorical rubric A–Q + overall) in the append-only, hash-chained log |
| `review apply SHEET` / `review export --format md\|sheet\|json` | Batch review sheets / reading packets |
| `review history ID` / `review stats` / `review verify-log` | Decisions + diffs between versions / progress, agreement (kappa), funnel / log integrity |
| `audit [--write] [--record ID]` | Heuristic audits (Problems 1–9, dates) + known issues register |
| `leakage [--distribution]` | Layered train/eval/seed leakage report (fails on hard findings) |
| `split [--review-policy require_approved\|allow_pending] [--dry-run]` | Immutable release `data/{train,validation,test}/goaljourney-v<ver>.jsonl` + manifest; aborts on any invalid example or hard leakage |
| `gates [--purpose sft\|preference]` | Release gates: is the release `training_ready`? (thresholds + rationale in `configs/release_gates.yaml`) |
| `export --format sft\|preference\|eval [--allow-draft] [--review-policy …]` | Training files only from approved content of a training-ready release (otherwise refused, or a marked draft); eval export ungated |
| `eval run --predictor reference\|naive\|model [--provider P --model M]` | Predict and score → `evaluation/reports/<run_id>/report.{json,md}` |
| `eval score --predictions file.jsonl` | Score predictions produced elsewhere (`{"case_id", "raw"}` per line) |
| `eval review-sheet --predictions file.jsonl --out sheet.yaml` | Human review sheet for model outputs (scored separately from automated metrics) |

## Typical workflows

**Review examples** (full guide: `docs/HUMAN_REVIEW_GUIDE.md`)
1. Add yourself to `review/reviewers.yaml`.
2. `gj review list --manifest` → start with the calibration items (`*`).
3. `gj review show ID`, `gj review template ID --out d.yaml`, fill it, `gj review approve|revise|reject ID --reviewer you --from d.yaml`.
4. `gj review stats` for progress and agreement.

**Add or edit examples by hand**
1. Edit/add YAML under `data/raw/examples/` (see `DATASET_SPEC.md` §19). Editing reviewed content makes it `stale`;
   record a `revise` decision first so the change is traceable.
2. `gj validate` until `PASS`, then `gj audit --write`.
3. Review again; bump `dataset_version` before the next release.

**Generate synthetic candidates (scale-up)**
```bash
cp .env.example .env            # add ANTHROPIC_API_KEY (or configure an OpenAI-compatible endpoint)
python3 -m pip install -r requirements-generation.txt
python3 scripts/gj.py generate --scenario sc-edu-001 --limit 3 --dry-run   # inspect prompts, no API call
python3 scripts/gj.py generate --scenario sc-edu-001 --limit 3 --with-contrastive
python3 scripts/gj.py validate && python3 scripts/gj.py review export --format sheet --status pending --out review.yaml
```
Candidates enter a release only after approval. Runs are capped at 50 candidates
(`configs/generation.yaml`) so every batch gets reviewed. Missing credentials fail with an
explicit message; secrets are read only from the environment or a git-ignored `.env`.

**Build a release and export for training**
```bash
# bump dataset_version in configs/versions.yaml first if content changed since the last release
python3 scripts/gj.py split --review-policy require_approved
python3 scripts/gj.py gates                        # must pass before any training export
python3 scripts/gj.py export --format sft          # {"messages": [system, user, assistant]} — approved rows only
python3 scripts/gj.py export --format preference   # chosen vs. rejected pairs from contrastive outputs
python3 scripts/gj.py export --format sft --allow-draft   # tooling smoke test: exports/v<ver>-draft/, training_eligible: false
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
| Review | 0 approved — release is `draft_unreviewed`; 30-item review sample ready; 10 examples need expert sign-off |
| Audit | 41 examples with recorded issues (6 high, 7 medium, 10 policy-dependent, 18 low) — see `docs/DATASET_AUDIT_v0.1.0.md` |
| Release gates | 2/11 pass — **not training-ready** |

`gj stats` and `gj coverage` print the live numbers.

## Repository map

```
schemas/          JSON Schema 2020-12 — single source of truth for every structure
gjcore/           paths, IO, config, env/credentials, schema registry, records, runtime prompt
generation/
  validators/     semantic lint, record validation, text heuristics, similarity/leakage
  generators/     providers (anthropic, openai_compatible, replay), teacher prompts, generator
  pipelines/      validate, stats, coverage, generate, review (+store, sampling), audit, leakage, gates, split, export
  scenarios/      scenario seeds for scale-up
evaluation/
  cases/v0.1.0/   evaluation cases (+ reference outputs)
  metrics/        checks and aggregation
  runners/        predictors, runner, case validation, naive baseline
  leakage/        evaluation-side leakage metadata (scenario groups, templates, reviewed overlaps)
  rubrics/        dataset review rubric (v0.2.0), model output rubric
prompts/          navigator runtime prompt, teacher prompts, operation guides, failure-mode catalogue
data/             raw → generated → reviewed (decision log + snapshots) → train/validation/test (+ manifests)
review/           reviewer registry, review sample manifest, known issues, audit findings
docs/             architecture, audit, review guide, leakage checks, evaluation expansion plan
configs/          versions, dataset, generation, evaluation, export, coverage targets, review, release gates, licensing
scripts/gj.py     CLI
tests/            pytest suite
```

## Principles the tooling enforces

* No photo-only verification; self-report accepted where proof is impossible and labelled `limited`.
* Insufficient evidence → `needs_more_evidence`, not rejection.
* Completed progress is never silently discarded; major changes and deadline changes need consent.
* Current external facts are cited only from provided research; otherwise marked for verification.
* Levels and achievements follow verified progress, never app activity.
* Releases are immutable; nothing unreviewed is treated as ground truth: training exports contain only
  content a qualified human approved, and only when every release gate passes.
* Leakage is checked in seven layers (exact, near-duplicate, paraphrase, template, scenario, seed); the
  checks can show that leakage exists, not that it is absent — behavioural overlaps between evaluation
  and training are reviewed by people (`docs/LEAKAGE_CHECKS.md`).
