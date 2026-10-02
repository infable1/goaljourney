# Active milestone

*Only the active milestone lives here. When it completes, move its summary to `PROJECT_STATE.md`
and `CHANGELOG.md`, then replace this file with the next milestone.*

## Milestone 1.7 — Human Review Round 1 (in progress)

**Status:** in progress. The product owner explicitly directed the project to proceed with
Human Review Round 1 on 2026-09-28. Nothing here trains a model or generates new data.

**Governance change inside this milestone (M1.7a, done 2026-09-29, D-026).** On the owner's
direction, the project moved from **multi-reviewer-first governance** to **solo-owner-first
governance with optional expert escalation**.

* The reason: the project has one owner, and the pairwise gates could be met only by a second person
  it does not have, or by a fabricated identity.
* `configs/review.yaml` `governance.mode: solo_owner`.
* `reviewer_diversity` and `calibration_agreement` are N/A in solo mode.
* The expert tier, the rubric, hash binding and the append-only log are unchanged.
* Pipeline 0.4.0, release gates 1.1.

The tasks and acceptance criteria below are adjusted for solo mode; the multi-reviewer versions
apply only if the mode is switched back.

### Objective

Get the first qualified human decisions on the v0.1.1 data and evaluation references, so the
review-dependent release gates can move. Nothing here trains a model or generates new data.

### Tasks

The column says who performs each task; the agent never records review decisions.

| # | Task | Who |
|---|---|---|
| 1 | Keep one registered owner in `review/reviewers.yaml` (ru + en); register `domain_expert`s only for real, qualified people (owner or others) for expert-tier items | owner |
| 2 | Rate the 8 calibration items (rv-0.1.0-02, -06, -07, -09, -12, -20, -29, -30); items -06 and -20 changed in v0.1.1. In solo mode they are ordinary sample items | owner |
| 3 | Multi-reviewer mode only: check pairwise agreement (κ ≥ 0.40, agreement ≥ 0.75). In solo mode, use the AI copilot to challenge ratings (guide §14) and clarify the rubric where the owner is unsure (guide §15) | owner + agent |
| 4 | Review the 36 ledger revisions (`gj revisions diff ID`) and record `reviewer_status` | reviewers |
| 5 | Decide the open known issues KI-008, KI-012 and KI-033; the agent then applies the decided fixes through the ledger | reviewers → agent |
| 6 | Give dispositions to the 100 evaluation overlaps in `evaluation/leakage/v0.2.0.yaml` (and the 27 in v0.1.0) | reviewers |
| 7 | Review the v0.2.0 reference outputs, longitudinal cases first | reviewers |
| 8 | Confirm POL-A…F, and assign owners for the 5 licensing items | product owner |
| 9 | Prepare review packets and keep the state files current (`/dataset-review`) | agent |

### Acceptance criteria

* Every sample item has a human decision on its current content hash. Expert-tier items without a
  qualified expert are listed as `awaiting_expert` (not training-eligible), never dropped. In
  `multi_reviewer` mode only: `calibration_agreement` passes (every reviewer pair on ≥ 8 shared
  calibration items agrees ≥ 75% with κ ≥ 0.40).
* Every ledger entry has a human `reviewer_status`, and every decided revision is applied and
  recorded, with `gj revisions check` clean.
* KI-008, KI-012 and KI-033 are decided. `validation_strict` passes, or the exception is recorded
  as a decision.
* Every evaluation overlap has a human disposition; `leakage_dispositions` passes or its remaining
  failures are listed.
* `make check` passes; `PROJECT_STATE.md`, this file and `CHANGELOG.md` are updated.

### Progress

As of 2026-09-30, on branch `claude/sleepy-dijkstra-nzrf3t` (not yet merged into the default
branch). The calibration round is recorded, the governance change (M1.7a) is implemented, and
solo-owner review of the rest of the sample is done (22 non-calibration items).
* Task 4 is done: all 36 v0.1.1 ledger revisions are reviewed.
* Task 5 is done: the three selected fixes are applied in dataset v0.1.2 and human-confirmed, so
  KI-008, KI-012 and KI-033 are `fixed`.
* v0.1.2 changed one sample item (rv-0.1.0-14), and it has since been re-decided, so all 30 sample
  items are decided on their current content.
* Task 6 is done. Every evaluation overlap has a human disposition: in v0.1.0, all 27 template
  overlaps and its one seed overlap; in v0.2.0, 100 of 100. `leakage_dispositions` passes.
* Task 7 has started: the reference-review mechanism (D-028, D-029) is in place. All six
  longitudinal cases, all 14 composite cases, `e2-safe-01`…`e2-safe-03`, `e2-mem-01`, `e2-mem-02`,
  `e2-prog-01`, `e2-prog-02`, `e2-clar-01`…`e2-clar-04`, `e2-feas-01` and `e2-feas-02` (76 of 106
  reference outputs) have the owner's review. Four expert-tier cases stay `awaiting_expert` until a
  registered `domain_expert` covers their domain: `e2-long-06` (`safety_policy`), `e2-comp-07`
  (`financial`), `e2-safe-01` and `e2-safe-03` (both `medical`). Eight reference outputs have
  `revise` decisions whose fixes are open: `e2-long-02/s5`, `e2-long-05/s2`, `e2-long-05/s4`,
  `e2-comp-02/s2`, `e2-comp-07/s2`, `e2-comp-14/s1`, `e2-prog-01` and `e2-feas-01`. Task 8 has not
  started, and the milestone is not complete.

* **M1.7a (done).** The solo-owner governance mode is implemented:
  * gate scopes, with N/A reporting that never counts as passed;
  * training-eligibility accounting in release manifests;
  * `--independent-rating`;
  * stats that show the mode;
  * AI copilot and "unsure" guidance (HUMAN_REVIEW_GUIDE §14–17);
  * tests in `tests/test_solo_review.py`.

  No review event, snapshot, release or example was changed.

* **Task 1 (partly done).** Two human dataset reviewers are registered: `po-reviewer` (`fdf6d4c`)
  and `po-reviewer-two` (`c8630b2`, registered at the product owner's request as a separate
  person). Both read ru and en. One owner is enough in solo mode. Both are still `active`, and
  their recorded decisions count; whether `po-reviewer-two` stays active is the owner's decision.
  No `domain_expert` and no `adjudicator` is registered.
* **Task 2 (done).** Both reviewers rated all 8 calibration items; `po-reviewer-two` rated them
  blind from a packet without existing decisions or automated findings. That is 16 calibration
  decisions. The 17th calibration-era event is `po-reviewer`'s approval of `gj-daily-002`, which
  is outside the review sample.
* **Solo-owner sample review (done).** `po-reviewer` reviewed all twenty-two non-calibration items under
  rubric 0.2.1:
  * rv-0.1.0-01 / `gj-feas-005` (`9457084`): approve / acceptable; minor issues on
    `language_quality` and `explanation_quality`;
  * rv-0.1.0-03 / `gj-prog-003` (`9457084`): approve / acceptable; minor issue on
    `explanation_quality`;
  * rv-0.1.0-04 / `gj-route-006` (`5b3f7c4`, `rev-612c1a60c45a`): `revise`, overall
    `needs_revision`, `user_agency: major_issues`, `language_quality: minor_issues`,
    `independent_rating: true`. It is `needs_revision`, so not training-eligible; the fix goes
    through a new `dataset_version` and the ledger;
  * rv-0.1.0-05 / `gj-route-003` (`71c92eb`, `rev-3f360f0323f8`): `approve`, overall
    `excellent`, no issues, `contrastive_quality: good`, `privacy_and_memory: not_applicable`,
    `independent_rating: false`. The owner changed those two ratings after the AI second-look
    discussion, so the flag records provenance; it is not an issue;
  * rv-0.1.0-08 / `gj-goalchg-004` (`2997666`, `rev-f758a292a772`): `approve`, overall
    `excellent`, no issues, `contrastive_quality: not_applicable`, `privacy_and_memory:
    not_applicable`, `independent_rating: false`. The owner changed those two ratings from `good`
    after the AI second-look discussion. It was `pending` and is now `approved`;
  * rv-0.1.0-10 / `gj-clar-008` (`301009a`, `rev-b9fc375fa353`): `approve`, overall `excellent`,
    no issues; `verification_quality`, `evidence_interpretation`, `adaptation_quality`,
    `contrastive_quality` and `privacy_and_memory` are `not_applicable`, the other 11 `good`;
    `independent_rating: false` (the owner changed those five from `good` after the AI
    second-look discussion). It was `pending` and is now `approved`;
  * rv-0.1.0-11 / `gj-web-004` (`c7eef17`, `rev-f9651cdb0493`): a `web_research_decision`,
    `approve`, overall `excellent`, no issues; `external_fact_discipline` and six other criteria
    `good`, nine criteria `not_applicable`; `independent_rating: false` (the owner changed seven
    ratings after the AI second-look discussion). It was `pending` and is now `approved`;
  * rv-0.1.0-13 / `gj-task-004` (`b297d91`, `rev-ee991d345309`): a `highest_risk` item that changed
    since sampling via `REV-0.1.1-005`; `approve`, overall `excellent`, `issues: []`; five criteria
    `not_applicable` (`question_minimality`, `evidence_interpretation`, `user_agency`,
    `adaptation_quality`, `privacy_and_memory`), eleven `good`; `independent_rating: false` (the
    owner changed those five from `good` after the AI second-look discussion). The reviewed
    version is the revised hash `7254399c…`, not the sampled `36c5dd1b…`. It was `pending` and is
    now `approved`; `KI-004` and `KI-015` remain `fixed_pending_review`;
  * rv-0.1.0-14 / `gj-jour-001` (`8aa4416`, `rev-9af791ca3ec1`): a `highest_risk` item that changed
    since sampling via `REV-0.1.1-017`; `revise`, overall `needs_revision`; issues `realism` minor,
    `explanation_quality` minor, `external_fact_discipline` major; `question_minimality`,
    `adaptation_quality` and `privacy_and_memory` `not_applicable`; `independent_rating: false`
    (the owner changed the applicability of those three after the AI second-look discussion and
    confirmed the E/K/L ratings). The reviewed version is the revised hash `b4492d1f…`, not the
    sampled `77906c26…`. It was `pending` and is now `needs_revision`; `KI-008` remains `open` and
    `KI-015` `fixed_pending_review`. Dataset v0.1.2 (REV-0.1.2-001) revised the example for
    KI-008, which covers the `realism` issue. The `explanation_quality` and
    `external_fact_discipline` issues were not part of that fix. The earlier decision stays
    unchanged for `b4492d1f…`. On the new hash `a6b644aa…`, `rev-e9ad553a3e34` (`ffe2432`) is
    `revise`, overall `needs_revision`, with issue `external_fact_discipline` major. C, H, I, J,
    P and Q are `not_applicable`, the other 9 `good`, and `independent_rating: false` (L and the
    applicability of P were changed after the AI second-look). The item went from `pending`
    (`content_changed`) to `needs_revision`;
  * rv-0.1.0-15 / `gj-vprot-004` (`6e92860`, `rev-a72d9fb206f1`): a `highest_risk` item that changed
    since sampling via `REV-0.1.1-016`; `approve`, overall `excellent`, `issues: []`; five criteria
    `not_applicable` (`question_minimality`, `dependency_correctness`, `adaptation_quality`,
    `contrastive_quality`, `privacy_and_memory`), eleven `good`; `independent_rating: false` (the
    owner changed the applicability of those criteria after the AI second-look discussion). The
    reviewed version is the revised hash `555bdf0e…`, not the sampled `b8123766…`. It was
    `pending` and is now `approved`; `KI-014` and `KI-015` remain `fixed_pending_review`;
  * rv-0.1.0-16 / `gj-task-002` (`d876db9`, `rev-905177337998`): a `highest_risk` item that changed
    since sampling via `REV-0.1.1-021`; `revise`, overall `needs_revision`; issues `realism` minor
    and `verification_quality` minor; `independent_rating: false`. The reviewed version is the
    revised hash `23c95b15…`, not the sampled `96f0bfce…`. It was `pending` and is now
    `needs_revision`; `KI-014` and `KI-015` remain `fixed_pending_review`;
  * rv-0.1.0-17 / `gj-clar-007` (`49fe41f`, `rev-f859c085d0a3`): a `highest_risk` item that changed
    since sampling via `REV-0.1.1-006`; `approve`, overall `excellent`, `issues: []`; four criteria
    `not_applicable` (`verification_quality`, `evidence_interpretation`, `adaptation_quality`,
    `privacy_and_memory`), twelve `good`; `independent_rating: false` (the owner changed the
    applicability of those criteria after the AI second-look discussion). The reviewed version is
    the revised hash `949f477f…`, not the sampled `a375ae92…`. It was `pending` and is now
    `approved`; `KI-005` remains `fixed_pending_review`;
  * rv-0.1.0-18 / `gj-nav-006` (`e27bb32`, `rev-411ee8471106`): a `highest_risk` item that changed
    since sampling via `REV-0.1.1-001`; `approve`, overall `excellent`, `issues: []`; four criteria
    `not_applicable` (`question_minimality`, `verification_quality`, `evidence_interpretation`,
    `privacy_and_memory`), twelve `good` including `adaptation_quality`; `independent_rating:
    false` (the owner changed the applicability of those criteria after the AI second-look
    discussion). The reviewed version is the revised hash `626869a7…`, not the sampled
    `5c93d672…`. It was `pending` and is now `approved`; `KI-001` remains `fixed_pending_review`;
  * rv-0.1.0-19 / `gj-time-003` (`8ee6efd`, `rev-d498bb6d343b`): a `highest_risk` item that changed
    since sampling via `REV-0.1.1-007`; `revise`, overall `needs_revision`; issues
    `adaptation_quality` major and `external_fact_discipline` major (hard gate); the other 14
    criteria `good`; `independent_rating: false` (the owner changed J and L and the decision after
    the AI second-look discussion). The reviewed version is the revised hash `e5e92c52…`, not the
    sampled `b5cc77ae…`. It was `pending` and is now `needs_revision`; `KI-007` and `KI-032` remain
    `fixed_pending_review`;
  * rv-0.1.0-21 / `gj-time-004` (`57c78c0`, `rev-7463e20f59e6`): a `highest_risk` item that changed
    since sampling via `REV-0.1.1-003`; `revise`, overall `needs_revision`; issue `realism` major;
    C, G, H, P and Q `not_applicable`, the other 10 `good`; `independent_rating: false`. The
    reviewed version is the revised hash `d8536ef0…`, not the sampled `83f2a3a8…`. It was
    `pending` and is now `needs_revision`; `KI-003` remains `fixed_pending_review`. An append-only
    correction event (`rev-ae41d3818db8`, `8eafa75`) fixed an arithmetic error in the issue text
    and notes (12 + 20 hours is 32, not 27); the original event is unchanged, and the decision,
    ratings and status did not change;
  * rv-0.1.0-22 / `gj-jour-004` (`10a493b`, `rev-3881c74630f9`): a `contrastive` item that changed
    since sampling via `REV-0.1.1-028`; `revise`, overall `needs_revision`; issue
    `goal_understanding` major (a required dinner-for-guests success criterion the user never asked
    for); C, H, I, J and Q `not_applicable`, the other 10 `good`; `independent_rating: false` (the
    owner changed B, the applicability of C, H, I, J and Q, and the decision after the AI
    second-look discussion). The reviewed version is the revised hash `dd7a3b8f…`, not the sampled
    `87549836…`. It was `pending` and is now `needs_revision`; `KI-013` remains
    `fixed_pending_review`;
  * rv-0.1.0-23 / `gj-feas-006` (`b7d1c5c`, `rev-fa531d93252b`): a `contrastive` item, unchanged
    since sampling (no ledger revision, no known issue); `revise`, overall `needs_revision`; issue
    `external_fact_discipline` major (an unverified general claim about associate-level cloud
    architecture exam requirements and typical preparation time, with no named certification);
    F, G, H, J and Q `not_applicable`, the other 10 `good`; `independent_rating: false` (the owner
    changed L, the applicability of F, G, H, J and Q, and the decision after the AI second-look
    discussion). The reviewed version is the sampled hash `67e429ff…`. It was `pending` and is now
    `needs_revision`;
  * rv-0.1.0-24 / `gj-vres-004` (`26e98e5`, `rev-aa592a3163df`; correction `212cf67`,
    `rev-07d13934c996`): a `contrastive` item that changed since sampling via `REV-0.1.1-031` (no
    known issue); `approve`, overall `excellent`, no issues; C, F, J and Q `not_applicable`, the
    other 12 `good`. The original event was recorded with `independent_rating: true`, which was
    wrong, because the owner changed the applicability of C, F, J and Q after the AI second-look
    discussion. The append-only corrective event repeats the same decision, content hash, ratings
    and empty issue list with `independent_rating: false`; the original event is unchanged. The
    effective latest decision is `approve` / `excellent` with `independent_rating: false`. The
    reviewed version is the revised hash `356dc499…`, not the sampled `2cbbbe61…`. It was
    `pending` and is now `approved`;
  * rv-0.1.0-25 / `gj-vprot-005` (`1e2e9b2`, `rev-8c9847364149`): a `contrastive` item, unchanged
    since sampling (no ledger revision, no known issue); `approve`, overall `excellent`, no issues;
    C, F, H, I, J and Q `not_applicable`, the other 10 `good`; `independent_rating: false` (the
    owner changed the applicability of C, F, H, I, J and Q after the AI second-look discussion).
    The reviewed version is the sampled hash `67b754a0…`. It was `pending` and is now `approved`;
  * rv-0.1.0-26 / `gj-clar-006` (`3af4cae`, `rev-5cd828a81332`): a `contrastive` item, unchanged
    since sampling (no ledger revision, no known issue); `approve`, overall `excellent`, no issues;
    G, H, J and Q `not_applicable`, the other 12 `good`; `independent_rating: false` (the owner
    changed the applicability of G, H, J and Q after the AI second-look discussion). The reviewed
    version is the sampled hash `3a263322…`. It was `pending` and is now `approved`;
  * rv-0.1.0-27 / `gj-vretry-002` (`73c22db`, `rev-aeb597251ce5`): a `contrastive` item, unchanged
    since sampling (no ledger revision, no known issue); `approve`, overall `excellent`, no issues;
    C, F, J and Q `not_applicable`, the other 12 `good`; `independent_rating: false` (the owner
    changed the applicability of C, F, J and Q after the AI second-look discussion). The reviewed
    version is the sampled hash `9690cc62…`. It was `pending` and is now `approved`;
  * rv-0.1.0-28 / `gj-safe-002` (`2f2511f`, `rev-fef976fb4399`): an `edge` item, expert tier
    (`financial`), unchanged since sampling (no ledger revision); `revise`, overall
    `needs_revision`; issue `external_fact_discipline` major (an unsupported claim that repaying
    about 300,000 of credit-card debt within a year is "quite achievable"); C, D, E, F, G, H, J and
    Q `not_applicable`, the other 7 `good`; `independent_rating: false` (the owner changed L, the
    applicability of C, D, E, F, G, H, J and Q, and the decision after the AI second-look
    discussion). The reviewed version is the sampled hash `5d0d0c50…`. It was `pending` and is now
    `needs_revision`; `KI-022` (low) remains `open`. Approving a revised version will still need
    `financial` sign-off.

  With rv-0.1.0-28 the 30-item sample is fully decided: every item has a human decision on its
  current content hash (20 `approved`, 10 `needs_revision`, none `pending` or `awaiting_expert`).

  `po-reviewer` also re-reviewed two calibration items under rubric 0.2.1:
  * rv-0.1.0-06 / `gj-time-001` (`8deff75`, `rev-1584bfb68001`): `approve`, overall `excellent`,
    no issues, `contrastive_quality: good`, `privacy_and_memory: not_applicable`,
    `independent_rating: false` (the owner changed `privacy_and_memory` after the AI second-look
    discussion). The item was already `approved` on its current content hash (`4e129fbf…`, the
    v0.1.1 revision) by both reviewers under rubric 0.2.0, so this event changed no pool or sample
    count. It is now `po-reviewer`'s latest decision on that content; the earlier events are
    unchanged.
  * rv-0.1.0-07 / `gj-mem-004` (`40a3d51`, `rev-2172b02c5ad4`): calibration item, `approve`,
    overall `acceptable`, minor `language_quality` issue, `contrastive_quality: not_applicable`,
    `independent_rating: false` (the owner changed `external_fact_discipline` and
    `contrastive_quality` after the AI second-look discussion). The `notes` field held a stray
    instruction, so `rev-896e41f5431a` (`7284b5a`) was appended with the intended notes and every
    other field identical; the earlier line is unchanged. The item was already `approved` on its
    current content hash (`3073971d…`) by both reviewers under rubric 0.2.0, so these events
    changed no pool or sample count.

  **Independence correction.** rv-0.1.0-01 was first recorded with `independent_rating: true`
  (`rev-044d69c4953d`). The owner had changed `language_quality` from major to minor issues after
  the AI-copilot discussion, so a corrective event (`rev-a1a061cc1487`) appends the same final
  decision with `independent_rating: false`. The original line is unchanged, and its latest
  decision is still approve / acceptable. rv-0.1.0-03 keeps `independent_rating: true`.

  The log now holds 46 events (`gj review verify-log`: 0 errors).
  * Pool (93): human-reviewed 31, training-eligible 21, needs_revision 10, content changed 0,
    not reviewed 62.
  * Sample (30): decided 30, approved 20, needs_revision 10, pending 0.
* **Task 3 (historical; N/A in solo mode).** Agreement on the decision is 7/8 (0.875), κ 0.60.
  That would pass `calibration_agreement` in `multi_reviewer` mode; in solo mode the gate is N/A.
  Agreement on the overall verdict is 3/8 (κ 0.05; it was 2/8 while rv-0.1.0-06 stood alone, before rv-0.1.0-07); the gap is mostly `excellent` against
  `acceptable`.
  * rv-0.1.0-02 / `gj-safe-003` (`high_risk`): `po-reviewer` chose revise and `po-reviewer-two`
    approve, so the item stays `needs_revision` (the most conservative decision wins). In solo mode no
    adjudicator is needed: a later `po-reviewer` decision replaces their own earlier one. An
    adjudication record (for multi-reviewer mode) is prepared but **not recorded**, because no
    adjudicator is registered. It proposes approve, overall excellent, A, B,
    I, K, L, M, N, P `good`, reasoned from the `high_risk` rule in DATASET_SPEC §9. It lives in
    `scratch/review/adjudication_rv-0.1.0-02.yaml`, which is git-ignored, so it must be prepared
    again if the working copy is lost. Even when recorded, an adjudicator without `medical` and
    `physical_safety` leaves the item `pending` (`awaiting_expert`).
  * rv-0.1.0-30 / `gj-safe-006` (`restricted`): both reviewers chose revise (external-fact
    discipline, a hard gate). The fix goes through a new `dataset_version` and the ledger, then a new
    review with `legal` sign-off.
  * Rubric 0.2.1 (D-025, `6ece224`) clarifies the safety anchor for restricted goals. The 17
    calibration-era events are stamped 0.2.0; the 29 solo-owner events are stamped 0.2.1.
* **Task 4 (done for v0.1.1).** On the owner's direction, ledger decisions are recorded with
  `gj revisions review` (D-027, schema 0.1.2, `d1d848d`). `po-reviewer` reviewed all 36 v0.1.1
  entries (`d1d848d`…`8c5d690`): 33 `confirmed`, 3 `disputed` (REV-0.1.1-002, -003, -011;
  `independent_rating: false`). The disputed corrections still need new content in a later version.
  Separately, `gj-time-001` (REV-0.1.1-002) is still `approved` as an example from rv-0.1.0-06,
  because a ledger decision does not change an example's status.
* **Task 5 (done: decided, applied and confirmed).** On 2026-09-30 the owner chose KI-008
  option B, KI-012 option A and KI-033 option A. Dataset v0.1.2 (base v0.1.1, draft release)
  implements them:
  * REV-0.1.2-001 / `gj-jour-001`: 10 h/week kept. The weekly time the learning tasks leave is
    planned as job-search time (background nodes n17–n19, first-interview node n16, estimates on
    n14 and n15, pacing notes), and `a4` unlocks on n16.
  * REV-0.1.2-002 / `gj-goalchg-001`: the message asks for the current 7 km time before judging
    December 1. `minor_adjustment` is kept.
  * REV-0.1.2-003 / `gj-vres-007`: the follow-up question is a required method, and the expected
    output asks for its answer.

  On 2026-10-01 `po-reviewer` confirmed all three corrections (`independent_rating: true`,
  `8c90b42`…`4500616`). The issues are now `fixed` with `human_review: confirmed` in
  `review/known_issues_v0.1.2.yaml`. Pipeline 0.4.2 judges the released v0.1.1 ledger and sample
  status against the v0.1.1 release, so they stay valid unchanged. Separately, the example-level
  review of `gj-jour-001` (rv-0.1.0-14) is `needs_revision` on its v0.1.2 content because of its
  `external_fact_discipline` issue, which is independent of KI-008.
* **Task 6 (done).** On 2026-10-01 `po-reviewer` decided Batch 1 in
  `evaluation/leakage/v0.1.0.yaml`: 5 strong overlaps are `accept_in_distribution`, retained and
  reported in the in-template evaluation slice:
  * `ev-ra-01` ↔ `gj-time-003`;
  * `ev-vr-04` ↔ `gj-vretry-002`;
  * `ev-vr-01` ↔ `gj-vres-002`;
  * `ev-vr-02` ↔ `gj-vres-004`;
  * `ev-v-02` ↔ `gj-vprot-005`.

  The agent's `proposed_disposition` values are kept unchanged; for four of the five it was
  `rewrite_eval_case`. Batch 2 (same day, same disposition) covers 5 more strong overlaps:
  * `ev-p-01` ↔ `gj-prog-002`;
  * `ev-m-01` ↔ `gj-mem-003`, `gj-lang-001`;
  * `ev-m-02` ↔ `gj-mem-001`;
  * `ev-f-01` ↔ `gj-feas-006`, `gj-feas-001`;
  * `ev-wr-03` ↔ `gj-web-004`.

  Here `proposed_disposition` was `rewrite_eval_case` for `ev-p-01` and `ev-m-02` and is unchanged.
  Batch 3 (same day, same disposition) covers 1 strong and 4 medium overlaps:
  * `ev-dp-01` ↔ `gj-daily-003`, `gj-daily-001`;
  * `ev-n-01` ↔ `gj-nav-002`;
  * `ev-n-03` ↔ `gj-nav-007`;
  * `ev-n-02` ↔ `gj-nav-008`, `gj-nav-011`;
  * `ev-s-01` ↔ `gj-safe-004`, `gj-safe-008`.

  All five match `proposed_disposition`. Batch 4 (same day, same disposition) covers 5 medium
  overlaps:
  * `ev-s-02` ↔ `gj-safe-006`;
  * `ev-s-04` ↔ `gj-safe-001`;
  * `ev-gc-01` ↔ `gj-goalchg-004`, `gj-goalchg-002`;
  * `ev-vr-03` ↔ `gj-vres-005`, `gj-vretry-001`;
  * `ev-v-01` ↔ `gj-vprot-002`.

  All five match `proposed_disposition`. Batch 5 (same day, same disposition) covers 4 medium
  overlaps and 1 coincidental automated candidate (`strength: none`):
  * `ev-t-01` ↔ `gj-task-001`, `gj-task-003`;
  * `ev-wr-01` ↔ `gj-web-004`, `gj-web-001`;
  * `ev-l-01` ↔ `gj-lang-002`, `gj-nav-001`;
  * `ev-q-01` ↔ `gj-clar-002`;
  * `ev-j-01` ↔ `gj-jour-002` (candidate).

  All five match `proposed_disposition`. Batch 6 (same day, same disposition) covers the last two:
  * `ev-p-01` ↔ `gj-prog-003` (coincidental automated candidate);
  * `ev-ra-02` ↔ `gj-feas-006` (topic-only).

  Both match `proposed_disposition`.

  **The v0.1.0 part is complete.** All 27 template overlaps are `accept_in_distribution`, decided
  by `po-reviewer`. Six of these decisions differ from a `rewrite_eval_case` proposal, which is kept
  unchanged.

  The file's one seed overlap is separate from the 27 template overlaps: `sc-pd-001` ↔ `ev-wr-02`.
  On 2026-10-01 `po-reviewer` set it to `accept_in_distribution`, and the proposed `change_seed` is
  kept unchanged. Schema 0.1.2 has no `note` field for seed overlaps, so the owner's note is
  recorded here:
  > Seed-level lexical overlap is retained as in-distribution; the evaluation case remains valid,
  > and the overlap should be reported separately from template-overlap results.

  v0.1.0 therefore has no `open` disposition.

  **v0.2.0 Batch 1 (2026-10-01).** `po-reviewer` set 10 strong set-up or intermediate-step overlaps
  to `accept_in_distribution`, reported in the in-template slice. All ten match
  `proposed_disposition`:
  * `e2-comp-06/s1` ↔ `gj-web-001`;
  * `e2-comp-07/s1` ↔ `gj-safe-002`;
  * `e2-comp-08/s1` ↔ `gj-mem-001`;
  * `e2-comp-12/s1` ↔ `gj-daily-002`;
  * `e2-comp-13/s1` ↔ `gj-web-004`;
  * `e2-comp-14/s1` ↔ `gj-feas-001`, `gj-feas-003`;
  * `e2-long-01/s7` ↔ `gj-vres-001`;
  * `e2-long-02/s3` ↔ `gj-task-002`;
  * `e2-long-04/s4` ↔ `gj-mem-002`;
  * `e2-long-06/s1` ↔ `gj-safe-007`.

  `gj eval build-cases` re-dumps this whole file. Dispositions are therefore written through the
  builder's own YAML writer, and `gj eval build-cases --check` stays clean.

  **v0.2.0 Batch 2 (same day, same disposition).** 1 strong and 9 medium overlaps, all matching
  `proposed_disposition`. With it, all 11 strong v0.2.0 overlaps are decided:
  * `e2-long-06/s2` ↔ `gj-web-003`;
  * `e2-clar-01` ↔ `gj-clar-008`;
  * `e2-clar-02` ↔ `gj-clar-004`;
  * `e2-clar-03` ↔ `gj-clar-007`, `gj-mem-002`;
  * `e2-clar-04` ↔ `gj-clar-007`;
  * `e2-feas-01` ↔ `gj-feas-001`, `gj-feas-006`;
  * `e2-feas-02` ↔ `gj-feas-004`;
  * `e2-feas-03` ↔ `gj-feas-005`, `gj-web-004`;
  * `e2-jour-01` ↔ `gj-jour-003`, `gj-jour-002`;
  * `e2-task-01` ↔ `gj-task-003`.

  **v0.2.0 Batch 3 (same day, same disposition).** 10 medium overlaps, all matching
  `proposed_disposition`. The coincidental candidates `e2-task-02` ↔ `gj-task-004` and
  `e2-vres-06` ↔ `gj-vres-005` are separate entries and stay `open`:
  * `e2-task-02` ↔ `gj-task-003`;
  * `e2-vprot-01` ↔ `gj-vprot-001`;
  * `e2-vprot-02` ↔ `gj-vprot-004`;
  * `e2-vprot-03` ↔ `gj-vprot-003`;
  * `e2-vres-01` ↔ `gj-vres-003`;
  * `e2-vres-03` ↔ `gj-vres-002`;
  * `e2-vres-04` ↔ `gj-vres-007`;
  * `e2-vres-05` ↔ `gj-vretry-002`, `gj-vretry-004`;
  * `e2-vres-06` ↔ `gj-vretry-003`, `gj-vres-001`;
  * `e2-route-01` ↔ `gj-time-003`, `gj-time-001`.

  **v0.2.0 Batch 4 (same day, same disposition).** 10 medium overlaps, all matching
  `proposed_disposition`. The topic-only entry `e2-gc-02` ↔ `gj-daily-003` is separate and stays
  `open`:
  * `e2-route-02` ↔ `gj-route-004`;
  * `e2-route-04` ↔ `gj-nav-006`;
  * `e2-route-05` ↔ `gj-route-002`;
  * `e2-daily-01` ↔ `gj-daily-003`, `gj-daily-002`;
  * `e2-daily-02` ↔ `gj-daily-001`;
  * `e2-nav-02` ↔ `gj-nav-002`;
  * `e2-nav-03` ↔ `gj-nav-006`;
  * `e2-nav-04` ↔ `gj-nav-008`, `gj-nav-011`;
  * `e2-gc-01` ↔ `gj-goalchg-001`;
  * `e2-gc-02` ↔ `gj-goalchg-001`.

  **v0.2.0 Batch 5 (same day, same disposition).** 10 medium composite-step overlaps, all matching
  `proposed_disposition`. The coincidental candidate `e2-comp-05/s2` ↔ `gj-task-002` is separate
  and stays `open`:
  * `e2-comp-01/s1` ↔ `gj-clar-007`;
  * `e2-comp-01/s2` ↔ `gj-jour-002`;
  * `e2-comp-02/s1` ↔ `gj-task-003`;
  * `e2-comp-02/s2` ↔ `gj-vres-003`;
  * `e2-comp-03/s1` ↔ `gj-vres-002`;
  * `e2-comp-03/s2` ↔ `gj-vretry-001`;
  * `e2-comp-04/s1` ↔ `gj-nav-006`;
  * `e2-comp-04/s2` ↔ `gj-daily-002`;
  * `e2-comp-05/s1` ↔ `gj-nav-005`;
  * `e2-comp-05/s2` ↔ `gj-task-003`.

  **v0.2.0 Batch 6 (same day, same disposition).** 10 medium composite-step overlaps, all matching
  `proposed_disposition`. The coincidental candidates `e2-comp-08/s2` ↔ `gj-task-002` and
  `e2-comp-11/s1` ↔ `gj-vres-005` are separate and stay `open`:
  * `e2-comp-06/s2` ↔ `gj-feas-004`;
  * `e2-comp-07/s2` ↔ `gj-jour-005`;
  * `e2-comp-08/s2` ↔ `gj-task-003`;
  * `e2-comp-09/s1` ↔ `gj-vres-003`;
  * `e2-comp-09/s2` ↔ `gj-vretry-002`, `gj-nav-002`;
  * `e2-comp-10/s1` ↔ `gj-goalchg-002`;
  * `e2-comp-10/s2` ↔ `gj-route-006`;
  * `e2-comp-11/s1` ↔ `gj-vres-001`;
  * `e2-comp-11/s2` ↔ `gj-prog-001`;
  * `e2-comp-12/s2` ↔ `gj-daily-001`.

  **v0.2.0 Batch 7 (same day, same disposition, `po-reviewer`).** 8 medium longitudinal-step
  overlaps and 2 topic-only overlaps, all matching `proposed_disposition`. The notes are the
  owner's supplied wording:
  * `e2-long-04/s2` ↔ `gj-mem-004`, `gj-mem-003`;
  * `e2-long-04/s5` ↔ `gj-lang-001`;
  * `e2-long-05/s2` ↔ `gj-time-003`;
  * `e2-long-05/s4` ↔ `gj-time-004`;
  * `e2-long-05/s5` ↔ `gj-prog-001`;
  * `e2-long-06/s3` ↔ `gj-feas-004`;
  * `e2-long-06/s4` ↔ `gj-goalchg-004`;
  * `e2-long-06/s5` ↔ `gj-route-006`;
  * `e2-nav-05` ↔ `gj-vprot-001` (topic-only);
  * `e2-gc-02` ↔ `gj-daily-003` (topic-only).

  **v0.2.0 Batch 8 (same day, same disposition, `po-reviewer`).** 10 medium overlaps, all matching
  `proposed_disposition`. The notes are the owner's wording:
  * `e2-web-01` ↔ `gj-web-001`;
  * `e2-web-02` ↔ `gj-web-002`, `gj-web-005`;
  * `e2-safe-01` ↔ `gj-safe-002`, `gj-jour-005`;
  * `e2-safe-02` ↔ `gj-safe-001`;
  * `e2-safe-03` ↔ `gj-safe-006`;
  * `e2-mem-01` ↔ `gj-mem-002`, `gj-mem-001`;
  * `e2-prog-01` ↔ `gj-prog-002`;
  * `e2-comp-13/s2` ↔ `gj-route-002`;
  * `e2-long-01/s1` ↔ `gj-clar-001`;
  * `e2-long-01/s2` ↔ `gj-clar-007`.

  **v0.2.0 Batch 9 (same day, same disposition, `po-reviewer`).** 10 medium longitudinal-step
  overlaps, all matching `proposed_disposition`. The notes are the owner's wording. The
  coincidental candidate `e2-long-01/s6` ↔ `gj-task-005` is separate and stays `open`:
  * `e2-long-01/s3` ↔ `gj-clar-004`, `gj-clar-007`;
  * `e2-long-01/s5` ↔ `gj-time-001`;
  * `e2-long-01/s6` ↔ `gj-task-003`;
  * `e2-long-01/s8` ↔ `gj-time-002`;
  * `e2-long-01/s9` ↔ `gj-daily-001`;
  * `e2-long-02/s1` ↔ `gj-clar-006`;
  * `e2-long-02/s5` ↔ `gj-time-001`;
  * `e2-long-02/s6` ↔ `gj-daily-002`;
  * `e2-long-03/s2` ↔ `gj-vres-003`;
  * `e2-long-03/s4` ↔ `gj-nav-002`.

  **v0.2.0 Batch 10 (same day, same disposition, `po-reviewer`).** The last 10 overlaps, all
  matching `proposed_disposition`. The notes are the owner's wording. These are 1 medium overlap,
  2 topic-only overlaps and the 7 coincidental automated candidates (`strength: none`), whose
  decided siblings for the same eval ids are unchanged:
  * `e2-long-03/s5` ↔ `gj-prog-002`;
  * `e2-prog-02` ↔ `gj-prog-001` (topic-only);
  * `e2-long-03/s1` ↔ `gj-vprot-005` (topic-only);
  * `e2-comp-05/s2` ↔ `gj-task-002` (candidate);
  * `e2-comp-08/s2` ↔ `gj-task-002` (candidate);
  * `e2-comp-11/s1` ↔ `gj-vres-005` (candidate);
  * `e2-comp-14/s2` ↔ `gj-jour-005` (candidate);
  * `e2-long-01/s6` ↔ `gj-task-005` (candidate);
  * `e2-task-02` ↔ `gj-task-004` (candidate);
  * `e2-vres-06` ↔ `gj-vres-005` (candidate).

  **Task 6 is complete.** All 100 v0.2.0 overlaps are `accept_in_distribution`, decided by
  `po-reviewer`: 11 strong, 78 medium, 4 topic-only and 7 coincidental. `proposed_disposition` is
  unchanged throughout. `gj leakage` reports 0 overlaps without a human disposition, and the
  `leakage_dispositions` gate now passes.
* **Task 7 (in progress).** On 2026-10-01 the owner made two decisions (D-028):
  * in `solo_owner` mode one registered owner completes the review of a reference output;
  * the review is stored inside the evaluation case.

  Schema 0.1.3 adds the case-level `reference_review` block. It holds append-only sessions with one
  hash-bound decision per reference output: `action`, `overall`, `issues` and `notes`, with no
  criterion ratings. `reference_status` is derived from these decisions. Pipeline 0.4.3 adds:
  * `gj eval review-reference`, which writes the decisions through the builder;
  * builder carry-over of the block;
  * validator checks.

  The evaluation and dataset versions are unchanged. Releases v0.1.1 and v0.1.2 keep their build-time
  review state, and the v0.1.2 release still rebuilds from its own inputs.

  The first review, recorded as given: `e2-long-01`, all 9 steps `approve` / `excellent`, no issues,
  no notes, `po-reviewer`, `independent_rating: true` (the AI second look changed nothing). The case
  is `human_reviewed`.

  The second review, on 2026-10-02, recorded as given: `e2-long-02`, `po-reviewer`,
  `independent_rating: false` (one decision changed after the AI second look).
  * s1–s4 and s6: `approve` / `excellent`, no issues.
  * s5: `revise` / `needs_revision`, with one `major` issue: the reference's remaining workload is
    arithmetically inconsistent. The prose says about 6 h while the listed tasks total 5 h, and
    `remaining_minutes_before: 360` / `weeks_needed: 1.3` do not agree at 3 h/week. The notes record
    the criterion (planning_quality / arithmetic consistency) and that the route-adaptation logic is
    usable.

  The case is `human_reviewed`: every reference output has a decision, and s5's decision is `revise`.
  The s5 fix is open. Changing a v0.2.0 reference means a new `evaluation_version`, because the set is
  inside a release.

  The third review, on 2026-10-02, recorded as given: `e2-long-03`, all 5 steps `approve` /
  `excellent`, no issues, no notes, `po-reviewer`, `independent_rating: true`. The case is
  `human_reviewed`.

  The fourth review, on 2026-10-02, recorded as given: `e2-long-04`, all 5 steps `approve` /
  `excellent`, no issues, no notes, `po-reviewer`, `independent_rating: true`. The case is
  `human_reviewed`.

  The fifth review, on 2026-10-02, recorded as given: `e2-long-05`, `po-reviewer`,
  `independent_rating: false` (s2 and s4 changed after the AI second look).
  * s1, s3 and s5: `approve` / `excellent`, no issues.
  * s2 and s4: `revise` / `needs_revision`, each with one `major` issue. The derived `weeks_needed` is
    inconsistent with `remaining_minutes_after` at `weekly_hours: 5`: 1380 min implies about 4.6
    weeks, not 6.4 (s2), and 780 min about 2.6 weeks, not 1.2 (s4). The notes record the criterion
    (planning_quality / numeric consistency).

  The case is `human_reviewed`, and the s2 and s4 fixes are open (a new `evaluation_version`, as for
  `e2-long-02/s5`).

  On 2026-10-02 the owner decided that an owner's review of an expert-tier reference is recorded and
  waits for the expert (D-029). Schema 0.1.3 gains the `awaiting_expert` status, and sessions now carry
  the reviewer's roles and expert domains (an additive change; the earlier sessions are untouched).

  The sixth review, recorded as given: `e2-long-06`, all 5 steps `approve` / `excellent`, no issues,
  no notes, `po-reviewer` (roles `dataset_reviewer`, no expert domains), `independent_rating: true`.
  The case is expert-tier (`high_risk`, `safety_policy`), so it is `awaiting_expert`. No expert
  qualification was claimed or created, and it becomes `human_reviewed` only when a registered
  `domain_expert` for `safety_policy` decides every reference output.

  The first composite case, recorded as given on 2026-10-02: `e2-comp-01`, s1 and s2 `approve` /
  `excellent`, no issues, no notes, `po-reviewer`, `independent_rating: true`. The case is
  `human_reviewed`.

  The second composite case, recorded as given on 2026-10-02: `e2-comp-02`, `po-reviewer`,
  `independent_rating: false` (s2 changed after the AI second look).
  * s1: `approve` / `excellent`, no issues.
  * s2: `revise` / `needs_revision`, with one `major` issue. The reference's next step says one more
    drill at 95% or above completes the task, but the protocol requires 95% in every drill and the
    export already holds a 94.1% drill; the fix is a repeat or replacement drill that brings the
    full set into compliance. The notes record the criterion (verification_quality / consistency
    with the acceptance criterion).

  The case is `human_reviewed`, and the s2 fix is open (a new `evaluation_version`, as for the
  other revise decisions).

  The third composite case, recorded as given on 2026-10-02: `e2-comp-03`, s1 and s2 `approve` /
  `excellent`, no issues, no notes, `po-reviewer`, `independent_rating: true`. The case is
  `human_reviewed`.

  The fourth composite case, recorded as given on 2026-10-02: `e2-comp-04`, s1 and s2 `approve` /
  `excellent`, no issues, no notes, `po-reviewer`, `independent_rating: true`. The case is
  `human_reviewed`.

  The fifth composite case, recorded as given on 2026-10-02: `e2-comp-05`, s1 and s2 `approve` /
  `excellent`, no issues, no notes, `po-reviewer`, `independent_rating: true`. The case is
  `human_reviewed`.

  The sixth composite case, recorded as given on 2026-10-02: `e2-comp-06`, s1 and s2 `approve` /
  `excellent`, no issues, no notes, `po-reviewer`, `independent_rating: true`. The case is
  `human_reviewed`.

  Three more composite cases, recorded as given on 2026-10-02 by `po-reviewer`:
  * `e2-comp-07` (finance, expert-tier `financial`), `independent_rating: false` (s2 changed after
    the AI second look). s1: `approve` / `excellent`, no issues. s2: `revise` / `needs_revision`,
    with one `major` issue: `decision_summary.why` says the admin takes about 30 minutes a week on
    average, but the route's `n5` (400 min) and `n6` (320 min) give 720 minutes over the 81-week
    horizon, about 8.9 minutes a week; the "about 40 minutes" monthly check-in is consistent. The
    notes record the criterion (planning_quality / numeric consistency). The case is
    `awaiting_expert`: the owner's review claims no expert qualification, and `financial` coverage
    from a registered `domain_expert` is missing. The s2 fix is open (a new `evaluation_version`).
  * `e2-comp-08` and `e2-comp-09`: s1 and s2 `approve` / `excellent`, no issues, no notes,
    `independent_rating: true`. Both cases are `human_reviewed`.

  Three more, recorded as given on 2026-10-02: `e2-comp-10`, `e2-comp-11` and `e2-comp-12`, each
  with s1 and s2 `approve` / `excellent`, no issues, no notes, `po-reviewer`,
  `independent_rating: true`. All three are human-tier and `human_reviewed`.

  Three more, recorded as given on 2026-10-02 by `po-reviewer`:
  * `e2-comp-13`: s1 and s2 `approve` / `excellent`, no issues, no notes,
    `independent_rating: true`. The case is `human_reviewed`.
  * `e2-comp-14`, `independent_rating: false` (s1 changed after the AI second look:
    unsupported_generalisation, P7). s1: `revise` / `needs_revision`, with one `minor` issue: the
    reference generalises, unsupported, that an 80,000-word draft usually needs several times the
    roughly 25 available writing hours; the fix is to remove it or mark it as an estimate. The
    issue schema has no notes field, so on the owner's instruction the criterion is in s1's notes
    ("Criterion: unsupported_generalisation / P7"). s2: `approve` / `excellent`. The case is
    `human_reviewed`, and the s1 fix is open (a new `evaluation_version`).
  * `e2-safe-01` (atomic, health, expert-tier `medical`): `approve` / `excellent`, no issues, no
    notes, `independent_rating: true`. The case is `awaiting_expert`: no expert qualification was
    claimed, and `medical` coverage from a registered `domain_expert` is missing.

  Three more atomic cases, recorded as given on 2026-10-02 by `po-reviewer`, each `approve` /
  `excellent`, no issues, no notes, `independent_rating: true`:
  * `e2-safe-02` (home, `allowed`, human-tier): `human_reviewed`.
  * `e2-safe-03` (health, `restricted`, expert-tier `medical`): `awaiting_expert`. No expert
    qualification was claimed, and `medical` coverage from a registered `domain_expert` is missing.
  * `e2-mem-01` (personal development, `allowed`, human-tier): `human_reviewed`.

  Three more atomic cases, recorded as given on 2026-10-02 by `po-reviewer` (all human-tier):
  * `e2-mem-02`: `approve` / `excellent`, no issues, no notes, `independent_rating: true`.
    `human_reviewed`.
  * `e2-prog-01`, `independent_rating: false`: `revise` / `needs_revision`, with one `minor` issue:
    `goal_progress.percent` is 15, but its own basis (2 of 4 practice tasks verified) gives 50%; the
    fix is 50, or a basis that really gives 15%. Notes: "Manual second-look: numeric consistency".
    `human_reviewed`, and the fix is open (a new `evaluation_version`).
  * `e2-prog-02`: `approve` / `excellent`, no issues, no notes, `independent_rating: true`.
    `human_reviewed`.

  Three more atomic cases, recorded as given on 2026-10-02 by `po-reviewer`: `e2-clar-01`,
  `e2-clar-02` and `e2-clar-03`, each `approve` / `excellent`, no issues, no notes,
  `independent_rating: true`. All three are human-tier and `human_reviewed`.

  Three more atomic cases, recorded as given on 2026-10-02 by `po-reviewer` (all human-tier):
  * `e2-clar-04`: `approve` / `excellent`, no issues, no notes, `independent_rating: true`.
    `human_reviewed`.
  * `e2-feas-01`, `independent_rating: false`: `revise` / `needs_revision`, with one `minor` issue:
    an unsupported generalisation that pieces, scales and sight-reading at this level usually take
    years of regular practice; the fix is to remove it or base the estimate only on the case's
    known data. Notes: "Manual second-look: unsupported_generalisation / P7". `human_reviewed`,
    and the fix is open (a new `evaluation_version`).
  * `e2-feas-02`: `approve` / `excellent`, no issues, no notes, `independent_rating: true`.
    `human_reviewed`.

  All 14 composite cases are reviewed. The other 30 cases (30 reference outputs, all atomic) are
  `draft_unreviewed`.
* **Task 8 (not started).** POL-A…F and the licensing owners are unconfirmed.
* **Task 9 (ongoing).** The blind calibration packet was prepared (in `scratch/`, git-ignored). The
  sample status file was regenerated with each recorded decision (latest: v0.1.2,
`review/review_sample_status_v0.1.2.json`; the
  independence correction `2438dd4` left it unchanged), and these state files were synchronised with
  `gj review stats`.

Acceptance criteria:
* **Met:** KI-008, KI-012 and KI-033 are decided, applied and human-confirmed (`fixed`), and
  `validation_strict` passes on v0.1.2.
* **Sample part met again:** every sample item has a human decision on its current content (30
  of 30; rv-0.1.0-14 was re-decided on v0.1.2), and none is `awaiting_expert`.
* **Open:** every ledger entry has a human status (v0.1.1: 33 confirmed, 3 disputed; v0.1.2: 3
  confirmed), but the 3 disputed v0.1.1 corrections are not re-applied yet.
* **Met:** every evaluation overlap has a human disposition (v0.1.0: 27 of 27 template overlaps
  and the 1 seed overlap; v0.2.0: 100 of 100), and `leakage_dispositions` passes.
* **Open:** the final `make check` and state-file updates at completion.
* **N/A in solo mode:** the multi-reviewer criterion, `calibration_agreement`.

Gates (`gj gates`, v0.1.2, solo_owner): 5 of 9 applicable pass (`findings_acknowledged`,
`leakage_hard_clean`, `leakage_dispositions`, `validation_strict`, `known_issues_closed`), and 2
are N/A (`reviewer_diversity`, `calibration_agreement`). Still failing: `review_all_approved`,
`coverage_minimums`, `eval_readiness` (63/200 cases) and `licensing_resolved`. `known_issues_closed` passes because the gate
counts only `open` issues; KI-008 and KI-012 are `fixed`, and no medium or high issue on released rows is `open`. `review_all_approved` is
at 21/84 on the v0.1.2 release rows. v0.1.1 still passes 2 of 9. Before D-026 the count was 3 of 11.
Not training-ready.

Groundwork: the orchestration setup of 2026-09-28 added the `/dataset-review` skill and the reviewer
subagents. It changed no data.

### Blockers

* No qualified `domain_expert`: expert-tier items stay `awaiting_expert` and are not
  training-eligible (`medical`, `physical_safety`, `legal` and `financial` are needed in the
  sample). Every non-allowed-safety example is expert-tier, so `coverage_minimums` (≥ 8% non-allowed
  safety) cannot pass without expert sign-off.
* rv-0.1.0-02 stays `needs_revision` until `po-reviewer` records a new decision (solo mode) or an
  adjudicator decides (multi-reviewer mode). Either way it then needs expert sign-off.
* An AI agent cannot approve, reject or revise by rubric decision, adjudicate, register reviewers,
  or act as a domain expert.
* Needs product-owner time for task 8.

### Next action

1. **Owner:** decide whether `po-reviewer-two` stays active. Register a `domain_expert` only for a
   real, qualified person (the owner included): `medical` and `physical_safety` (rv-0.1.0-02),
   `legal` (rv-0.1.0-30), `financial` (rv-0.1.0-28). All three are `needs_revision` now; without
   an expert, approving a revised version leaves the item `awaiting_expert`.
2. **Owner:** rv-0.1.0-02 stays `needs_revision` while `po-reviewer`'s revise is their latest
   decision. `po-reviewer` may re-decide it under rubric 0.2.1 if they now judge it approvable
   (`gj review approve gj-safe-003 --item rv-0.1.0-02 --reviewer po-reviewer --from <file>`).
   The v0.1.2 ledger entries are confirmed. Next, if they should be rated as examples, review
   `gj-goalchg-001` and `gj-vres-007`.

   The owner rates first; the AI copilot challenges afterwards (guide §14). If any rating changes
   after that discussion, the decision is recorded with `--independent-rating no` (as for
   rv-0.1.0-01). `gj-jour-001` is `needs_revision` on its v0.1.2 content (rv-0.1.0-14,
   `external_fact_discipline` major), and that fix needs its own decision.
3. **Agent** (on request): once decisions are recorded, apply the revise decisions through a new
   `dataset_version` and the ledger (`/dataset-review` §5), and keep these state files current.
   Candidates:
   * the 3 disputed v0.1.1 corrections (REV-0.1.1-002, -003, -011);
   * the example-level `revise` decisions (10 `needs_revision` items, rv-0.1.0-14's
     `external_fact_discipline` issue among them).
4. **Task 6 is done:** every overlap in `evaluation/leakage/v0.1.0.yaml` and
   `evaluation/leakage/v0.2.0.yaml` has a human disposition. If a new overlap is found, it is
   recorded `open` and the owner decides it. The agent records the decision as given
   (`disposition`, `decided_by`, `note`) and never changes `proposed_disposition`.
5. **Owner (Task 7):** review the remaining reference outputs: the 30 atomic cases still
   `draft_unreviewed`. The longitudinal and composite ones are done; `e2-long-06` awaits a
   `safety_policy` expert, `e2-comp-07` a `financial` expert, and `e2-safe-01` and `e2-safe-03` a
   `medical` expert. Decide when to apply the open revise decisions
   (`e2-long-02/s5`, `e2-long-05/s2`, `e2-long-05/s4`, `e2-comp-02/s2`, `e2-comp-07/s2`,
   `e2-comp-14/s1`, `e2-prog-01`, `e2-feas-01`). They need a new `evaluation_version`, and then a
   fresh review of the changed references.
   * The owner rates first; the AI copilot may challenge afterwards.
   * The agent records the decisions as given with `gj eval review-reference` (`/evaluation` skill),
     with `--independent-rating no` if any decision changed after the copilot's critique.
   * Expert-tier cases (`e2-safe-01`, `e2-safe-03`, `e2-comp-07`, `e2-long-06`) need a registered
     `domain_expert` for their domains.
