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

As of 2026-09-29, on branch `claude/sleepy-dijkstra-nzrf3t` (not yet merged into the default
branch). The calibration round is recorded, the governance change (M1.7a) is implemented, and
solo-owner review of the rest of the sample has started (4 items). The rest of the milestone has not
started.

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
* **Solo-owner sample review (started).** `po-reviewer` reviewed four non-calibration items under
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
    discussion, so the flag records provenance; it is not an issue.

  **Independence correction.** rv-0.1.0-01 was first recorded with `independent_rating: true`
  (`rev-044d69c4953d`). The owner had changed `language_quality` from major to minor issues after
  the AI-copilot discussion, so a corrective event (`rev-a1a061cc1487`) appends the same final
  decision with `independent_rating: false`. The original line is unchanged, and its latest
  decision is still approve / acceptable. rv-0.1.0-03 keeps `independent_rating: true`.

  The log now holds 22 events (`gj review verify-log`: 0 errors).
  * Pool (93): human-reviewed 13, training-eligible 10, needs_revision 3, not reviewed 80.
  * Sample (30): decided 12, approved 9, needs_revision 3, pending 18.
* **Task 3 (historical; N/A in solo mode).** Agreement on the decision is 7/8 (0.875), κ 0.60.
  That would pass `calibration_agreement` in `multi_reviewer` mode; in solo mode the gate is N/A.
  Agreement on the overall verdict is 3/8 (κ 0.05); the gap is mostly `excellent` against
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
    calibration-era events are stamped 0.2.0; the 5 solo-owner events are stamped 0.2.1.
* **Tasks 4–8 (not started).** All 36 ledger entries are `pending_human_review`. KI-008, KI-012 and
  KI-033 are open. The 100 + 27 evaluation overlaps are `open`. The v0.2.0 references are
  unreviewed. POL-A…F and the licensing owners are unconfirmed.
* **Task 9 (ongoing).** The blind calibration packet was prepared (in `scratch/`, git-ignored). The
  sample status file was regenerated with each recorded decision (latest: `71c92eb`; the
  independence correction `2438dd4` left it unchanged), and these state files were synchronised with
  `gj review stats`.

Acceptance criteria: all open. The multi-reviewer criterion, `calibration_agreement`, is N/A in
solo mode.

Gates (`gj gates`, v0.1.1, solo_owner): 2 of 9 applicable pass (`findings_acknowledged`,
`leakage_hard_clean`), and 2 are N/A (`reviewer_diversity`, `calibration_agreement`).
`review_all_approved` is at 10/93. Before D-026 the count was 3 of 11. Not training-ready.

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
   `legal` (rv-0.1.0-30), `financial` (rv-0.1.0-28). Without one, those items stay
   `awaiting_expert`.
2. **Owner:** rv-0.1.0-02 stays `needs_revision` while `po-reviewer`'s revise is their latest
   decision. `po-reviewer` may re-decide it under rubric 0.2.1 if they now judge it approvable
   (`gj review approve gj-safe-003 --item rv-0.1.0-02 --reviewer po-reviewer --from <file>`).
   Then rate the other 18 pending sample items (`gj review export --format sheet --manifest`), the 36
   ledger revisions and the open known issues. The owner rates first; the AI copilot challenges
   afterwards (guide §14). If any rating changes after that discussion, the decision is recorded
   with `--independent-rating no` (as for rv-0.1.0-01).
3. **Agent** (on request): once decisions are recorded, apply the revise decisions through a new
   `dataset_version` and the ledger (`/dataset-review` §5), and keep these state files current.
