---
name: evaluation
description: Evaluation workflow for GoalJourney Navigator. Use when authoring or changing evaluation cases (builders), rendering and checking them, running the reference, naive-baseline or model predictors, reading reports, preparing human review sheets for model outputs, or recording eval leakage overlaps. Covers the frozen-set and independence rules.
---
# Evaluation

Design: `docs/EVALUATION_V0.2_DESIGN.md`. Leakage: `docs/LEAKAGE_CHECKS.md`. Always-on rules:
`.claude/rules/evaluation.md`. For a large batch of cases, brief the `evaluation-engineer` subagent.

## Before changing any case: which set?

`evaluation/cases/v0.2.0/` is the **test split of release v0.1.1**, and `evaluation/cases/v0.1.0/`
is frozen. You can't mutate a set inside a release. To add or change cases:

1. Bump `evaluation_version` in `configs/versions.yaml`.
2. Add a new builder package, `evaluation/builders/v<new>/`, starting as a copy.
3. Point `build.py` and `configs/evaluation.yaml` at the new version. Record this in
   `docs/DECISIONS.md` if the design changes.
4. Plan a new `dataset_version` before the next `gj split`, because the test split changes.

Confirm this scope with the owner first: it is a milestone-level change.

## Authoring a case (builders are the source)

In `evaluation/builders/v0_2_0/` (or the new version), using the helpers in `common.py`:

1. **Seed.** `seed(sid, language, domain, situation, twists)`: its own seed, never a training
   scenario.
2. **Scenario.** `scenario(sid, operation, trigger, condition, decision, description)`. The
   `operation|trigger|condition|decision` pattern must differ from every training pattern in
   `data/scenarios/behavioural_scenarios.yaml` (side `train`). Grep that file and
   `data/raw/examples/` for the topic and decision first.
3. **Case.**
   - Single-step: `case(..., task_type=, input=, checks=, reference=)`.
   - Multi-step: `case(..., steps=[step(...), ...])`.
   - Give each step its own `pattern` and **teacher forcing**: step N's input carries the
     *reference* results of steps 1…N−1. That means replies as assistant turns, and confirmed changes
     applied to `goal`, `journey` and `decision_log`.
4. **Checks.**
   - Start from `base_checks(language)`, which gives `schema_valid`, `semantic_clean` and `language`.
   - Add `c(check, metric, ...)` and `lint_absent(...)` for the behaviour under test.
   - At least one check must fail the naive baseline.
5. **Content.**
   - Dates follow from `today` and the calendar. Phrase a remaining span as "N weeks away", not
     "N weeks left" (a known lint false positive).
   - Russian is gender-neutral: avoid a sentence-initial institution plus a feminine past tense, and
     use impersonal «перенесли».
   - Only product capabilities (`configs/product_capabilities.yaml`).

Then render and check:

```bash
python3 scripts/gj.py eval build-cases            # writes cases, seeds, eval-side scenarios, leakage `cases:` block
python3 scripts/gj.py validate                    # includes evaluation cases (reference passes its own checks)
python3 scripts/gj.py eval run --predictor reference   # every case must pass
python3 scripts/gj.py eval run --predictor naive       # must fail; a unit it passes has checks that are too weak
python3 scripts/gj.py leakage                     # no hard findings; review template candidates
python3 -m pytest -q tests/test_evaluation.py
```

**Leakage metadata** goes in `evaluation/leakage/v<ver>.yaml`. The hand-maintained sections are
kept on rebuild. Add every automated candidate or overlap found by reading to `template_overlaps`,
with `strength`, `relation`, `proposed_disposition` and `disposition: open`. A human sets the final
`disposition` and `decided_by`. Never write "no leakage".

## Running a model

```bash
# endpoint and key are set by the user in the environment (.env): OPENAI_COMPATIBLE_BASE_URL / _API_KEY
python3 scripts/gj.py eval run --predictor model --provider openai_compatible --model <served-name> [--limit N] [--out evaluation/reports/<run>]
python3 scripts/gj.py eval review-sheet --predictions evaluation/reports/<run>/predictions.jsonl --out scratch/eval_review_<run>.yaml
```

- **Reading the results.** Read `evaluation/reports/<run>/report.md`. Don't read `predictions.jsonl`
  whole.
- **Scoring.** There is no overall score (D-018). Report per metric and per dimension. A case passes
  only if all its units pass.
- **Committing.** Reports are git-ignored; summarise the results in the milestone docs instead.
- **Prompt parity.** The navigator system prompt used for eval (`configs/evaluation.yaml`) must be
  the one used to build the SFT export. If they differ, say so in the report.
- **References.** A reference is one acceptable answer, not the only correct one. Most are still
  `draft_unreviewed`. A model disagreeing with a reference is a finding for a human, not automatically
  a model error.

## Recording a human review of reference outputs (D-028)

The owner rates first; the agent only records what the owner decided. Write their decisions to a
git-ignored file, e.g. `scratch/review/<case>_<reviewer>.yaml`:

```yaml
units:
  - {step_id: s1, action: approve, overall: excellent, issues: [], notes: ''}   # omit step_id for an atomic case
```

```bash
python3 scripts/gj.py eval review-reference <case> --reviewer <id> --from <file> --independent-rating yes|no
```

The command does the following:
- it refuses an unregistered or non-human reviewer, a language gap, and `multi_reviewer` mode;
- on a risk-tier case the owner's review completes it like any other (D-030: no expert coverage, no
  `awaiting_expert`); never claim or imply expert qualification;
- it binds each decision to its reference output's content hash;
- it writes the case file through the builder, so `gj eval build-cases --check` stays clean.

Use `--independent-rating no` if any decision changed after an AI-copilot critique. Never invent
criterion ratings, issues or notes.

## Scoring existing predictions

```bash
python3 scripts/gj.py eval score --predictions <file.jsonl>
```

## Finish

- Run `gj eval build-cases --check` and `make check`.
- Record case counts, pass/fail against the reference and naive predictors, and open overlaps in
  `docs/ACTIVE_MILESTONE.md`.
