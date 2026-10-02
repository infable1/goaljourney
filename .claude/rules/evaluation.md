---
paths:
  - "evaluation/**"
---
# Evaluation cases and leakage metadata

Design: `docs/EVALUATION_V0.2_DESIGN.md`. Workflow: `/evaluation`.

- **Builders are the source.** Write v0.2.0 cases in `evaluation/builders/v0_2_0/*.py` and render
  them with `gj eval build-cases`. Never edit the generated files:
  - `evaluation/cases/v0.2.0/*.yaml`;
  - `evaluation/seeds/v0.2.0.yaml`;
  - the eval side of `data/scenarios/behavioural_scenarios.yaml`;
  - the `cases:` block of `evaluation/leakage/v0.2.0.yaml`.

  `gj eval build-cases --check` and the tests catch drift.
- **Frozen sets.** `evaluation/cases/v0.1.0/` is frozen. `evaluation/cases/v0.2.0/` is the test
  split of release v0.1.1. Changing or adding a case therefore means a new `evaluation_version`, and
  a new `dataset_version` before the next `gj split`. Don't mutate a set that is inside a release.
- **Independence (D-017).**
  - Every case starts from its own seed and its own eval-side scenario.
  - The `operation|trigger|condition|decision` pattern must differ from every training pattern.
  - Never paraphrase a training example or reuse its topic. Check `data/raw/examples/` and
    `generation/scenarios/` first.
- **Multi-step cases are teacher-forced.** Each step's input contains the *reference* results of
  earlier steps: earlier replies as assistant turns, and confirmed changes applied to `goal`,
  `journey` and `decision_log`. Give each step its own `step_pattern`.
- **References are acceptable answers, not the only correct one.** Human review (D-028) is stored
  in the case's `reference_review` block and recorded only with `gj eval review-reference`, never by
  hand. In `solo_owner` mode one registered owner completes it. `reference_status` is derived: it is
  `human_reviewed` only when every reference output has a decision on its current content hash. An
  expert-tier case without registered `domain_expert` coverage is `awaiting_expert` (D-029). The
  builder carries the block over, so never strip it.
- **Every unit** needs `schema_valid`, `semantic_clean` and a `language` check, plus checks that the
  naive baseline fails.
- **Leakage metadata** in `evaluation/leakage/v<ver>.yaml`:
  - record every new automated candidate or hand-found overlap under `template_overlaps`, with
    strength, relation and `proposed_disposition`;
  - `disposition` stays `open` until a human decides. Record the decision in `disposition`,
    `decided_by` and `note`, and never change `proposed_disposition`;
  - the file never claims "no leakage".
  - `evaluation/leakage/v0.1.0.yaml` is frozen except for those three human-review fields on its
    overlap entries (owner decision, 2026-10-01). The rest stays as recorded: the `cases:` block,
    and each overlap's ids, `strength`, `cross_lingual`, `relation` and `proposed_disposition`.
- **Reports** under `evaluation/reports/` are git-ignored run outputs. Read `report.md`, not
  `predictions.jsonl`.
