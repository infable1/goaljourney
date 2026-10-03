# Changelog

All notable changes to the dataset, schemas, prompts, pipeline and evaluation. Versions are
defined in `configs/versions.yaml`; releases are immutable.

## 2026-10-03 — Owner-only approval, no expert gate (D-030; schema 0.1.4, pipeline 0.4.4)

The product owner decided that one accountable human owner's approval of the exact current content
hash is sufficient human approval for every current training example and every evaluation reference
decision, including the former expert-tier and non-allowed-safety items (D-030, superseding the
expert requirement of D-026, D-028 and D-029). No external domain expert is required. D-030 is a
governance change, not a claim about the owner's professional qualification.

- **Training review (`review_store`).**
  - `approval.expert_tier_requires_expert` is removed from `configs/review.yaml`. A qualified human
    approval of the current content approves an example of any risk tier.
  - `awaiting_expert` is removed from the status details and from `INELIGIBILITY_REASONS` (now
    `not_reviewed`, `content_changed`, `needs_revision`, `rejected`). `training_eligibility()`
    returns `human_reviewed`, `training_eligible` and `reason`.
  - Unchanged: content-hash binding, registered humans only, language match, the most conservative
    decision winning, revise/reject, findings acknowledgement, known issues and every release gate
    setting.
  - `required_expert_domains` and the `expert_review_required` tier stay as a risk label for
    sampling, coverage and the review manifest; they no longer gate an approval. `domain_expert`
    stays a valid registry role but grants nothing.
- **Evaluation reference review (`evaluation/reference_review.py`).** The status is
  `draft_unreviewed` until every reference output has a decision on its current content, then
  `human_reviewed`. Risk domains never affect it. `gj validate` reports `human_reviewed` and
  `draft_unreviewed` cases.
- **Schema 0.1.4** (0.1.3 archived byte-identically in `schemas/archive/v0.1.3/`).
  - `eval_case.json`: `reference_status` is `draft_unreviewed` or `human_reviewed`. Session
    `reviewer_roles` / `reviewer_expert_domains` are an audit snapshot only.
  - `review_event.json`: `new_status_detail` is `not_reviewed`, `content_changed` or `decided`.
  - Model I/O records keep `schema_version` 0.1.1. Evaluation envelopes stamped 0.1.3 still
    validate against the archived 0.1.3, and the review log (v0.3, 46 events) is unchanged and
    verifies.
- **Migration.** `gj eval build-cases` rebuilt the v0.2.0 YAML. Only 4 `reference_status` lines
  changed: `e2-long-06`, `e2-comp-07`, `e2-safe-01` and `e2-safe-03` moved from `awaiting_expert`
  to `human_reviewed` on their existing owner decisions. No review event was added, and no
  decision, content hash, input, reference output or check changed. All 63 cases are
  `human_reviewed` (106/106 reference outputs decided); the 9 `revise` decisions are kept.
- **Training state:** no example was `awaiting_expert`, so no row changed status: 21 `approved`
  (training-eligible), 10 `needs_revision`, 62 `not_reviewed`, 0 `rejected`, 0 `content_changed`.
  The release v0.1.2 manifest is unchanged. Still blocking `gj gates`: `review_all_approved`
  (21/84), `coverage_minimums`, `eval_readiness` (63/200) and `licensing_resolved`.
- **Tests:** owner approval of former expert-tier training examples and evaluation cases; no
  current code path produces `awaiting_expert`; historical events still validate; revise/reject,
  hash binding, findings acknowledgement and the other gate settings unchanged; evaluation cases
  never become training rows (D-017).
- **Docs:** D-030 in `docs/DECISIONS.md` (superseded notes on D-026, D-028 and D-029), the human
  review guide, `DATASET_SPEC.md`, the evaluation design, the product-owner checklist, the review,
  evaluation and release-check skills, the evaluation rule, the safety-reviewer agent, `CLAUDE.md`
  and the state files.

## 2026-10-02 — Expert-tier reference reviews await the expert (D-029; schema 0.1.3 and pipeline 0.4.3 amended, no version change)

The product owner decided that the owner's review of an expert-tier evaluation reference is recorded and waits
for a qualified expert (D-029, refining D-028).

- **Schema 0.1.3, additive change; 0.1.3 is in no release.**
  - `reference_status` gains `awaiting_expert`.
  - Review sessions gain optional `reviewer_roles` and `reviewer_expert_domains`, the reviewer's registry
    entry at recording time.
  - Earlier sessions are untouched and count as no expert coverage.
- **`gj eval review-reference`.**
  - It no longer refuses an expert-tier case. It records the owner's session with their roles and domains.
  - The status is `awaiting_expert` until registered `domain_expert` decisions on the current content
    cover the required domains for every reference output; then it is `human_reviewed`.
  - The "already decided" guard now applies only to the same reviewer, so an expert can decide after the
    owner without `--replace`.
  - `gj validate` lists the cases awaiting an expert and the domains they need.
- **Recorded:** the owner's review of `e2-long-06`, recorded as given:
  - all 5 steps `approve` / `excellent`;
  - no issues or notes;
  - `po-reviewer`, `independent_rating: true`.

  The case is expert-tier (`safety_policy`) and is `awaiting_expert`. No expert qualification was claimed or
  created, and the reviewer registry is unchanged. Eval cases are never training rows, so this is a review
  state, not training eligibility.
- Docs: DECISIONS D-029 (and a refinement note on D-028), EVALUATION_V0.2_DESIGN §1, HUMAN_REVIEW_GUIDE §18,
  the evaluation rule and skill, PROJECT_STATE and ACTIVE_MILESTONE.
- Tests: three new tests in `tests/test_reference_review.py` cover owner-then-expert recording, a
  wrong-domain expert, sessions without roles and the human tier. The old "expert-tier is refused"
  expectation is replaced, and the summary assertions now include the two new keys.

## 2026-10-01 — Evaluation reference review, stored in the cases (schema 0.1.3, pipeline 0.4.3; no dataset or evaluation version change)

The product owner decided how evaluation reference outputs are reviewed (Milestone 1.7, task 7; D-028):
under `solo_owner` governance one registered owner completes the review, and the review is stored inside
the evaluation case.

- **Schema 0.1.3.** `schemas/eval_case.json` gains an optional case-level `reference_review` block:
  - `metadata_schema_version`, plus append-only `sessions`;
  - each session has `reviewer_id`, `timestamp`, `governance_mode` (`solo_owner`) and `independent_rating`;
  - each session has one decision per reference output: `step_id` for multi-step cases, the output's
    `content_hash`, `action` approve|revise|reject, `overall` excellent|acceptable|needs_revision|incorrect,
    `issues` and `notes`;
  - the action, overall and issues must be consistent;
  - there are no criterion ratings.

  The `reference_status` description no longer requires two reviewers. The 0.1.2 schemas are archived
  byte-identical in `schemas/archive/v0.1.2/`, records stay at `schema_version` 0.1.1, and no lint rule
  changed. A reviewed case's envelope is validated against the block's `metadata_schema_version`; the
  case's own `schema_version` stays its model input/output contract.
- **Pipeline 0.4.3.**
  - `gj eval review-reference CASE --reviewer --from FILE --independent-rating yes|no [--replace]` records
    one session. It refuses the following:
    - unregistered, non-human or inactive reviewers;
    - a language gap;
    - an expert-tier case without a matching `domain_expert`;
    - `multi_reviewer` mode;
    - unknown or duplicate steps, or a given content hash;
    - generated files that drift from the builder.
  - It binds each decision to the reference output's current hash and writes the case file through the
    builder.
  - `gj eval build-cases` carries recorded reviews over, derives `reference_status`, and refuses to render
    if a review's case is no longer built.
  - `gj validate` checks reviewers, units, session order and the derived status, and reports how many
    reference outputs are decided.
- **Status semantics.** `human_reviewed` means every reference output has a decision on its current
  content. A partial or stale review stays `draft_unreviewed`. A reviewed reference is still one acceptable
  answer, not the only correct one.
- **Releases unchanged.** Review metadata is not evaluation content, so neither `evaluation_version` nor
  `dataset_version` changes. Releases keep their build-time review state.
  `test_existing_release_is_idempotent` now rebuilds a release from the reference reviews as they stood
  at build time, as it already did for the review log; v0.1.2 still reproduces byte for byte.
- **Recorded:** the owner's review of `e2-long-01`, recorded as given:
  - all 9 steps `approve` / `excellent`;
  - no issues or notes;
  - `po-reviewer`, `independent_rating: true` (the AI second look changed nothing).

  The case is `human_reviewed`, with 9 of 106 reference outputs decided. No reference output, check,
  input or other case changed.
- Docs: DECISIONS (D-028), EVALUATION_V0.2_DESIGN §1, §6, §8 and §9, HUMAN_REVIEW_GUIDE §18, the
  evaluation rule and skill, README, PROJECT_STATE and ACTIVE_MILESTONE. Tests:
  `tests/test_reference_review.py` (21). `test_v020_case_type_shapes` now asserts the derived status
  instead of "every case is a draft".

## 2026-09-30 — Dataset v0.1.2: owner-decided fixes for KI-008, KI-012 and KI-033 (pipeline 0.4.2; no schema or evaluation version change)

The product owner decided the three open known issues (Milestone 1.7, task 5): KI-008 option B, KI-012 option A
and KI-033 option A. v0.1.1 is released, so the fixes go into dataset v0.1.2 (base v0.1.1), with a new ledger
`data/revisions/v0.1.2.yaml` and a draft release (`draft_unreviewed`: train 72, validation 12, test 63; the
9 `needs_revision` examples are excluded).

- **REV-0.1.2-001 / `gj-jour-001` (KI-008).** Pacing stays at 10 h/week and the milestone dates are unchanged.
  - The weekly time the learning tasks leave is planned as job-search time:
    - background nodes n17–n19 in region r4 (now active): 25.5 h, 36 h and 40.5 h;
    - a new first-interview node n16 (13.5 h);
    - estimates on n14 (45 h) and n15 (10.5 h).
  - Each milestone window is within capacity: cumulative 39.5/40, 99.5/100, 149/150 and 218/220 h.
  - `pacing.notes`, the r4 description, the strategy summary, the message and the impact state the split:
    47 h learning, portfolio and CV; 102 h background search; 69 h active search.
  - Achievement a4 «Первое собеседование» unlocks on n16.
- **REV-0.1.2-002 / `gj-goalchg-001` (KI-012).**
  - The message asks for the current 7 km time before judging whether December 1 fits a sub-60 finish.
  - `facts_used` marks that time as unknown.
  - `minor_adjustment`, the updated goal and the preserved progress are unchanged.
- **REV-0.1.2-003 / `gj-vres-007` (KI-033).**
  - The follow-up question is a required method, with a pass criterion for its answer.
  - The expected output asks for the answer as well.
  - The required list of ideas and the medium ceiling are kept.
  - This removes the only `VP_NATURE_MISMATCH` warning, so `validation_strict` passes on v0.1.2.
- **Known issues.** `review/known_issues_v0.1.2.yaml` carries v0.1.1 forward.
  - KI-008, KI-012 and KI-033 are `fixed_pending_review`, with the owner's decision under `resolution`, their
    revision ids, and `human_review: pending`.
  - The v0.1.1 register is unchanged.
- **Review state.** No review event changed.
  - Human review of the new content is pending: the three ledger entries are `pending_human_review`.
  - rv-0.1.0-14 / `gj-jour-001` is `pending` (`content_changed`) on its new hash. Its rv-0.1.0-14 decision stays
    in the log for the old hash.
  - That decision's `external_fact_discipline` and `explanation_quality` issues were not part of the KI-008
    fix.
- **Pipeline 0.4.2** (`generation/pipelines/revisions.py`, `sample_status.py`).
  - A released, no-longer-current version's ledger and sample status are judged against that version's own
    release (`version_records`, `records_for_version`), not the working pool. The v0.1.2 edits therefore do
    not make the v0.1.1 ledger, its 36 human reviews or `review/review_sample_status_v0.1.1.json` look
    stale.
  - Rows a release left out are reconstructed from the base and the ledger's current snapshot.
  - A released ledger is never re-synced.
  - The sample status lists revision ids along the ledger chain back to the sample version
    (`revision_history`).
- **Generated outputs:** `review/audit_findings_v0.1.2.json`, `review/review_sample_status_v0.1.2.json`,
  revision snapshots, and the v0.1.2 release files.
- **Gates.** `gj gates` on v0.1.2 passes 4 of 9 applicable (`validation_strict` and `known_issues_closed` now
  pass). It is not training-ready.
- **Tests** in `tests/test_sampling_audit_leakage.py`:
  - the v0.1.2 ledger, register and release;
  - the ledger chain;
  - historical checks, including reconstructed rows;
  - no re-sync of a released ledger;
  - sample status for both versions.

## 2026-09-30 — Human reviews of revision-ledger entries (schema 0.1.2, pipeline 0.4.1; no dataset or evaluation version change)

On the owner's direction (D-027), a ledger entry's human decision is now recorded with its reviewer,
notes and independence, not only as a bare `reviewer_status`.

- **Schema 0.1.2.** `schemas/revision_ledger.json` gains an optional per-entry `review` block
  (`reviewer_id`, `timestamp`, `content_hash`, `independent_rating`, `notes`). It is required when
  `reviewer_status` is `confirmed` or `disputed`, and forbidden while `pending_human_review`. The
  0.1.1 schemas are archived byte-identical in `schemas/archive/v0.1.1/`. No record changes: examples
  stay at `schema_version` 0.1.1 and validate against the archived set, and no lint rule changed.
- **`gj revisions review REV-ID --reviewer --status confirmed|disputed --notes --independent-rating
  yes|no [--replace]`** (`generation/pipelines/revisions.py`). It refuses unless the ledger passes
  `gj revisions check`, the reviewer is a registered, active human who reads the example's
  languages, and notes are given. The decision is bound to the entry's current `content_hash`. A
  second review of the same entry needs `--replace`; git keeps the earlier block.
- **`gj revisions check`** now also fails when a review's `content_hash` differs from its entry's
  (the correction changed after the decision) or names a reviewer who is not a registered human.
  `gj revisions diff` shows the review.
- **First decisions** (po-reviewer): REV-0.1.1-001, -004 and -005 `confirmed`
  (`independent_rating: true`); REV-0.1.1-002 and -003 `disputed` (`independent_rating: false`, the
  owner changed them from confirmed after an AI second-look). No example, snapshot, known issue,
  review event or release changed; the disputed corrections are not fixed here.
- Seven tests in `tests/test_revision_reviews.py`.

## 2026-09-29 — Fix: `reviewer_diversity` counts one approval per reviewer per approved row (no version change)

- `generation/pipelines/gates.py` counted approve *events*, so a corrective re-approval by the same
  reviewer (rv-0.1.0-01, `rev-a1a061cc1487`) raised the informational share to 111%. It now counts
  each reviewer whose latest decision on the row's current content hash is approve (`resolve()`
  decisions), at most once per approved row. Thresholds, solo behaviour (N/A) and event meanings
  are unchanged; v0.1.1 in multi-reviewer mode still fails the gate (share 100%).
- Five tests in `tests/test_solo_review.py`; three of them fail on the old counting.

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
