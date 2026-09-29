---
name: dataset-review
description: Human-review round workflow for the GoalJourney dataset (solo-owner governance by default, D-026). Use when preparing review packets or sheets, acting as the AI review copilot after the owner has rated, checking review status, training eligibility or release gates, recording decisions a human reviewer has made, or applying revisions requested by reviewers. The agent prepares, explains and verifies; only registered humans decide.
---
# Dataset review round

Full guide for reviewers: `docs/HUMAN_REVIEW_GUIDE.md`. Config: `configs/review.yaml`. Rubric:
`evaluation/rubrics/dataset_review_rubric_v0.2.1.yaml` (0.2.0, which earlier events are stamped with, stays in
`dataset_review_rubric.yaml`).

**Governance mode** (`configs/review.yaml` `governance.mode`, D-026). The default is `solo_owner`:

- one human owner reviews, and their latest decision on a content hash is final;
- there is no second reviewer, adjudication or pairwise calibration to arrange;
- `reviewer_diversity` and `calibration_agreement` show as N/A. Never report them as passed.

In `multi_reviewer` mode, the pairwise gates and adjudication apply (guide §17). Never create or
suggest a second identity to satisfy a gate.

## The one rule

**The agent prepares, humans decide.**

- Never author a rating, an issue, a note or an `action` in a decision file or sheet.
- Never run `gj review approve|revise|reject` on your own initiative.
- Never pass `--acknowledge-findings` for someone.
- Never add an entry to `review/reviewers.yaml`, and never edit `data/reviewed/` by hand.
- Validation, audits and subagent findings are not reviews. Don't describe them as one.
- As the **AI review copilot** (guide §14), you may explain, challenge and recalculate, but only
  after the owner has rated the item.
  - You are never a reviewer or a domain expert, and never the source of a qualification.
  - You never change a rating. If the owner changes one after your critique, they record it with
    `--independent-rating no`.

## 1. Preconditions

```bash
python3 scripts/gj.py review stats | tail -3     # "Reviewers: none yet" = nobody registered
```

If no reviewer is registered (`reviewers: []` in `review/reviewers.yaml`), stop. The next action belongs to the owner: register reviewers with
pseudonymous ids, roles, languages and expert domains. Say so, and prepare packets only if asked.

## 2. Orientation

```bash
python3 scripts/gj.py review list --manifest     # the sample in manifest order; * = calibration item
python3 scripts/gj.py review sample-status       # per item: changed since sampling, known issues, status
python3 scripts/gj.py gates                      # which review gates are still open
```

## 3. Prepare the materials (outputs go in git-ignored `scratch/review/`)

| For | Command |
|---|---|
| Calibration round first: the 8 `*` items, rated by every reviewer independently | `gj review export --format md --manifest --out scratch/review/packet.md` |
| A batch sheet the reviewer fills in | `gj review export --format sheet --manifest --out scratch/review/sheet_<reviewer>.yaml` |
| One item | `gj review template <id> --out scratch/review/<id>.yaml` |

- Never add `--with-automated` to a reviewer's packet. Reviewers rate first and look at automated
  findings afterwards (guide §5).
- Expert-tier items need a registered `domain_expert` for every required domain. List those items
  and their domains for the owner. Never tell a reviewer outside a domain that they may approve.
- Without a qualified expert, an expert-tier item stays `pending` / `awaiting_expert` and is not
  training-eligible. Release manifests list it with its reason; it is never dropped silently.

## 4. Record decisions (only a human's own filled file)

A reviewer normally records their own decisions:

```bash
python3 scripts/gj.py review apply --reviewer <their-id> <their-filled-sheet>
```

Run this for them only when they explicitly ask in this session, with their filled file, unmodified.
If the file is incomplete or invalid, report the error. Never fill the gaps.

Then verify:

```bash
python3 scripts/gj.py review verify-log        # hash chain + snapshots intact
python3 scripts/gj.py review stats             # mode, human-reviewed / training-eligible counts, N/A items
python3 scripts/gj.py review sample-status --write
python3 scripts/gj.py gates
```

In `multi_reviewer` mode, calibration agreement below the gate (guide §9) is resolved by
discussion and an `adjudicator`. In solo mode, an owner who is unsure writes that in the notes
(guide §15); no new state is needed. The agent can summarise disagreements or doubts, but never
resolves them.

## 5. Act on `revise` and `reject` decisions

1. Treat each requested revision as a content change: follow `.claude/rules/dataset.md`.
   - A released version is frozen, so bump `dataset_version` and open a new ledger whose base is
     the last release.
   - Then edit the examples.
   - Then run `gj revisions sync` and `gj revisions check`.
2. Run `gj validate`, `gj audit --write`, `gj review sample-status --write`, then `make check`.
3. Changed content goes back to `pending` (`content_changed`). A human must review the new content
   hash. Never carry an approval over.
4. Update `review/known_issues_v<ver>.yaml`: link the `revision_ids`, and set `fixed_pending_review`.
   Only a human review moves an issue to resolved.

## Also human-only

- Dispositions of leakage overlaps (`evaluation/leakage/*.yaml`, `disposition: open` until decided).
- Licensing resolutions (`configs/licensing_status.yaml`).
- Adjudication, and deciding that a known issue is `wont_fix`.

## Optional pre-pass

The `dataset-auditor` subagent can check sample items against the spec and policies. Its findings go
to the owner and the known-issues register, never into a reviewer's packet before they have rated.

## Finish

Update Progress and Next action in `docs/ACTIVE_MILESTONE.md`. Record these counts in
`docs/PROJECT_STATE.md`:

- the governance mode;
- human-reviewed and training-eligible counts;
- awaiting expert;
- applicable gates passed, and the N/A gates.
