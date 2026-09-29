# Active milestone

*Only the active milestone lives here. When it completes, move its summary to `PROJECT_STATE.md`
and `CHANGELOG.md`, then replace this file with the next milestone.*

## Milestone 1.7 — Human Review Round 1 (in progress)

**Status:** in progress. The product owner explicitly directed the project to proceed with
Human Review Round 1 on 2026-09-28. Nothing here trains a model or generates new data.

### Objective

Get the first qualified human decisions on the v0.1.1 data and evaluation references, so the
review-dependent release gates can move. Nothing here trains a model or generates new data.

### Tasks

The column says who performs each task; the agent never records review decisions.

| # | Task | Who |
|---|---|---|
| 1 | Register reviewers in `review/reviewers.yaml`: ≥ 2 who read RU and ≥ 2 who read EN, plus domain experts for expert-tier items | owner |
| 2 | Independently rate the 8 calibration items (rv-0.1.0-02, -06, -07, -09, -12, -20, -29, -30); items -06 and -20 changed in v0.1.1 | reviewers |
| 3 | Check agreement (`gj review stats`, `gj gates`: κ ≥ 0.40, agreement ≥ 0.75) and clarify the rubric where people disagree | reviewers + agent |
| 4 | Review the 36 ledger revisions (`gj revisions diff ID`) and record `reviewer_status` | reviewers |
| 5 | Decide the open known issues KI-008, KI-012 and KI-033; the agent then applies the decided fixes through the ledger | reviewers → agent |
| 6 | Give dispositions to the 100 evaluation overlaps in `evaluation/leakage/v0.2.0.yaml` (and the 27 in v0.1.0) | reviewers |
| 7 | Review the v0.2.0 reference outputs, longitudinal cases first | reviewers |
| 8 | Confirm POL-A…F, and assign owners for the 5 licensing items | product owner |
| 9 | Prepare review packets and keep the state files current (`/dataset-review`) | agent |

### Acceptance criteria

* `calibration_agreement` passes: every reviewer pair on ≥ 8 shared calibration items agrees
  ≥ 75% with κ ≥ 0.40.
* Every ledger entry has a human `reviewer_status`, and every decided revision is applied and
  recorded, with `gj revisions check` clean.
* KI-008, KI-012 and KI-033 are decided. `validation_strict` passes, or the exception is recorded
  as a decision.
* Every evaluation overlap has a human disposition; `leakage_dispositions` passes or its remaining
  failures are listed.
* `make check` passes; `PROJECT_STATE.md`, this file and `CHANGELOG.md` are updated.

### Progress

As of 2026-09-29, on branch `claude/sleepy-dijkstra-nzrf3t` (not yet merged into the default
branch). The calibration round is recorded; the rest of the milestone has not started.

* **Task 1 (partly done).** Two human dataset reviewers are registered: `po-reviewer` (`fdf6d4c`)
  and `po-reviewer-two` (`c8630b2`, registered at the product owner's request as a separate
  person). Both read ru and en, which meets "≥ 2 RU, ≥ 2 EN". No `domain_expert` and no
  `adjudicator` is registered.
* **Task 2 (done).** Both reviewers rated all 8 calibration items; `po-reviewer-two` rated them
  blind from a packet without existing decisions or automated findings. That is 16 calibration
  decisions. The log holds 17 events in total; the extra one is `po-reviewer`'s approval of
  `gj-daily-002`, which is outside the review sample.
* **Task 3 (partly done).** Agreement on the decision is 7/8 (0.875), κ 0.60, so
  `calibration_agreement` passes. Agreement on the overall verdict is 3/8 (κ 0.05); the gap is
  mostly `excellent` against `acceptable` and has not been discussed yet.
  * rv-0.1.0-02 / `gj-safe-003` (`high_risk`): `po-reviewer` chose revise and `po-reviewer-two`
    approve, so the item stays `needs_revision`. An adjudication record is prepared but **not
    recorded**, because no adjudicator is registered. It proposes approve, overall excellent, A, B,
    I, K, L, M, N, P `good`, reasoned from the `high_risk` rule in DATASET_SPEC §9. It lives in
    `scratch/review/adjudication_rv-0.1.0-02.yaml`, which is git-ignored, so it must be prepared
    again if the working copy is lost. Even when recorded, an adjudicator without `medical` and
    `physical_safety` leaves the item `pending` (`awaiting_expert`).
  * rv-0.1.0-30 / `gj-safe-006` (`restricted`): both reviewers chose revise (external-fact
    discipline, a hard gate). The fix goes through a new `dataset_version` and the ledger, then a new
    review with `legal` sign-off.
  * Rubric 0.2.1 (D-025, `6ece224`) clarifies the safety anchor for restricted goals. All 17 events
    are stamped 0.2.0.
* **Tasks 4–8 (not started).** All 36 ledger entries are `pending_human_review`. KI-008, KI-012 and
  KI-033 are open. The 100 + 27 evaluation overlaps are `open`. The v0.2.0 references are
  unreviewed. POL-A…F and the licensing owners are unconfirmed.
* **Task 9 (ongoing).** The blind calibration packet was prepared (in `scratch/`, git-ignored). The
  sample status file was regenerated (`0182552`) and these state files were synchronised.

Acceptance criteria: `calibration_agreement` passes, and `make -k check` passes at `0182552`. The
other criteria are open.

Gates (`gj gates`, v0.1.1): 3/11 pass. `reviewer_diversity` fails: `po-reviewer` approved all 7
approved rows (100% share, cap 80%).

Groundwork: the orchestration setup of 2026-09-28 added the `/dataset-review` skill and the reviewer
subagents. It changed no data.

### Blockers

* No registered `adjudicator`: the rv-0.1.0-02 disagreement cannot be resolved.
* No registered `domain_expert`: no expert-tier item can be approved (`medical`, `physical_safety`,
  `legal`, `financial` are needed in the sample).
* `reviewer_diversity` fails: `po-reviewer` holds 100% of the approvals (cap 80%).
* An AI agent cannot approve, reject or revise by rubric decision, adjudicate, or register reviewers
  on its own.
* Needs product-owner time for task 8.

### Next action

1. **Owner:** register real people only: an `adjudicator`, and `domain_expert`s for `medical` and
   `physical_safety` (rv-0.1.0-02), `legal` (rv-0.1.0-30) and `financial` (rv-0.1.0-28).
2. **Adjudicator:** confirm or amend the prepared rv-0.1.0-02 record and record it under their own
   id (`gj review approve gj-safe-003 --item rv-0.1.0-02 --reviewer <id> --from <file>`).
3. **Reviewers:** discuss the overall-verdict gap (excellent vs acceptable), then rate the other 22
   sample items (`gj review export --format sheet --manifest`), the 36 ledger revisions and the
   open known issues.
4. **Agent** (on request): once decisions are recorded, apply the revise decisions through a new
   `dataset_version` and the ledger (`/dataset-review` §5), and keep these state files current.
