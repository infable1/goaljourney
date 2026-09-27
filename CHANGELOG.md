# Changelog

All notable changes to the dataset, schemas, prompts, pipeline and evaluation. Versions are
defined in `configs/versions.yaml`; releases are immutable.

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
