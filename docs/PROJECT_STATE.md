# Project state

*Last updated: 2026-09-29 · during Milestone 1.7 (Human Review Round 1), after the move to
solo-owner-first review governance (D-026, pipeline 0.4.0) and the first solo-owner reviews
(rv-0.1.0-01, rv-0.1.0-03). Update this file before declaring any
milestone complete (`/milestone-complete`).*

**Governance change (D-026).** The project has moved from **multi-reviewer-first governance** to
**solo-owner-first governance with optional expert escalation**. The reasons:

* the project has one product owner;
* the pairwise gates (`reviewer_diversity`, `calibration_agreement`) could be met only with a second
  independent person the project does not have, or with a fabricated identity, which the review
  rules forbid.

Solo mode keeps every check one careful human can honestly perform:

* the rubric A–Q with hard gates L and M;
* content-hash binding and the append-only log;
* invalidation on revision;
* ratings independent of automated findings;
* the expert tier.

Solo mode is also explicit about what one person cannot provide: the two pairwise gates are shown as
**N/A**, never as passed, and expert-tier items without a qualified expert stay `awaiting_expert`
and are not training-eligible. `multi_reviewer` mode keeps the earlier semantics.

This file is the durable, factual snapshot of the repository. The repository is the source of
truth; chat history is not.

## Repository

| | |
|---|---|
| Repository | `infable1/goaljourney` — dataset, validation and evaluation pipeline for the GoalJourney Navigator model |
| Working branch | Default branch `claude/fervent-keller-j517cd` (there is no `main`). The M1.7 review round after `ae21c7d` is on `claude/sleepy-dijkstra-nzrf3t`, which also merged the rv-0.1.0-29 record from `claude/compassionate-noether-1o9iyx`; it is not merged into the default branch. No open pull request (infable1/goaljourney#1 and infable1/goaljourney#2 were closed unmerged) |
| History | `995f513` M1 → `476d322` M1.5 → `c3b7cfb`…`13d837e` M1.6 → orchestration setup → M1.7 review round `fdf6d4c`…`e0dbc53` → solo-owner governance (D-026, pipeline 0.4.0) `6d6bcb5` → first solo-owner reviews `9457084` and the rv-0.1.0-01 independence correction (latest commits: `git log --oneline -5`) |
| Language / stack | Python ≥ 3.10; jsonschema, referencing, PyYAML, pytest; CLI `scripts/gj.py`; `make check` |
| Mobile app / product code | not in this repository |

## Versions (`configs/versions.yaml` is authoritative)

| Artefact | Version | Notes |
|---|---|---|
| dataset | 0.1.1 | release `draft_unreviewed`: train 81, validation 12, test 63 eval cases. v0.1.0 is immutable and kept |
| schema | 0.1.1 | v0.1.0 archived in `schemas/archive/v0.1.0/` |
| pipeline | 0.4.0 | review governance modes (`solo_owner` default), gate scopes, training-eligibility accounting in release manifests; 0.3.0: v0.1.1 validators, revision ledger, review log v0.3, eval builders |
| evaluation | 0.2.0 | 63 cases / 106 model calls (43 atomic, 14 composite, 6 longitudinal). v0.1.0 (30 cases) frozen |
| navigator prompt / generation prompts | 0.1.1 / 0.1.1 | `prompts/navigator/v0.1.1/`, `prompts/generation/v0.1.1/` |
| base model | unset | chosen later, recorded in `configs/versions.yaml` |

## Milestones

* Done: M1 (dataset foundation), M1.5 (human review system, audits, leakage, gates) and M1.6
  (dataset calibration v0.1.1).
* Active: M1.7 (Human Review Round 1), in progress; see [`ACTIVE_MILESTONE.md`](ACTIVE_MILESTONE.md).
  Plan: [`ROADMAP.md`](ROADMAP.md). Review state (from `gj review stats`, `gj gates`):
  * **Governance mode:** `solo_owner` (`configs/review.yaml`). `reviewer_diversity` and
    `calibration_agreement` are N/A. Adjudication and pairwise calibration are not part of the solo
    workflow.
  * **Reviewers:** 2 registered humans, `po-reviewer` and `po-reviewer-two`, both still `active`.
    Both are `dataset_reviewer`, read ru and en, and hold no expert domains. No `adjudicator` and no
    `domain_expert` is registered. `gj review stats` notes the 2 active reviewers in solo mode.
    Whether `po-reviewer-two` keeps reviewing (or is set `active: false`; past events keep their
    snapshot) is the owner's decision.
  * **Decisions:** 20 review events (`po-reviewer` 12, `po-reviewer-two` 8).
    * The first 17 are stamped rubric 0.2.0: 16 on the 8 calibration items, plus 1
      (`rev-da39af4d1363`, approve of `gj-daily-002`) on an example outside the review sample.
    * The last 3 are stamped rubric 0.2.1. They are the first solo-owner reviews by `po-reviewer`,
      both approve / acceptable with minor issues:
      * rv-0.1.0-01 / `gj-feas-005`: `rev-044d69c4953d`, followed by the corrective
        `rev-a1a061cc1487`;
      * rv-0.1.0-03 / `gj-prog-003`: `rev-599dbd07516e`.
  * **Independence correction.** `rev-044d69c4953d` was recorded with `independent_rating: true`,
    but the owner had changed `language_quality` from major to minor issues after the AI-copilot
    discussion. The corrective event appends the same final decision with
    `independent_rating: false`; the original line is unchanged. rv-0.1.0-03 keeps
    `independent_rating: true`, because no rating changed there. Across all events:
    `independent_rating` is absent on 16, `true` on 3, `false` on 1.
  * **Counts (`gj review stats`):**
    * pool (93): human-reviewed 11, training-eligible 9, needs_revision 2, not reviewed 82;
    * review sample (30): decided 10, approved 8, needs_revision 2, pending 20
      (`review/review_sample_status_v0.1.1.json`).
  * **Historical calibration (informational in solo mode):** all 8 items rated by both reviewers
    (`po-reviewer-two` from a blind packet). Decision agreement is 7/8 (0.875, κ 0.60) and
    overall-verdict agreement 3/8 (κ 0.05). The events are unchanged and still count as recorded.
  * **rv-0.1.0-02 (gj-safe-003, `high_risk`):** the recorded decisions disagree (`po-reviewer`
    revise, `po-reviewer-two` approve), so it stays `needs_revision`; the most conservative
    decision wins. In solo mode no adjudicator is needed. A later decision by `po-reviewer` replaces
    their own earlier one. An adjudication record (approve, excellent) is prepared in git-ignored
    `scratch/` only and is **not recorded**. The item also needs `medical` and `physical_safety`
    sign-off before it can be `approved`.
  * **rv-0.1.0-30 (gj-safe-006, `restricted`):** both reviewers chose revise (external-fact
    discipline). It needs a content revision (new dataset version and ledger entry) and `legal`
    sign-off.
  * **Rubric:** 0.2.1 is in force (D-025, restricted-goal safety anchor). 0.2.0 is kept for the
    events stamped with it.

## Model training

**Not started. v0.1.1 is not training-ready.** No base model is chosen, and no training code is in
the repository. Training exports are refused until every applicable release gate passes.

`gj gates` (solo_owner) passes 2 of 9 applicable gates: `findings_acknowledged` and
`leakage_hard_clean`. The other 2 gates are N/A. Before D-026 the count was 3 of 11; the third pass
was `calibration_agreement`, which is now N/A rather than passed.

## Implemented capabilities

* **Data contract.**
  * JSON Schemas for 14 operations, with records validated against their own `schema_version`.
  * Semantic lint of ~170 rules: calendar, workload arithmetic, deadline autonomy, capabilities,
    evidence ceilings, fact provenance, Russian voice.
  * A contrastive self-test.
* **Data.** 93 agent-authored examples (RU 41 / EN 52) and 64 rejected outputs. The revision ledger
  `data/revisions/v0.1.1.yaml` records 36 revised examples.
* **Review.**
  * A rubric (0.2.1; 0.2.0 kept).
  * An append-only, hash-chained decision log (20 events).
  * A reviewer registry (2 human dataset reviewers; one owner is enough) and expert tiers.
  * Governance modes `solo_owner` (default) and `multi_reviewer`.
  * Training-eligibility states (human-reviewed / expert-reviewed / training-eligible / not
    eligible with a reason).
  * An `--independent-rating` flag, and a documented AI review copilot and "unsure" path
    (HUMAN_REVIEW_GUIDE §14–15).
  * A 30-item sample (8 calibration items) and a per-version sample status file.
* **Audit.** Heuristic audit (`gj audit`) and the known-issues register
  `review/known_issues_v0.1.1.yaml`.
* **Leakage.** 8 layers in 3 families (lexical, semantic/template, scenario). The reviewed overlap
  list is `evaluation/leakage/v0.2.0.yaml`.
* **Releases.**
  * Immutable releases (`gj split`). From pipeline 0.4.0, manifests list every example that is not
    training-eligible, with its reason (`training_eligibility`).
  * 11 release gates (`gj gates`, `configs/release_gates.yaml` 1.1): 9 with `scope: always`, and
    2 with `scope: multi_reviewer` that are N/A in solo mode.
  * Gated exports (`gj export`).
* **Evaluation.** Builders (`gj eval build-cases`), teacher-forced multi-step units and a
  reference/naive/model runner.
* **Generation.** Synthetic generation pipeline (`gj generate`). It is provider-agnostic, capped at
  50 candidates per run, and not yet used at scale.
* **Orchestration.**
  * `CLAUDE.md` and `.claude/settings.json` (auto-compaction at 75%).
  * 6 path-scoped rules and 6 skills: `/start-session`, `/milestone-complete`, `/dataset-review`,
    `/dataset-generation`, `/evaluation`, `/release-check`.
  * 6 subagents in `.claude/agents/`.
  * These state files; see `docs/CONTEXT_MANAGEMENT.md`.

## Health (at last update)

`make -k check` passes (after the rv-0.1.0-01 independence correction, every target):

* 445 tests passed and 2 skipped (9 in `tests/test_orchestration.py`, 21 in
  `tests/test_solo_review.py`);
* the builder, ledger and sample drift checks;
* reference 106/106, naive 0/106;
* leakage: 0 hard findings;
* `gj review verify-log`: 20 events, 0 errors, 1 warning. The warning is the expected fork left by
  merging two branches that both appended to the log (guide §11).

`gj validate` has 1 warning: gj-vres-007 (KI-033).

## Blockers

1. **Human review is at an early stage.** 20 review events so far. 20 of the 30 sample items and the
   36 ledger revisions (all `pending_human_review`) are not reviewed.
   * `review_all_approved`: 9/93 approved.
   * In solo mode the owner reviews alone. `reviewer_diversity` and `calibration_agreement` are N/A
     and no longer block. Under `multi_reviewer` mode, `reviewer_diversity` would still fail:
     `po-reviewer` approved every approved row.
   * `reviewer_diversity` counts one approval per reviewer per approved row (fixed after the
     corrective re-approval of `gj-feas-005` made the informational share read 111%). Its
     informational share is now 100%.
   * **No qualified `domain_expert`:** expert-tier items stay `awaiting_expert` and are not
     training-eligible. rv-0.1.0-02 needs `medical` and `physical_safety`, rv-0.1.0-30 needs
     `legal`, rv-0.1.0-28 needs `financial`.
   * Consequence: `coverage_minimums` requires a non-allowed-safety share ≥ 8% of approved rows.
     Every non-allowed example is expert-tier (the fallback domain is `safety_policy`), so **no
     release can be training-ready without qualified expert sign-off**. This is intended; the gate
     is not loosened.
2. **Policies POL-A…F** need product-owner confirmation (`docs/POLICY_DECISIONS_v0.1.1.md`).
3. **Licensing:** 5 open items (`configs/licensing_status.yaml`) block any training-ready release.
4. **Open known issues:** KI-008 and KI-012 (medium), and KI-033, which fails `validation_strict` and
   needs a reviewer's choice.
5. **Evaluation overlaps:** 100 reviewed overlaps have no disposition, and eval size is 63/200 cases.

## Where to look

| Need | File |
|---|---|
| Data contract | `DATASET_SPEC.md` |
| Policies | `docs/POLICY_DECISIONS_v0.1.1.md` |
| Latest audit | `docs/DATASET_AUDIT_v0.1.1.md` |
| Evaluation design | `docs/EVALUATION_V0.2_DESIGN.md` |
| Review workflow | `docs/HUMAN_REVIEW_GUIDE.md` |
| Leakage | `docs/LEAKAGE_CHECKS.md` |
| History | `CHANGELOG.md` |
| Durable decisions | `docs/DECISIONS.md` |
| Context / session rules | `docs/CONTEXT_MANAGEMENT.md` |
