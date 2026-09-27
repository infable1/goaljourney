# Changelog

All notable changes to the dataset, schemas, prompts, pipeline and evaluation. Versions are
defined in `configs/versions.yaml`; releases are immutable.

## [0.1.1] — 2026-09-27 — Milestone 1.6: Dataset Calibration

This is dataset 0.1.1, schema 0.1.1, navigator and generation prompts 0.1.1, pipeline 0.3.0 and
evaluation 0.2.0. v0.1.0 is unchanged: its release, manifest, review manifest, known issues, audit
report, evaluation cases, leakage metadata and schemas are byte-identical, and the v0.1.0 schemas are
archived in `schemas/archive/v0.1.0/`. No model was trained. No example was approved, and no approval
came from automation.

### Policies (docs/POLICY_DECISIONS_v0.1.1.md)
- **POL-A — capabilities.** `configs/product_capabilities.yaml` classifies each capability as
  available, planned or unsupported. Training data never requires a planned capability (video, tracker
  sync, proactive messages, calendar) and never promises an unsupported one.
- **POL-B — confidence semantics.** `configs/evidence_policy.yaml` defines evidence classes and the
  ceiling each supports. User-entered data is the user's word unless references are spot-checked.
- **POL-C — deadline autonomy.** Task dates are `auto`; milestone dates are `adapt_with_summary`; goal
  dates are `confirm_required` and only `proposed` until the user confirms.
- **POL-D — Russian voice.** No gendered self-reference, no gendered address to the user, and neutral
  memory.
- **POL-E — fact provenance** (`facts_used`).
- **POL-F — the product principle.**

### Dataset v0.1.1 (data/revisions/v0.1.1.yaml)
- 36 examples revised: 13 defect fixes and 23 policy alignments. Each ledger entry records the defect,
  correction, rationale, known issues, policies, before/after hashes, changed paths and snapshots, and
  `reviewer_status: pending_human_review`.
- The six defects named in the brief are corrected: `gj-nav-006`, `gj-time-001`, `gj-time-004`,
  `gj-nav-001`, `gj-task-004`, `gj-clar-007`.
- All 93 examples move to `schema_version` 0.1.1. Scenario groups are now behavioural scenarios
  (`data/scenarios/behavioural_scenarios.yaml`), and the old group is kept as `topic_group`.
- `gj revisions check|sync|diff`: releases are refused while the ledger is incomplete.
- Release v0.1.1 (`draft_unreviewed`): train 81, validation 12, test 63 evaluation cases. Revised rows
  carry `revision_ids` and `previous_content_hash`. The validation membership changed with the new
  scenario groups (10 of 12), so validation scores are not comparable with v0.1.0.
- Known issues v0.1.1: 34 issues — 22 fixed pending review, 11 open, 1 won't fix.

### Validators (docs/DATASET_AUDIT_v0.1.1.md §4)
- New modules:
  - `calendar` (weekday/date);
  - `workload` + `quantities` (remaining work, pace phases, horizons, arithmetic stated in prose);
  - `policy` (capabilities, evidence classes);
  - `provenance` (facts_used, memory numbers);
  - `russian` (gendered forms).
- Deadline-autonomy, feasibility and contradiction rules, input lint, and a warning for untagged
  defects in rejected outputs.
- All new rules are version-gated: v0.1.0 records are still judged by v0.1.0 rules.
- The audit heuristics now use the policies and the shared calendar/Russian modules.

### Schemas 0.1.1
- New properties:
  - `facts_used` on seven operations;
  - `modified_deadlines[].autonomy/state` and `workload`/`invalidated_progress` on route adaptation;
  - navigator `target_type`/`new_date`;
  - evidence classes and `references_required` on protocols;
  - `contradictions` on verification results;
  - `evidence.responds_to`.
- `example_record.topic_group/revision`.
- `eval_case` gains case types, steps with `step_pattern`, strata, adversarial tags and
  `reference_status`.
- New schemas: `behavioural_scenarios`, `revision_ledger`, `review_sample_status`.
- Six new failure modes: `calendar_error`, `arithmetic_error`, `unavailable_capability`,
  `overconfident_verification`, `ignored_contradiction`, `gendered_language`.

### Review
- Canonical statuses `pending | approved | needs_revision | rejected`, with a detail of
  `not_reviewed | content_changed | awaiting_expert | decided`. Review log v0.3.0 stays append-only.
- The v0.1.0 30-item sample and its 8 calibration items are carried forward (`sampling.sample_version`)
  and regenerated from the frozen v0.1.0 inputs.
- `gj review sample-status` → `review/review_sample_status_v0.1.1.json`: 12 of 30 items changed, 30
  pending, 0 approved by automation.

### Evaluation 0.2.0 (docs/EVALUATION_V0.2_DESIGN.md)
- 63 cases from independent seeds (`evaluation/seeds/v0.2.0.yaml`): 43 atomic, 14 composite and 6
  longitudinal — 106 model calls and 658 checks. This includes the 5-turn Python chain and adversarial
  cases (26 cases).
- Cases are authored in `evaluation/builders/v0_2_0/` and rendered by `gj eval build-cases [--check]`.
- Teacher-forced steps are scored as units, and a case passes only if all its units pass.
- New metrics: state_consistency, numeric_consistency, evidence_integrity, capability_compliance,
  fact_provenance, deadline_autonomy. New check: `value_between`.
- Results: reference 106/106, naive 0/106.
- Evaluation v0.1.0 is kept frozen and validated.

### Leakage (docs/LEAKAGE_CHECKS.md)
- The report is grouped into lexical, semantic/template and scenario families.
- New L8 decision-pattern layer; registry-side checks; per-step units.
- `evaluation/leakage/v0.2.0.yaml` holds 100 reviewed overlaps (11 strong, 78 medium, 4 topic-only,
  7 coincidental), all awaiting human dispositions.
- 3 cases were rewritten and 5 re-topicked during the review. The automated layers found 13 of the
  116 reviewed pairs.

### Release gates
- 1 of 11 pass (`leakage_hard_clean`). No gate was loosened. `validation_strict` now fails on one input
  warning (`gj-vres-007`, KI-033, which needs a reviewer's decision).

### Tooling
- `make check` adds the drift checks: builder, revision ledger, review sample and sample status.
- `eval_readiness` counts cases, and per-operation model calls.
- 416 tests.

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
