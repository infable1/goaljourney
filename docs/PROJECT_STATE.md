# Project state

*Last updated: 2026-09-30 · during Milestone 1.7 (Human Review Round 1), after the move to
solo-owner-first review governance (D-026, pipeline 0.4.0) and the first solo-owner reviews
(rv-0.1.0-01, rv-0.1.0-03, rv-0.1.0-04, rv-0.1.0-05, rv-0.1.0-06, rv-0.1.0-07, rv-0.1.0-08, rv-0.1.0-10, rv-0.1.0-11, rv-0.1.0-13, rv-0.1.0-14, rv-0.1.0-15, rv-0.1.0-16, rv-0.1.0-17, rv-0.1.0-18). Update this file before declaring any
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
| History | `995f513` M1 → `476d322` M1.5 → `c3b7cfb`…`13d837e` M1.6 → orchestration setup → M1.7 review round `fdf6d4c`…`e0dbc53` → solo-owner governance (D-026, pipeline 0.4.0) `6d6bcb5` → first solo-owner reviews `9457084`, the rv-0.1.0-01 independence correction `2438dd4` the rv-0.1.0-04 review `5b3f7c4` and the rv-0.1.0-05 review `71c92eb` and the rv-0.1.0-06 review `8deff75` and the rv-0.1.0-07 review `40a3d51` with its notes correction `7284b5a` the rv-0.1.0-08 review `2997666` and the rv-0.1.0-10 review `301009a` the rv-0.1.0-11 review `c7eef17` the rv-0.1.0-13 review `b297d91` and the rv-0.1.0-14 review `8aa4416` the rv-0.1.0-15 review `6e92860` the rv-0.1.0-16 review `d876db9` the rv-0.1.0-17 review `49fe41f` and the rv-0.1.0-18 review `e27bb32` (latest commits: `git log --oneline -5`) |
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
  * **Decisions:** 34 review events (`po-reviewer` 26, `po-reviewer-two` 8).
    * The first 17 are stamped rubric 0.2.0: 16 on the 8 calibration items, plus 1
      (`rev-da39af4d1363`, approve of `gj-daily-002`) on an example outside the review sample.
    * The last 17 are stamped rubric 0.2.1. They are the solo-owner reviews by `po-reviewer`:
      * rv-0.1.0-01 / `gj-feas-005`: `rev-044d69c4953d` (approve / acceptable, minor issues),
        followed by the corrective `rev-a1a061cc1487`;
      * rv-0.1.0-03 / `gj-prog-003`: `rev-599dbd07516e` (approve / acceptable, minor issue);
      * rv-0.1.0-04 / `gj-route-006`: `rev-612c1a60c45a` (`5b3f7c4`), `revise`, overall
        `needs_revision`, `user_agency: major_issues`, `language_quality: minor_issues`,
        `independent_rating: true`. The example is `needs_revision`, so it is not
        training-eligible;
      * rv-0.1.0-05 / `gj-route-003`: `rev-3f360f0323f8` (`71c92eb`), `approve`, overall
        `excellent`, no issues, `contrastive_quality: good`, `privacy_and_memory:
        not_applicable`, `independent_rating: false`. The owner changed those two ratings after
        the AI second-look discussion, so the flag records provenance; it is not an issue;
      * rv-0.1.0-06 / `gj-time-001` (a calibration item): `rev-1584bfb68001` (`8deff75`),
        `approve`, overall `excellent`, no issues, `contrastive_quality: good`,
        `privacy_and_memory: not_applicable`, `independent_rating: false` (the owner changed
        `privacy_and_memory` after the AI second-look discussion). The example was already
        `approved` on its current content hash (`4e129fbf…`, the v0.1.1 revision) by
        `po-reviewer` and `po-reviewer-two`, both `acceptable` under rubric 0.2.0, so this event
        did not change any pool or sample count. It is now `po-reviewer`'s latest decision on
        that content, and the earlier 0.2.0 events are unchanged;
      * rv-0.1.0-07 / `gj-mem-004` (a calibration item): `rev-2172b02c5ad4` (`40a3d51`), `approve`,
        overall `acceptable`, minor `language_quality` issue, `contrastive_quality:
        not_applicable`, `independent_rating: false` (the owner changed `external_fact_discipline`
        and `contrastive_quality` after the AI second-look discussion). Its `notes` field held a
        stray instruction, so `rev-896e41f5431a` (`7284b5a`) was appended with the intended notes
        and every other field identical; the earlier line is unchanged. The example was already
        `approved` on its current content hash (`3073971d…`) by `po-reviewer` (`excellent`) and
        `po-reviewer-two` (`acceptable`) under rubric 0.2.0, so these events changed no pool or
        sample count. `po-reviewer`'s latest decision on it is now `acceptable`;
      * rv-0.1.0-08 / `gj-goalchg-004`: `rev-f758a292a772` (`2997666`), `approve`, overall
        `excellent`, no issues, `contrastive_quality: not_applicable`, `privacy_and_memory:
        not_applicable`, `independent_rating: false` (the owner changed those two ratings from
        `good` after the AI second-look discussion). It was `pending` and is now `approved`;
      * rv-0.1.0-10 / `gj-clar-008`: `rev-b9fc375fa353` (`301009a`), `approve`, overall
        `excellent`, no issues, `verification_quality`, `evidence_interpretation`,
        `adaptation_quality`, `contrastive_quality` and `privacy_and_memory` all
        `not_applicable`, the other 11 `good`, `independent_rating: false` (the owner changed
        those five from `good` after the AI second-look discussion). It was `pending` and is now
        `approved`;
      * rv-0.1.0-11 / `gj-web-004` (a `web_research_decision`): `rev-f9651cdb0493` (`c7eef17`),
        `approve`, overall `excellent`, no issues. `product_usefulness`, `goal_understanding`,
        `explanation_quality`, `external_fact_discipline`, `safety`, `language_quality` and
        `contrastive_quality` are `good`; `question_minimality`, `actionability`, `realism`,
        `dependency_correctness`, `verification_quality`, `evidence_interpretation`,
        `user_agency`, `adaptation_quality` and `privacy_and_memory` are `not_applicable`.
        `independent_rating: false` (the owner changed seven ratings after the AI second-look
        discussion). Content hash `e3db3ea1…` matched the sampled hash and had no earlier review.
        It was `pending` and is now `approved`;
      * rv-0.1.0-13 / `gj-task-004` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-005`): `rev-ee991d345309` (`b297d91`), `approve`, overall `excellent`,
        `issues: []`. `question_minimality`, `evidence_interpretation`, `user_agency`,
        `adaptation_quality` and `privacy_and_memory` are `not_applicable`; the other 11 are
        `good`. `independent_rating: false` (the owner changed those five from `good` after the AI
        second-look discussion). The reviewed version is the revised content hash `7254399c…`, not
        the sampled `36c5dd1b…`; it had no earlier review and is now `approved`. Its known issues
        `KI-004` and `KI-015` remain `fixed_pending_review` in the sample status;
      * rv-0.1.0-14 / `gj-jour-001` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-017`): `rev-9af791ca3ec1` (`8aa4416`), `revise`, overall `needs_revision`.
        Issues: `realism` minor, `explanation_quality` minor, `external_fact_discipline` major.
        `question_minimality`, `adaptation_quality` and `privacy_and_memory` are `not_applicable`.
        `independent_rating: false` (the owner changed the applicability of those three after the
        AI second-look discussion and confirmed the E/K/L ratings). The reviewed version is the
        revised content hash `b4492d1f…`, not the sampled `77906c26…`; it had no earlier review
        and is now `needs_revision`. `KI-008` remains `open` and `KI-015`
        `fixed_pending_review` in the sample status;
      * rv-0.1.0-15 / `gj-vprot-004` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-016`): `rev-a72d9fb206f1` (`6e92860`), `approve`, overall `excellent`,
        `issues: []`. `question_minimality`, `dependency_correctness`, `adaptation_quality`,
        `contrastive_quality` and `privacy_and_memory` are `not_applicable`; the other 11 are
        `good`. `independent_rating: false` (the owner changed the applicability of those criteria
        after the AI second-look discussion). The reviewed version is the revised content hash
        `555bdf0e…`, not the sampled `b8123766…`; it had no earlier review and is now `approved`.
        Its known issues `KI-014` and `KI-015` remain `fixed_pending_review` in the sample
        status;
      * rv-0.1.0-16 / `gj-task-002` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-021`): `rev-905177337998` (`d876db9`), `revise`, overall `needs_revision`.
        Issues: `realism` minor, `verification_quality` minor. `question_minimality`,
        `user_agency`, `adaptation_quality`, `contrastive_quality` and `privacy_and_memory` are
        `not_applicable`; the other 9 are `good`. `independent_rating: false`. The reviewed
        version is the revised content hash `23c95b15…`, not the sampled `96f0bfce…`; it had no
        earlier review and is now `needs_revision`. `KI-014` and `KI-015` remain
        `fixed_pending_review` in the sample status;
      * rv-0.1.0-17 / `gj-clar-007` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-006`): `rev-f859c085d0a3` (`49fe41f`), `approve`, overall `excellent`,
        `issues: []`. `verification_quality`, `evidence_interpretation`, `adaptation_quality` and
        `privacy_and_memory` are `not_applicable`; the other 12 are `good`.
        `independent_rating: false` (the owner changed the applicability of those criteria after
        the AI second-look discussion). The reviewed version is the revised content hash
        `949f477f…`, not the sampled `a375ae92…`; it had no earlier review and is now `approved`.
        Its known issue `KI-005` remains `fixed_pending_review` in the sample status;
      * rv-0.1.0-18 / `gj-nav-006` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-001`): `rev-411ee8471106` (`e27bb32`), `approve`, overall `excellent`,
        `issues: []`. `question_minimality`, `verification_quality`, `evidence_interpretation` and
        `privacy_and_memory` are `not_applicable`; the other 12, including `adaptation_quality`,
        are `good`. `independent_rating: false` (the owner changed the applicability of those
        criteria after the AI second-look discussion). The reviewed version is the revised content
        hash `626869a7…`, not the sampled `5c93d672…`; it had no earlier review and is now
        `approved`. Its known issue `KI-001` remains `fixed_pending_review` in the sample status.
  * **Independence correction.** `rev-044d69c4953d` was recorded with `independent_rating: true`,
    but the owner had changed `language_quality` from major to minor issues after the AI-copilot
    discussion. The corrective event appends the same final decision with
    `independent_rating: false`; the original line is unchanged. rv-0.1.0-03 keeps
    `independent_rating: true`, because no rating changed there. Across all events:
    `independent_rating` is absent on 16, `true` on 4, `false` on 14 (the two corrective events, rv-0.1.0-05, rv-0.1.0-06, rv-0.1.0-07, rv-0.1.0-08, rv-0.1.0-10, rv-0.1.0-11, rv-0.1.0-13, rv-0.1.0-14, rv-0.1.0-15, rv-0.1.0-16, rv-0.1.0-17 and rv-0.1.0-18).
  * **Counts (`gj review stats`):**
    * pool (93): human-reviewed 22, training-eligible 17, needs_revision 5, not reviewed 71;
    * review sample (30): decided 21, approved 16, needs_revision 5, pending 9
      (`review/review_sample_status_v0.1.1.json`).
  * **Historical calibration (informational in solo mode):** all 8 items rated by both reviewers
    (`po-reviewer-two` from a blind packet). Decision agreement is 7/8 (0.875, κ 0.60) and
    overall-verdict agreement 3/8 (0.375, κ 0.05; it was 2/8 while rv-0.1.0-06 was `po-reviewer`'s
    only 0.2.1 verdict on a calibration item, before rv-0.1.0-07 made their `gj-mem-004` overall
    `acceptable`). The events are unchanged and still count as recorded.
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
  * An append-only, hash-chained decision log (34 events).
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

`make -k check` passes (after the rv-0.1.0-18 review, every target):

* 445 tests passed and 2 skipped (9 in `tests/test_orchestration.py`, 21 in
  `tests/test_solo_review.py`);
* the builder, ledger and sample drift checks;
* reference 106/106, naive 0/106;
* leakage: 0 hard findings;
* `gj review verify-log`: 34 events, 0 errors, 1 warning. The warning is the expected fork left by
  merging two branches that both appended to the log (guide §11).

`gj validate` has 1 warning: gj-vres-007 (KI-033).

## Blockers

1. **Human review is at an early stage.** 34 review events so far. 9 of the 30 sample items and the
   36 ledger revisions (all `pending_human_review`) are not reviewed.
   * `review_all_approved`: 17/93 approved.
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
