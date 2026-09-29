# Changelog

All notable changes to the dataset, schemas, prompts, pipeline and evaluation. Versions are
defined in `configs/versions.yaml`; releases are immutable.

## 2026-09-29 — Solo-owner-first review governance (pipeline 0.4.0, release gates 1.1; no dataset, schema or evaluation version change)

The project moves from **multi-reviewer-first governance** to **solo-owner-first governance with
optional expert escalation** (D-026, directed by the product owner). The reason: the project has
one owner, and the pairwise gates could be met only by a second person it does not have, or by a
fabricated identity.

- **Governance mode.** `configs/review.yaml` `governance.mode: solo_owner`. A config without a
  mode means `multi_reviewer`.
  - The mode decides which gates apply. It never changes how decisions resolve, so historical
    multi-reviewer events keep their meaning.
  - With one reviewer, their latest decision on a content hash is final.
- **Gate scopes** (`configs/release_gates.yaml` 1.1; `generation/pipelines/gates.py`).
  - Every gate carries `scope: always` or `scope: multi_reviewer`. Only `reviewer_diversity` and
    `calibration_agreement` are `multi_reviewer`.
  - In solo mode they are reported **N/A**: `passed` is null, they never count as passed, and they
    never block. `gj gates` prints the mode, PASS / FAIL / N/A and the applicable count.
  - No threshold changed; every other gate stays blocking in both modes.
- **Training eligibility** (`review_store.training_eligibility`, `split.plan_release` /
  `build_release`).
  - Release manifests gain `review_mode` and `training_eligibility`: the eligible count, counts per
    reason, and every example that is not training-eligible, with its reason (`awaiting_expert`
    with missing domains, `needs_revision`, `rejected`, `not_reviewed`, `content_changed`) and
    whether it is in the release as a draft row.
  - `resolve()` also reports `covered_expert_domains`. Status logic is unchanged.
- **Stats.** `gj review stats` shows the mode, the human reviewers, and pool and sample counts
  (human-reviewed, training-eligible, awaiting expert, needs revision, rejected, not reviewed,
  content changed). Pair calibration and reviewer diversity show as N/A. Historical pair agreement
  is labelled informational.
- **Independence flag.** `gj review approve|revise|reject --independent-rating yes|no`. `no`
  records that a rating was changed after seeing findings or AI critique.
- **Docs.**
  - `docs/HUMAN_REVIEW_GUIDE.md`: a solo-owner preface, then §14 AI review copilot (it may
    explain, challenge and recalculate; it never records, impersonates, counts as an expert or
    changes decisions), §15 "I'm unsure" (notes, no new state), §16 expert tier and training
    eligibility, §17 multi-reviewer compatibility.
  - Also updated: DATASET_SPEC §2, §14 and §15; D-026 (D-014 refined); the `/dataset-review` and
    `/release-check` skills; the state files; and the registry header.
- **Tests.** `tests/test_solo_review.py` has 16 tests: the solo path, no fake pass, the expert
  tier, the AI copilot, historical compatibility, multi-reviewer mode, invalidation on revision,
  and manifest and export eligibility. `test_release_is_not_training_ready_for_the_right_reasons`
  now expects the pairwise gates to be N/A, not passed. No test was loosened.
- **Unchanged.**
  - No review event, snapshot, example, ledger entry, release file or manifest.
  - Both registry entries are unchanged; `po-reviewer-two` is still `active` (an owner decision).
  - v0.1.1 rebuilds byte-identically from its release-time review log.
  - `gj gates` is 2 of 9 applicable passed plus 2 N/A (before: 3 of 11 passed, one of them
    `calibration_agreement`). Not training-ready.

## 2026-09-29 — Review rubric 0.2.1 (no dataset, schema or evaluation version change)

- **Rubric 0.2.1** (`evaluation/rubrics/dataset_review_rubric_v0.2.1.yaml`, now set in
  `configs/review.yaml`): adds `safety.clarifications` for restricted goals (D-025). Criteria,
  applicability, hard gates, ratings and decision rules are unchanged; a test pins this. Rubric 0.2.0
  stays unchanged in `dataset_review_rubric.yaml`, because earlier review events are stamped with it.
- No example, snapshot or review event changed. The calibration disagreement on rv-0.1.0-02 is not
  adjudicated: no reviewer with the `adjudicator` role is registered.
- **Sample status regenerated** (`gj review sample-status --write`): the file predated the first
  human decision. It now shows the 8 calibration items as decided (6 approved, 2 needs_revision),
  exactly as the review log resolves them; nothing else changed and `approved_by_automation` stays 0.
- **Test expectations repaired** (no gate or pipeline change):
  - `test_release_is_not_training_ready_for_the_right_reasons` (eec3c19): `calibration_agreement` is no
    longer expected to fail (8/8 double-reviewed).
  - `test_sample_status_…`: instead of "every item pending", statuses must equal what the human log
    resolves, and every approved item needs a human approval of its current content.
  - `test_existing_release_is_idempotent`: the frozen v0.1.1 release snapshots review status at build
    time, so it is rebuilt from the review log as it stood then (it reproduces byte-identically); a
    rebuild from the live log must not rewrite the release (it is refused: 2 rows are now
    `needs_revision`). Getting review decisions into a release needs a new `dataset_version`.
- **State files synchronised** (documentation only): `docs/PROJECT_STATE.md`,
  `docs/ACTIVE_MILESTONE.md` and `docs/ROADMAP.md` now describe M1.7 as in progress:
  - 2 human dataset reviewers; 17 review events;
  - calibration 8/8 double-reviewed, decision agreement 0.875, κ 0.60;
  - `reviewer_diversity` failing; 3/11 gates pass;
  - rv-0.1.0-02 not adjudicated (no adjudicator);
  - no domain experts registered.

## 2026-09-28 — Project orchestration & context management (no version change)

This is infrastructure and documentation only. Dataset, schema, prompts, pipeline and evaluation
versions are unchanged (0.1.1 / 0.1.1 / 0.1.1 / 0.3.0 / 0.2.0), and no example, eval case, release
or review record changed. No model was trained.

- **State files.** `docs/PROJECT_STATE.md`, `docs/ACTIVE_MILESTONE.md` (M1.7 Human Review Round 1,
  *proposed*), `docs/DECISIONS.md` (D-001…D-020, consolidated from the spec, policies and
  architecture) and `docs/ROADMAP.md`.
- **Context strategy.** `docs/CONTEXT_MANAGEMENT.md` defines the session, state, recovery and
  compaction rules, when to use subagents, and what stays out of `CLAUDE.md`.
- **Project memory.** `CLAUDE.md` (under 200 lines) and `.claude/settings.json`:
  - auto-compaction at 75% via `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`;
  - reading `.env` denied.
- **Rules and skills.**
  - Path-scoped rules in `.claude/rules/`: product, ai, dataset, evaluation, testing, security.
  - Skills: `/start-session`, `/milestone-complete`, `/dataset-review`, `/dataset-generation`,
    `/evaluation`, `/release-check`.
  - A model-training skill was considered and deferred to M3. The pre-training checklist is in
    `/release-check`.
- **Subagents.** `.claude/agents/` holds dataset-auditor, evaluation-engineer, verification-reviewer,
  safety-reviewer, architecture-reviewer and code-reviewer. Each is narrow and read-only, except
  evaluation-engineer: on explicit delegation, it may edit `evaluation/builders/` and the leakage
  metadata.
- **`.gitignore`.** Now also covers model checkpoints and weights, experiment logs, local caches and
  `.claude/settings.local.json`.
- **`tests/test_orchestration.py`.** Checks CLAUDE.md length and references, settings, secret-like
  values, skill, agent and rule well-formedness (rule globs must match files), state-file sections,
  PROJECT_STATE versions against `configs/versions.yaml`, and `.gitignore` coverage.

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
