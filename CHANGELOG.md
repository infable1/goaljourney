# Changelog

All notable changes to the dataset, schemas, prompts, pipeline and evaluation. Versions are
defined in `configs/versions.yaml`; releases are immutable.

## [pipeline 0.2.0] — 2026-09-27 — Milestone 1.5: Human Review & Dataset Calibration

Dataset content is unchanged (`dataset_version` stays 0.1.0; the release is byte-identical). No
example was edited, generated or approved; no model was trained.

### Added
- **Review system v0.2.** Categorical rubric A–Q + overall O (`evaluation/rubrics/dataset_review_rubric.yaml`,
  v0.2.0; no summed score; hard gates on external facts and safety). Append-only, hash-chained decision
  log (`data/reviewed/review_events.jsonl`, `schemas/review_event.json`) with preserved snapshots of the
  reviewed content, derived statuses (pending / stale / approved / approved_pending_expert /
  needs_revision / rejected), reviewer registry (`review/reviewers.yaml`, humans only), language
  qualification, expert tier with domain sign-off, adjudication, acknowledgement of high-severity
  findings, Cohen's kappa agreement statistics.
- CLI: `gj review sample | list | show [--show-automated] | template | approve | revise | reject | apply |
  history | stats | export --format md|sheet|json | verify-log`.
- **Deterministic review sample** `review/review_manifest_v0.1.0.json`: 30 items (12 random, 9 highest-risk,
  6 contrastive, 3 edge), all 22 coverage categories, ≥ 3 expert-tier, 8 calibration items, stable ids.
- **Audit scanner** `gj audit` (Problems 1–9 + weekday/date consistency) → `review/audit_findings_v0.1.0.json`,
  and a **known-issues register** `review/known_issues_v0.1.0.yaml` (32 issues on 41 examples, each with a
  proposed revision; nothing applied).
- **Layered leakage checks** `gj leakage` (exact, character near-duplicate, lexical paraphrase, behavioural
  template, scenario group, seed); evaluation-side metadata `evaluation/leakage/v0.1.0.yaml` with 27 reviewed
  template overlaps and 1 seed overlap awaiting human dispositions; `docs/LEAKAGE_CHECKS.md`.
- **Release gates** `gj gates` (`configs/release_gates.yaml`, every threshold with its rationale) and
  `configs/licensing_status.yaml`; release status `draft_unreviewed → reviewed_not_training_ready → training_ready`.
- Docs: `docs/DATASET_AUDIT_v0.1.0.md`, `docs/HUMAN_REVIEW_GUIDE.md`, `docs/EVALUATION_EXPANSION_PLAN.md`,
  `docs/LEAKAGE_CHECKS.md`, `review/README.md`.
- 51 tests (225 total).

### Changed
- `gj export --format sft|preference` is gated: only content approved *now* (content-hash match), only if the
  release gates pass; `--allow-draft` writes `exports/v<ver>-draft/` with `training_eligible: false` and a
  `DRAFT_NOT_FOR_TRAINING` marker; `--review-policy allow_pending` implies a draft.
- `gj split` uses the layered leakage guard; release immutability compares data files (a manifest built by an
  earlier pipeline is kept as built).
- `gj review export/apply/status` replaced by the v0.2 workflow (the v0.1 numeric rubric is kept for reference;
  the v0.1 log was never written, and review commands refuse to run if one appears unmigrated).
- `pipeline_version` 0.1.0 → 0.2.0.

### Findings (see docs/DATASET_AUDIT_v0.1.0.md)
- 6 examples with high-severity defects that pass every validator (wrong weekday, two arithmetic errors,
  an invented user fact, masculine self-reference, masculine address); 7 with medium issues; 10 awaiting
  policy decisions; 18 with low-severity notes.
- v0.1.0 is not training-ready: 2 of 11 release gates pass.

## [0.1.0] — 2026-09-27 — Milestone 1: Dataset Foundation

### Added
- JSON Schemas (2020-12) for 7 entities (goal, journey, task, verification protocol, evidence,
  memory, decision summary), the model input context, 14 operation outputs and 4 record envelopes.
- Semantic linter with ~115 coded behavioural rules and a failure-mode catalogue of 30 modes
  (14 auto-detected, enforced by a contrastive self-test).
- 93 agent-authored training examples across all 14 operations and every behaviour family in the
  brief (RU 41 / EN 52, 3 mixed-language inputs, 20 domains, all 5 safety categories), with 64
  schema-valid contrastive outputs.
- 30 evaluation cases (173 automated checks) covering 12 dimensions, each with a reference output;
  `reference` / `naive` / `model` predictors; per-metric and per-dimension reports; human review sheets.
- Dataset-quality rubric (review gate) and model-output rubric (human evaluation).
- Pipelines: validate, stats, coverage, generate (2-stage + contrastive, provider-agnostic, dry run),
  review (content-hash-keyed log), split (group split, leakage guard, immutable releases), export
  (SFT, preference, eval).
- 30 scenario seeds and coverage targets for the ~2,000-example scale-up.
- Release v0.1.0 (`draft_unreviewed`): train 81, validation 12, test 30.

### Known limitations
- No human review yet; see `DATASET_SPEC.md` §20.
