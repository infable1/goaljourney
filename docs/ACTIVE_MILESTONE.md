# Active milestone

*Only the active milestone lives here. When it completes, move its summary to `PROJECT_STATE.md`
and `CHANGELOG.md`, then replace this file with the next milestone.*

## Milestone 1.7 — Human Review Round 1 (proposed, not started)

**Status:** proposed. It follows the recommended next step of `docs/DATASET_AUDIT_v0.1.1.md` §12.
The owner has not issued a brief for it yet. If the owner defines a different next milestone,
replace this section.

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

0%. No reviewers are registered and no decisions are recorded (no decision log in `data/reviewed/`
yet).

Groundwork: the orchestration setup of 2026-09-28 added the `/dataset-review` skill and the reviewer
subagents. It changed no data.

### Blockers

* Needs human reviewers. An AI agent cannot approve, reject or revise by rubric decision.
* Needs product-owner time for task 8.

### Next action

1. **Owner:** add reviewers to `review/reviewers.yaml`.
2. **Agent** (on request): produce the calibration packet with `gj review export --format md
   --manifest`, following `/dataset-review`.
