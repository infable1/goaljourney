---
paths:
  - "data/**"
  - "schemas/**"
  - "review/**"
  - "generation/pipelines/**"
  - "generation/scenarios/**"
  - "configs/dataset.yaml"
  - "configs/versions.yaml"
  - "configs/review.yaml"
  - "configs/release_gates.yaml"
  - "configs/coverage_targets.yaml"
  - "DATASET_SPEC.md"
---
# Dataset, schemas and review data

Spec: `DATASET_SPEC.md`. Workflows: `/dataset-review`, `/dataset-generation` and `/release-check`.

## Immutability and traceability

- **Released files are never edited:** `data/{train,validation,test}/goaljourney-v*.jsonl`,
  `data/manifests/*` and `schemas/archive/`. Nor are frozen per-version artefacts:
  `review/*_v0.1.0.*`, `evaluation/cases/v0.1.0/` and `evaluation/leakage/v0.1.0.yaml`.
  The one exception (owner decision, 2026-10-01): in `evaluation/leakage/v0.1.0.yaml`, the human-review
  fields `disposition`, `decided_by` and `note` on overlap entries are recorded by the disposition
  workflow. Everything else in that file stays frozen (`.claude/rules/evaluation.md`).
- **Changing an example's trainable content** (`task_type`, `input`, `expected_output`,
  `contrastive`) means:
  1. edit the YAML in `data/raw/examples/`;
  2. add an entry to the ledger `data/revisions/v<ver>.yaml`, giving the defect, correction,
     rationale, known issues and policies, with `reviewer_status: pending_human_review`;
  3. run `gj revisions sync` and `gj revisions check`;
  4. run `gj validate`, `gj audit --write` and `gj review sample-status --write`.
- **If the current `dataset_version` is already released**, bump it first and start a new ledger
  whose base is the last release. `gj split` refuses an incomplete ledger and never overwrites a
  release.
- **Metadata** (tags, notes) doesn't change the content hash. It is still counted in the ledger's
  metadata summary.

## Review data

- `data/reviewed/review_events.jsonl` is append-only and hash-chained, and `data/reviewed/snapshots/`
  is write-once. Never edit either by hand; only `gj review …` writes them.
- Only humans record decisions, and `review/reviewers.yaml` lists humans only. Statuses are derived:
  `pending` (with a detail), `approved`, `needs_revision` or `rejected`.
- In `review/known_issues_v<ver>.yaml`, new issues continue the numbering. An issue closes only
  through a human decision, or a revision marked `fixed_pending_review`.
- The review sample in force is set in `configs/review.yaml` (`sampling.sample_version`). Don't
  re-draw it silently.

## Authoring examples (YAML)

- Quote flow-collection items that contain prose, commas, `?` or `: `. The authoring guard flags
  mis-splits.
- Dates are relative to `input.today`, and milestones are due on or before the goal deadline.
- Weekday names must match the calendar. Every number in the message must follow from the plan.
- Never infer a user's gender. Russian text avoids gendered forms for the assistant and the user.
- Rejected outputs (`contrastive`) are schema-valid, realistic and tagged with *every* failure mode
  they show. At v0.1.1, untagged lint errors produce a warning.
- No real personal data. Names of real exams or products are allowed (tracked in LIC-004).

## Schemas

- A structural change means: new `schema_version`, archive the old schemas, version-gate the new
  lint rules, and state the migration in the ledger's metadata summary.
- Keys and enums are English. User-facing strings are Russian or English.
