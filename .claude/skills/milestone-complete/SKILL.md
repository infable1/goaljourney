---
name: milestone-complete
description: Milestone completion protocol for GoalJourney. Use before declaring any milestone (or a milestone-sized task) complete and before its final commit — runs tests and validation, reviews the diff, checks every acceptance criterion with evidence, updates PROJECT_STATE / ACTIVE_MILESTONE / DECISIONS / ROADMAP / CHANGELOG, reports unresolved issues, then commits and pushes. Completion is never claimed from tests alone.
---
# Complete a milestone

Work through every step, in order. If a step fails, the milestone is not complete. Report what
blocks it instead of declaring success.

## 1. Tests

```bash
python3 -m pytest -q
```

All tests must pass; note the count. A failing test gets a root-cause fix, never a skip, xfail or
loosening (`.claude/rules/testing.md`).

## 2. Validation

```bash
make check      # validate, tests, eval builder/ledger/sample drift, eval self-check, leakage, review log
```

Then run what the milestone touched:

| If the milestone… | Run |
|---|---|
| changed examples | `gj revisions check`, `gj audit --write`, `gj review sample-status --write` |
| changed eval builders | `gj eval build-cases`, then `gj eval run --predictor reference` (all pass) and `--predictor naive` (should fail) |
| built a release | `gj split` (after bumping versions), then `gj gates`. Gates may fail; report every failing gate and its reason, and never loosen one |
| changed docs only | check links and paths exist, e.g. `grep -o '\`[a-z_./-]*\.\(md\|yaml\|py\)\`'` on the changed files |

## 3. Inspect the diff

```bash
git status --short
git diff --stat <commit-before-the-milestone>..HEAD
git diff --stat
```

Read the diff adversarially. Look for:

- **Unrelated changes.** Is there anything outside the milestone's scope?
- **Hand-edited generated files.** Eval YAML, releases, audit JSON, sample status and ledger hashes
  must match their commands (`make check` covers most).
- **Changed frozen artefacts.** Earlier releases, `schemas/archive/`, `evaluation/cases/v0.1.0/`
  and `review/*_v0.1.0.*` must not change: `git diff --stat <milestone-start> -- <those paths>`
  must be empty.
- **Secrets, personal data, large files, debug leftovers.**
- **Loosened tests, gates or thresholds.**

## 4. Acceptance criteria, with evidence

Go through the acceptance criteria in `docs/ACTIVE_MILESTONE.md` one by one. For each, cite the
evidence: a command output, a file or a test. An unmet criterion means the milestone is not
complete. Say so and list it under unresolved issues.

## 5. Update the durable state

1. **`docs/PROJECT_STATE.md`:** versions (must match `configs/versions.yaml`; a test checks this),
   health numbers, capabilities, blockers, Last updated.
2. **`docs/ACTIVE_MILESTONE.md`:** replace it with the next milestone from `docs/ROADMAP.md`. Mark
   that milestone *proposed* if the owner has not briefed it. Put the finished milestone's summary
   in `CHANGELOG.md`, not here.
3. **`docs/DECISIONS.md`:** add a `D-NNN` for every durable decision made, and supersede rather than
   delete. Use *adopted* until the owner confirms.
4. **`docs/ROADMAP.md`:** update the status column.
5. **`CHANGELOG.md`:** add a new top section with what changed, versions, results and known issues.

## 6. Report unresolved issues

List them explicitly: open known issues, failing gates, skipped items, uncertainties and follow-ups.
Never bury them.

## 7. Commit and push

```bash
git add <paths>          # stage deliberately; check git status first
git commit -m "Milestone X.Y: <title>" -m "<summary of changes, results, unresolved issues>"
git push -u origin <designated-branch>
```

- Follow the commit attribution conventions the session gives you. Never rewrite pushed history or
  force-push.
- If a push fails on the network, retry with backoff.

## 8. Final report to the user

Keep it concise:

- done and not-done, per acceptance criterion;
- files created or changed;
- checks run and their results;
- unresolved issues;
- the recommended next step.

Recommend starting a **fresh session** for the next milestone (`docs/CONTEXT_MANAGEMENT.md` §1).
