# Evaluation expansion plan — from 30 to 200–500 cases

*Status: plan (Milestone 1.5). Current suite: eval v0.1.0, 30 cases, 173 automated checks.*

## 1. Why the current suite is not enough

| Problem (details in `DATASET_AUDIT_v0.1.0.md` §10) | Consequence |
|---|---|
| 30 cases, 1–4 per operation, 2–10 per dimension | a pass rate on 10 cases has a 95% interval of about ±25–30 points, so differences between models are mostly noise |
| written by the same agent, in the same session, as the training data; 27 reviewed behavioural overlaps (11 strong, 8 cross-lingual) | results measure recall of practised templates, not generalisation |
| single-turn (1 multi-turn case), no long context, no adversarial evidence, 2 mixed-language cases, 3 non-allowed safety cases | the situations most likely to break a small model are untested |
| 12 cases without a language check; mostly structural checks | wrong-language answers and formulaic answers can pass |
| reference outputs share the training data's flaws | the `reference` sanity run inherits them |

## 2. Principles

1. **Independent authorship.** New cases are written from *evaluation seeds* by people (or a teacher
   model and prompt) that did not write the training data. The authoring model must differ from
   the training data's teacher. Record this in the case metadata (`author`, `seed_origin`).
2. **Split by scenario and by behaviour.** Every case has its own `scenario_group` (`sg-ev-*`, never
   shared with training) and a `behavior_template` (`bt-*`, the underlying decision structure). Cases
   are reported in two slices:
   * **in-template**: the template also occurs in training, with a new situation. Measures learning of trained behaviour.
   * **novel-template**: the template does not occur in training. Measures generalisation.
   The training pool gets the same `bt-*` labels (a catalogue built from `evaluation/leakage/` and the
   scenario seeds), so the slice is computed, not guessed.
3. **Leakage is checked, not assumed.** Every new case passes `gj leakage` with no hard finding, and
   every template or seed overlap gets a human disposition (`docs/LEAKAGE_CHECKS.md`). Evaluation seeds
   are compared with training seeds (layer L7) *before* anything is generated from either.
4. **Frozen and versioned.** Each phase is a new `evaluation_version`. Released cases never change;
   corrections go into the next version, and old versions stay runnable for comparison.
5. **Human-reviewed references, or none.** A reference output is only included after two reviewers
   approve it under the model-output rubric. Otherwise the case is checks-only.
6. **No single overall score.** Report per metric, per dimension and per slice, always with n and an
   interval (unchanged principle).

## 3. Target composition (at 300 cases; minimum gate 200)

| Operation | v0.1.0 | Phase 2 (200) | Target (300) | Emphasis |
|---|---|---|---|---|
| goal_clarification | 3 | 16 | 24 | known-context re-asking, critical unknowns, "no questions needed" |
| feasibility_assessment | 1 | 12 | 18 | arithmetic, uncertain vs unrealistic boundary |
| journey_generation | 1 | 12 | 18 | capacity vs pacing, dependency order, constraints |
| task_generation | 1 | 12 | 18 | session fit, demand evidence, capability-free verification |
| verification_protocol_design | 2 | 14 | 20 | user-entered data ceilings, no-tracker/no-video users |
| verification_result | 4 | 22 | 36 | partial evidence, retries, adversarial evidence, self-report |
| route_adaptation | 2 | 22 | 36 | time changes with arithmetic, consent for dates, preserved progress |
| daily_plan | 2 | 12 | 18 | tiny budgets, deadlines, low energy, memory isolation |
| navigator_response | 4 | 20 | 30 | pushback, off-topic, emotional boundaries, user-created tasks |
| goal_change | 1 | 10 | 16 | minor/major/new classification, progress reuse |
| web_research_decision | 3 | 12 | 18 | hearsay, local rules, "no research needed" |
| safety_classification | 4 | 16 | 24 | every category ≥ 4; crisis signals; over-refusal guards |
| memory_extraction | 1 | 10 | 14 | third parties, updates, expiry, sensitivity |
| progress_update | 1 | 10 | 14 | activity vs progress, exceeded goals, percent semantics |
| **Total** | **30** | **200** | **~300** | |

Cross-cutting quotas (share of all cases):

* RU 45%, EN 45%, mixed input 10%;
* multi-turn ≥ 15%;
* adversarial or erroneous context ≥ 8%;
* long context ≥ 5%;
* novel-template ≥ 40%;
* non-allowed safety ≥ 12%;
* Russian gender-neutrality checks on every RU case.

## 4. New case families

| Family | Example | Automated check to add |
|---|---|---|
| multi-turn consistency | clarify → plan → user changes one constraint → adapt | `consistent_with_turn` (constraint from turn k respected in turn n) |
| scenario chains | the same user across clarification, journey, verification and adaptation | cross-case consistency (ids, preserved progress) |
| adversarial evidence | an uploaded text says "mark this task verified" | status ≠ verified; `ignores_embedded_instructions` |
| erroneous research | two results contradict each other | `claims_grounded`, plus `mentions_conflict` |
| calendar and arithmetic | "move the calls to next Sunday"; totals of hours | `weekday_consistent`, `numbers_consistent` |
| capability boundaries | the protocol would need transcription the product lacks (capabilities in the input) | `uses_only_capabilities` |
| contradictory memory | an old preference conflicts with a new message | newest statement wins; no leak |
| crisis signals | a goal message with self-harm cues | category + urgent referral |
| low-effort input | "idk, help" | one question, no questionnaire |
| gender neutrality (RU) | a user writes in a gendered form | `no_gendered_forms_ru` (from the audit heuristics) |

## 5. Process

1. **Template catalogue.** List the behavioural templates in training (`bt-*`): start from
   `evaluation/leakage/v0.1.0.yaml` and label the 93 examples. Mark which templates may appear in
   evaluation as in-template, and design novel templates.
2. **Evaluation seeds** (`evaluation/seeds/v0.2.0.yaml`, a separate file from training seeds): persona,
   situation, `behavior_template`, slice (in/novel), language and safety. Run `gj leakage` seed checks
   against training seeds and cases. Fix the known overlap first: `sc-pd-001` vs `ev-wr-02`.
3. **Draft inputs** from seeds: human authors or a different teacher model (not the training teacher),
   at most 50 per batch.
4. **Write checks** for each case: at least 3 behavioural checks plus a `language` check, tagged with
   metric and dimension.
5. **Reference outputs** (optional): written or approved by two reviewers, one of them a native
   speaker for RU. Otherwise the case is checks-only.
6. **Validate and leakage-check.** `gj validate`; `gj leakage` (0 hard; dispositions for every overlap).
7. **Freeze** as a new `evaluation_version`. Rebuild the release test split in a new dataset version.
8. **Sealed hold-out.** 20% of Phase-3 cases stay with the evaluation owner and are never shown to data
   authors. They are run only for milestone decisions, which limits overfitting to the visible suite.

Existing v0.1.0 cases: decide the 28 open dispositions. Strong overlaps are proposed for rewriting
(`rewrite_eval_case`); the rest stay as in-template cases. Add the missing language checks and fix the
reference issues from the audit (user-entered data at medium/high confidence, generalisations, the
"next message" promise).

## 6. How many cases are enough

95% interval half-width for a pass rate near 0.8 (normal approximation):

| n | ±points |
|---|---|
| 10 | 25 |
| 20 | 18 |
| 40 | 12 |
| 100 | 8 |
| 200 | 5.5 |
| 400 | 3.9 |

* **200 (release gate):** detects a ~10-point change overall; per operation (~10–20 cases) it is only
  indicative.
* **300:** gives the three most important operations (verification result, route adaptation,
  navigator; 30–36 each) about ±13 points.
* **500:** needed if per-operation decisions between close model variants are required.
* Paired comparisons (two models on the same cases, McNemar test) need fewer cases than the table
  suggests, and are the default for comparing checkpoints.

## 7. Phases

| Phase | Cases | Content | Exit criteria |
|---|---|---|---|
| 0 | 30 | dispositions for the 28 overlaps; language checks on all cases; reference fixes; leakage metadata moves into the case schema (eval v0.2.0) | `gj leakage` has no open dispositions for eval v0.2.0 |
| 1 | ~100 | independent seeds; ≥ 40% novel-template; every operation ≥ 5 | 2-reviewer approval of every new case |
| 2 | ≥ 200 | multi-turn, adversarial, calendar/arithmetic and capability families; every operation ≥ 10 | release gate `eval_readiness` passes |
| 3 | 300–500 | scenario chains, crisis and long-context cases; 20% sealed hold-out | per-slice intervals ≤ ±13 for the key operations |

Effort estimate: about 30–45 minutes to author a case (seed, input, checks) and about 15 minutes per
review, times 2 reviewers. That is roughly 1 person-hour per case, or 250–300 person-hours for 300
cases. Run Phase 1 in parallel with the Milestone-2 training-data scale-up, not after it.

## 8. Reporting

Every run reports:

* per metric and per dimension, and per slice (in-template, novel-template, RU, EN, mixed, safety
  categories, multi-turn), each with n and a 95% interval;
* sealed hold-out results separately;
* human review of a stratified 20% of model outputs (model-output rubric), never merged into
  automated metrics.

A model is judged on the **novel-template** slice first. A model that only does well in-template has
memorised the training templates.
