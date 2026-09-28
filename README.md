# GoalJourney AI — Dataset & Evaluation Pipeline

Versioned, validated and extensible data pipeline for training **GoalJourney Navigator**, a
specialised ~4B open-weight model that helps a user reach one goal: it asks only useful questions,
builds a living route (Journey), verifies progress with task-specific evidence, and adapts the
route as reality changes — without becoming a general-purpose assistant.

**Status (Milestone 1.6 — Dataset Calibration v0.1.1):**

* **Policies** are decided: capabilities, confidence semantics, deadline autonomy, Russian voice and
  fact provenance.
* **Dataset v0.1.1** is a traced revision of the immutable v0.1.0: 36 examples revised, every change in
  `data/revisions/v0.1.1.yaml`. The six defects named in the brief are fixed, pending human review.
* **Deterministic validators** now check calendars, workload arithmetic, deadline autonomy, capability
  use, evidence ceilings, fact provenance and Russian gendered forms.
* **Evaluation v0.2.0** has 63 cases (106 model calls): atomic, composite and longitudinal, written from
  independent seeds. Its leakage report separates lexical, template and scenario overlap.

Still, **nothing is approved and release `v0.1.1` is not training-ready** (1/11 release gates pass).
Next step: human review, starting with the 8 calibration items.

| Document | What it is |
|---|---|
| [`DATASET_SPEC.md`](DATASET_SPEC.md) | The data contract: records, operations, policies, rules, splits, exports, evaluation |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Short architectural proposal and design decisions |
| [`DATA_SOURCES.md`](DATA_SOURCES.md) | Provenance, licensing, privacy |
| [`docs/POLICY_DECISIONS_v0.1.1.md`](docs/POLICY_DECISIONS_v0.1.1.md) | POL-A…F: capabilities, confidence semantics, deadline autonomy, Russian voice, fact provenance, product principle |
| [`docs/DATASET_AUDIT_v0.1.1.md`](docs/DATASET_AUDIT_v0.1.1.md) | Audit of v0.1.1: the revisions, validator and schema changes, remaining issues, gates |
| [`docs/EVALUATION_V0.2_DESIGN.md`](docs/EVALUATION_V0.2_DESIGN.md) | Evaluation v0.2.0: case types, strata, adversarial coverage, leakage review |
| [`docs/DATASET_AUDIT_v0.1.0.md`](docs/DATASET_AUDIT_v0.1.0.md) | Audit of v0.1.0 (frozen): composition, gaps, Problems 1–9, schema/rule weaknesses |
| [`docs/HUMAN_REVIEW_GUIDE.md`](docs/HUMAN_REVIEW_GUIDE.md) | How to review: roles, independence, rubric A–Q, Russian neutrality, workflow |
| [`docs/EVALUATION_EXPANSION_PLAN.md`](docs/EVALUATION_EXPANSION_PLAN.md) | From 30 to 200–500 independent evaluation cases |
| [`docs/LEAKAGE_CHECKS.md`](docs/LEAKAGE_CHECKS.md) | What each leakage layer can and cannot establish |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |
| [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) | Current state: versions, health, blockers — updated at every milestone |
| [`docs/ACTIVE_MILESTONE.md`](docs/ACTIVE_MILESTONE.md) | The milestone in progress: tasks, acceptance criteria, progress, next action |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Durable product, data and engineering decisions (D-001…) |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Milestone plan and standing constraints |
| [`docs/CONTEXT_MANAGEMENT.md`](docs/CONTEXT_MANAGEMENT.md) | How work is split across Claude Code sessions: state, recovery, compaction, subagents |

## Quick start

Requires Python ≥ 3.10.

```bash
python3 -m pip install -r requirements.txt   # jsonschema, referencing, PyYAML, pytest
python3 scripts/gj.py validate               # everything must print RESULT: PASS
python3 -m pytest -q                         # 416 tests
python3 scripts/gj.py eval run --predictor reference   # sanity: 106/106 model calls (63/63 cases) pass
python3 scripts/gj.py eval run --predictor naive       # sanity: checks discriminate (0/106)
```

`make check` runs:

* validate and tests;
* the drift checks: evaluation builder, revision ledger, review sample and its status;
* both evaluation sanity runs;
* the leakage report and review-log verification. All commands exit non-zero on failure, so they can gate CI. `make gates` fails until the
release is training-ready (by design, it fails today).

## Commands

All commands: `python3 scripts/gj.py <command> --help`.

| Command | Purpose |
|---|---|
| `validate [--strict] [-v] [--report out.json]` | Schema + semantic lint + contrastive self-test for all examples; YAML authoring guard; near-duplicate check; scenario seeds; evaluation cases (reference outputs must pass their checks) |
| `stats [--json]` | Distribution by operation, behaviour, language, domain, difficulty, size, safety, failure mode |
| `coverage` | Pool vs. scale-up targets (`configs/coverage_targets.yaml`), with the seed scenarios that can fill each gap |
| `generate --scenario ID --task-type OP --limit N [--with-contrastive] [--dry-run]` | Synthetic candidates from scenario seeds via a teacher LLM → `data/generated/<run_id>/` |
| `review sample [--write\|--check]` | Deterministic 30-item review sample → `review/review_manifest_v<ver>.json`; v0.1.1 keeps the v0.1.0 sample (`configs/review.yaml` `sample_version`) |
| `review sample-status [--write\|--check]` | The sample in force at this version: per item what changed (revision ids), known issues, human status → `review/review_sample_status_v<ver>.json` |
| `review list [--manifest] [--status S]` / `review show ID [--show-automated]` | Examples with tier, required qualifications and status / one example for review (automated findings hidden by default) |
| `review template ID` → `review approve\|revise\|reject ID --reviewer ME --from FILE` | Record a decision (categorical rubric A–Q + overall) in the append-only, hash-chained log |
| `review apply SHEET` / `review export --format md\|sheet\|json` | Batch review sheets / reading packets |
| `review history ID` / `review stats` / `review verify-log` | Decisions + diffs between versions / progress, agreement (kappa), funnel / log integrity |
| `audit [--write] [--record ID]` | Heuristic audits (Problems 1–9, dates) + known issues register |
| `revisions check\|sync\|diff [ID]` | Revision ledger vs the base release: every change recorded with defect, correction, rationale and snapshots (no silent edits) |
| `leakage [--distribution]` | Leakage report in three families — lexical, semantic/template, scenario (fails on hard findings) |
| `split [--review-policy require_approved\|allow_pending] [--dry-run]` | Immutable release `data/{train,validation,test}/goaljourney-v<ver>.jsonl` + manifest; aborts on any invalid example or hard leakage |
| `gates [--purpose sft\|preference]` | Release gates: is the release `training_ready`? (thresholds + rationale in `configs/release_gates.yaml`) |
| `export --format sft\|preference\|eval [--allow-draft] [--review-policy …]` | Training files only from approved content of a training-ready release (otherwise refused, or a marked draft); eval export ungated |
| `eval build-cases [--check]` | Render `evaluation/cases/v0.2.0/` (and seeds, eval scenarios, leakage `cases:` block) from `evaluation/builders/v0_2_0/` |
| `eval run --predictor reference\|naive\|model [--provider P --model M]` | Predict and score each model call (atomic case or step) → `evaluation/reports/<run_id>/report.{json,md}` |
| `eval score --predictions file.jsonl` | Score predictions produced elsewhere (`{"case_id", "raw"}` per line) |
| `eval review-sheet --predictions file.jsonl --out sheet.yaml` | Human review sheet for model outputs (scored separately from automated metrics) |

## Typical workflows

**Review examples** (full guide: `docs/HUMAN_REVIEW_GUIDE.md`)
1. Add yourself to `review/reviewers.yaml`.
2. `gj review list --manifest` → start with the calibration items (`*`).
3. `gj review show ID`, `gj review template ID --out d.yaml`, fill it, `gj review approve|revise|reject ID --reviewer you --from d.yaml`.
4. `gj review stats` for progress and agreement.

**Add or edit examples by hand**
1. Edit/add YAML under `data/raw/examples/` (see `DATASET_SPEC.md` §19). Editing content that was decided
   makes its status `pending` (detail `content_changed`).
2. Record the change in the revision ledger `data/revisions/v<ver>.yaml` (defect, correction, rationale),
   then run `gj revisions sync` and `gj revisions check`. A release cannot be built with an unrecorded
   change.
3. `gj validate` until `PASS`, then `gj audit --write` and `gj review sample-status --write`.
4. Review again; bump `dataset_version` before the next release.

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
The model is prompted exactly as in SFT export (`prompts/navigator/v0.1.1/system.md` + request JSON).

## Current dataset (v0.1.1)

| | |
|---|---|
| Training pool | 93 examples → release v0.1.1: train 81 / validation 12 (split by behavioural scenario group) |
| Revisions | 36 examples changed from v0.1.0 (13 defect fixes, 23 policy alignments), all pending human review — `data/revisions/v0.1.1.yaml` |
| Test | evaluation v0.2.0: 63 cases (43 atomic, 14 composite, 6 longitudinal) = 106 model calls, 658 automated checks; v0.1.0's 30 cases kept frozen |
| Languages | RU 41 / EN 52 answers; 3 mixed-language inputs (eval: 29 RU / 34 EN cases, 4 mixed inputs) |
| Coverage | all 14 operations, 20 domains, 5 safety categories |
| Contrastive | 64 rejected outputs covering 32 of the 36 failure modes (each ≥ 2); calendar_error, arithmetic_error, ignored_contradiction and gendered_language (new in v0.1.1) have no rejected example yet |
| Review | 0 approved — release is `draft_unreviewed`; the v0.1.0 review sample is carried forward (12 of 30 items changed) |
| Known issues | 34: 22 fixed pending review, 11 open (2 medium), 1 won't fix |
| Release gates | 1/11 pass — **not training-ready** |

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
  cases/v0.2.0/   current evaluation cases (GENERATED from builders/); cases/v0.1.0/ frozen
  builders/       evaluation v0.2.0 authoring source (Python) → `gj eval build-cases`
  seeds/          independent evaluation seeds
  metrics/        checks and aggregation
  runners/        predictors, runner, case validation, naive baseline
  leakage/        evaluation-side leakage metadata (scenario groups, templates, reviewed overlaps)
  rubrics/        dataset review rubric (v0.2.0), model output rubric
prompts/          navigator runtime prompt, teacher prompts, operation guides, failure-mode catalogue
data/             raw → generated → reviewed (decision log + snapshots) → train/validation/test (+ manifests);
                  revisions/ (ledger + snapshots), scenarios/ (behavioural scenario registry)
review/           reviewer registry, review sample manifest + per-version status, known issues, audit findings
docs/             architecture, policy decisions, audits, review guide, leakage checks, evaluation design and expansion plan
configs/          versions, dataset, generation, evaluation, export, coverage targets, review, release gates, licensing
scripts/gj.py     CLI
tests/            pytest suite
CLAUDE.md, .claude/   Claude Code project memory, settings, path-scoped rules, skills, subagents
```

## Working with Claude Code

The project is built across many independent Claude Code sessions. The repository, not chat history,
carries the state (`docs/CONTEXT_MANAGEMENT.md`).

* **Loaded every session.** `CLAUDE.md` (under 200 lines) holds the principles, rules, conventions
  and critical commands.
* **Loaded when relevant.**
  * `.claude/rules/*.md` load when matching files are touched: product, ai, dataset, evaluation,
    testing, security.
  * Skills load on demand:

    | Skill | Use |
    |---|---|
    | `/start-session` | recover the state |
    | `/milestone-complete` | completion protocol |
    | `/dataset-review` | human-review round |
    | `/dataset-generation` | synthetic generation |
    | `/evaluation` | eval cases and runs |
    | `/release-check` | releases, gates, pre-training checklist |

* **Subagents.** `.claude/agents/` defines six narrow, mostly read-only reviewers: dataset-auditor,
  evaluation-engineer, verification-reviewer, safety-reviewer, architecture-reviewer and
  code-reviewer. Agents never record review decisions.
* **State files.** The files in `docs/` (`PROJECT_STATE`, `ACTIVE_MILESTONE`, `DECISIONS`,
  `ROADMAP`) are updated at checkpoints and before a milestone is declared complete.
* **Context.** Auto-compaction triggers at 75% (`.claude/settings.json`). One major milestone per
  primary session.

`tests/test_orchestration.py` keeps these files well-formed. It also checks that
`docs/PROJECT_STATE.md` matches `configs/versions.yaml`.

## Principles the tooling enforces

* Only capabilities the product has are used or promised (`configs/product_capabilities.yaml`); confidence
  never exceeds what the evidence class supports (`configs/evidence_policy.yaml`).
* No photo-only verification; self-report accepted where proof is impossible and labelled `limited`.
* Insufficient evidence → `needs_more_evidence`, not rejection.
* Completed progress is never silently discarded; major changes need consent. Deadline autonomy:
  task dates may adapt automatically; milestone dates may adapt with a stated summary; goal dates are
  only proposed until the user confirms.
* Dates, weekdays and hour arithmetic in messages must follow from the calendar and the plan; facts
  keep their provenance (user-provided is never presented as verified).
* Current external facts are cited only from provided research; otherwise marked for verification.
* Levels and achievements follow verified progress, never app activity.
* Releases are immutable; nothing unreviewed is treated as ground truth: training exports contain only
  content a qualified human approved, and only when every release gate passes.
* Every change to a released example is recorded in a revision ledger with the defect, correction,
  rationale and snapshots; releases are built only from a clean ledger.
* Leakage is checked in eight layers, grouped into lexical, semantic/template and scenario families.
  The checks can show that leakage exists, not that it is absent: behavioural overlaps between
  evaluation and training are reviewed by people (`docs/LEAKAGE_CHECKS.md`).
