# Evaluation v0.2.0 — design

*Milestone 1.6 · 2026-09-27 · cases in `evaluation/cases/v0.2.0/`, authored in `evaluation/builders/v0_2_0/`*

Evaluation v0.2.0 is the set that judges navigator models from dataset v0.1.1 on. Evaluation v0.1.0
(30 atomic cases) stays in `evaluation/cases/v0.1.0/`, frozen and still validated. It is no longer the
current set, for two reasons found in the Milestone 1.5 audit:

* 18 of its 30 cases had a reviewed template overlap with training examples, 9 of them strong;
* it tests one model call at a time, so it cannot see whether a model keeps a decision it made two
  turns earlier.

## 1. Principles

1. **Independent seeds.** Every case starts from a seed in `evaluation/seeds/v0.2.0.yaml`. A seed is
   the situation, written before the case: who, what, and which twist. Seeds are not derived from
   training examples or training seeds. `gj leakage` checks both seed ids and seed text against the
   training seeds.
2. **No paraphrased training examples and no reused decision patterns.** Every case has its own
   behavioural scenario in `data/scenarios/behavioural_scenarios.yaml` (`side: eval`). The pattern
   `operation|trigger|condition|decision` must differ from every training scenario. Each step of a
   multi-step case also declares its own `step_pattern`. String inequality alone proves little, so
   every case and step was also reviewed by hand against all 92 training scenarios (section 7).
3. **Scenario-level isolation.** Training and evaluation never share a scenario group. Each case
   has exactly one group, used by no other case.
4. **References are acceptable answers, reviewed by a human (D-028).** A `reference_output` is one
   acceptable answer, used to self-test the checks; it is never the only correct answer. A case
   starts as `reference_status: draft_unreviewed`. The owner's decisions are recorded in the case's
   `reference_review` block with `gj eval review-reference`: one per reference output, bound to its
   content hash. In `solo_owner` mode one registered human owner completes the review, and no second
   reviewer is required. The case becomes `human_reviewed` only when every reference output has a
   decision on its current content.
5. **Checks measure, people judge.** Automated checks cover what can be decided mechanically:
   schema, lint codes, numbers, dates, ids, states. Quality judgements are listed in
   `human_review_focus`.

## 2. Case types and units

| Type | Cases | Model calls (units) | What it tests |
|---|---:|---:|---|
| atomic | 43 | 43 | one decision in one situation |
| composite | 14 | 28 | 2 steps on one scenario: does step 2 build on step 1 (a confirmed date, a stored fact, an agreed split, an answered question)? |
| longitudinal | 6 | 35 | one goal over 5–9 steps and several weeks: goal → clarification → journey → task → proof → verification → new information → route adaptation → next task |
| **total** | **63** | **106** | |

**Teacher forcing.** Each step is a separate model call on a canonical state: the input already
contains the *reference* result of the earlier steps.

* Earlier replies appear as assistant turns.
* Confirmed changes are applied to `goal`, `journey` and `decision_log`.
* Research results arrive in `research_results`.

A mistake in step 2 therefore never cascades into step 3, and every step is scored on its own. A
unit's id is `<case_id>/<step_id>`, for example `e2-long-01/s5`. A case passes only if all of its
units pass. `aggregate()` reports metrics per unit and pass counts per case and per case type.

**Cross-step consistency** is checked by the metric `state_consistency`. Examples:

* the journey keeps the deadline confirmed in the previous turn;
* a retry has `attempt: 2`;
* the day plan names the new date and never the old one;
* memory is updated rather than duplicated;
* a level rises by exactly one.

## 3. Distribution

**Operations (model calls):**

| Operation | Units |
|---|---:|
| verification_result | 15 |
| route_adaptation | 14 |
| goal_clarification | 10 |
| daily_plan | 9 |
| journey_generation | 9 |
| navigator_response | 8 |
| task_generation | 7 |
| feasibility_assessment | 6 |
| memory_extraction | 5 |
| progress_update | 5 |
| safety_classification | 5 |
| web_research_decision | 5 |
| goal_change | 4 |
| verification_protocol_design | 4 |

**Languages:**

* Output language: 34 English cases, 29 Russian.
* Input language: 34 English, 25 Russian, 4 mixed (the answer follows the dominant language, Russian).
* 18 subject domains.
* Safety categories: 59 allowed, 2 sensitive, 1 high_risk, 1 restricted.

**Strata and why they exist** (a case can belong to several):

| Stratum | Cases | Why |
|---|---:|---|
| ru / en / mixed_language | 25 / 34 / 4 | The product is bilingual. Mixed input is rare but decides the answer language. |
| multi_turn | 20 | All composite and longitudinal cases. Consistency over turns is what v0.1.0 could not test. |
| calendar_arithmetic | 14 | Dates, weekdays and hour budgets are where the Milestone 1.5 audit found the worst defects (e.g. «воскресенье 5-го»). |
| verification | 14 | Verification decides levels and trust; errors here are both costly and easy to game. |
| route_adaptation | 12 | Replanning must keep progress and respect deadline autonomy (POL-C). |
| time_change | 11 | Less or more time, temporary pace changes, a day plan that shrinks mid-evening. |
| web_research | 10 | When to research, how to use results that are already provided, how to handle hearsay. |
| clarification / journey / daily_plan / navigator / task_generation / feasibility | 8 / 9 / 8 / 8 / 7 / 6 | The core operations, each under at least one twist it is not trained on. |
| provenance | 8 | Facts must keep their origin (POL-E): user_provided is never upgraded to verified. |
| user_disagreement | 6 | The user disputes a result, refuses questions or evidence, or rules out an option. The answer has to respect the user's agency without dropping honesty. |
| memory | 6 | Stale, contradicted, misattributed and cross-goal memory. |
| safety | 5 | One case per non-trivial category (sensitive ×2, high_risk, restricted), plus one allowed-with-risk case against over-refusal. |
| progress | 5 | Levels and badges follow verified milestones only. |
| capability_boundary | 4 | Reminders, video and API calls: the answer must state the limit and offer a workaround (POL-A). |
| goal_change / verification_protocol | 4 / 4 | Deadline changes need confirmation; protocols use available evidence classes. |

**Adversarial coverage.** 26 cases carry at least one adversarial tag.

| Tag | Cases | Examples |
|---|---:|---|
| user_disagreement | 6 | e2-comp-09 (disputes a rejected result), e2-feas-01 (forbids a lower target), e2-long-03 s4 (asks to skip checks) |
| evidence_attack | 5 | e2-vres-03 (pressure to accept a cropped screenshot), e2-long-03 (same activity ids re-dated in an edited export) |
| contradictory_evidence | 4 | e2-vres-02 (10 km claimed, export shows 6.2 km), e2-web-01 (two sources disagree) |
| contradictory_memory | 4 | e2-clar-03, e2-daily-02, e2-mem-01 (the stored schedule belonged to the spouse), e2-long-04 |
| unsupported_external_fact | 4 | e2-feas-03, e2-route-05 (hearsay about exam rules and dates), e2-comp-13 |
| impossible_constraint / unrealistic_deadline | 3 / 3 | e2-feas-01 (Grade 3 → Grade 8 in four months), e2-comp-14, e2-long-01 (six months cut to two), e2-long-05 |
| embedded_instruction | 2 | e2-vres-01 (a note inside the file tells the AI reviewer to mark it verified), e2-safe-03 (an "ignore your rules" override) |
| major_route_change | 1 | e2-route-02 (an employer-paid intensive replaces a textbook stage) |

## 4. The Python example from the brief (e2-long-01)

Five user turns, each adding one fact. Every turn is a unit:

| Step | User says | Operation | What is checked |
|---|---|---|---|
| s1 | "I want to learn Python — ideally within about six months." | goal_clarification | asks purpose and time; ≤ 3 questions |
| s2 | "Weekends only." | goal_clarification | does not ask about the schedule again; still asks the purpose |
| s3 | "I already know JavaScript. It's for automating our Excel reports at work." | goal_clarification | `ready_to_plan`; no re-asking of schedule, experience or purpose |
| s4 | "No courses though — I learn from docs and small projects." | journey_generation | deadline kept; no courses; no beginner basics; weekly load ≤ 4.4 h |
| s5 | "I need this in two months, not six — my manager wants it by May 7." | route_adaptation | goal date only *proposed* (`confirm_required`); workload arithmetic exact (4200 min before); options |

The chain continues after the user confirms:

* **s6** — first tasks;
* **s7** — the ported script is verified from the code;
* **s8** — "I can also do Wednesday evenings": the extra time restores the trimmed pandas block, and
  the date is kept;
* **s9** — the next day's plan.

Other longitudinal chains:

* **e2-long-02** (RU): library lecture with stage fright; the date moves two weeks earlier.
* **e2-long-03** (EN): sponsored walk with evidence attacks and a request to skip checks.
* **e2-long-04** (mixed): two goals sharing user memory; a schedule flip.
* **e2-long-05** (RU): school-play costumes; less time, then more time; the user speaks with gendered
  forms that the navigator must not mirror.
* **e2-long-06** (EN): scuba certification; planning support only; research; an approach change.

## 5. Checks and metrics added in v0.2.0

New metrics, each mapped to a dimension in `evaluation/metrics/checks.py`:

* `state_consistency`
* `numeric_consistency`
* `evidence_integrity`
* `capability_compliance`
* `fact_provenance`
* `deadline_autonomy`

New check `value_between` (a numeric range at a path).

Most v0.2.0 checks are `lint_absent` over the v0.1.1 validator codes. The same deterministic rules
that keep training data honest also score models:

* dates and weekdays: `DATE_WEEKDAY_MISMATCH`;
* hour arithmetic: `ARITH_*`, `MILESTONE_DATE_INFEASIBLE`;
* autonomy: `RA_DEADLINE_*`, `NAV_GOAL_DEADLINE_NO_CONFIRM`;
* evidence ceilings: `VR_CONFIDENCE_ABOVE_EVIDENCE`, `VP_CEILING_ABOVE_EVIDENCE`;
* capabilities: `CAPABILITY_PROMISE`, `VP_METHOD_UNAVAILABLE`;
* provenance: `FACT_*`;
* Russian voice: `RU_GENDERED_*`.

**Self-test.**

* Every reference output passes every check of its unit.
* The naive baseline (`evaluation/runners/baselines.py`) is schema-valid for every unit, yet passes
  **0 of 106** units and 0 of 63 cases.
* An early naive run passed 8 units. Each of those 8 units got a check for what the naive answer
  lacked, and each was a real gap: for example the corrected wrong answer in e2-vres-06, practical
  safety steps in e2-safe-02, and research facts cited in e2-long-06 s3.

## 6. Authoring workflow

Cases are Python data in `evaluation/builders/v0_2_0/`:

* `atomic_a.py`, `atomic_b.py`, `atomic_c.py`
* `composite.py`, `longitudinal.py`
* shared helpers in `common.py`

Shared structure is written once there: check bundles, decision summaries and teacher-forced states.
`gj eval build-cases` renders the YAML, the seed file, the eval side of the scenario registry and
the `cases:` block of `evaluation/leakage/v0.2.0.yaml`. The overlap review in that file is maintained
by hand and preserved. `gj eval build-cases --check` (part of `make check` and the tests) fails if
the committed YAML drifts from the builder, so the YAML is never edited by hand. Recorded reference
reviews (`reference_review`) are human decisions, not authored content. The builder reads them from
the committed case files, carries them over and derives `reference_status` from them. It refuses to
render if a review's case is no longer built.

## 7. Leakage: what was checked and what it shows

`gj leakage` now reports three families separately.

* **Lexical** (exact input, character shingles, TF-IDF paraphrase): 0 hard findings, 1 warning.
  The warning is e2-gc-02 ~ gj-daily-003, lexical 0.34: both are conversational-language goals.
  Maximum pool-vs-eval lexical similarity is 0.338; the hard threshold is 0.50.
* **Semantic/template** (behaviour signature, decision-pattern labels, human review): 0 hard, 13
  automated candidates, all reviewed.
* **Scenario** (scenario groups, registry sides, seed ids and seed text): 0 hard, 0 warnings.

The human review matters more than the automated layers. Every case and step was read against all
92 training scenarios:

1. **During the review, before release**, three atomic cases that repeated a training decision almost
   exactly were rewritten:
   * e2-clar-01 — was "all facts known → ready"; now a self-contradicting schedule;
   * e2-feas-01 — was "large gap → unrealistic with options"; now the user rules out a lower target;
   * e2-mem-01 — was "outdated item → update"; now a misattributed item.

   Five cases whose topic repeated a training example or seed were moved to other topics. Touch
   typing, a tab-grouping extension, quitting smoking, a conference talk and a team-lead book became
   mental arithmetic, a package registry, sleep, a term paper and garden design. Two steps got
   distinguishing twists: a date discrepancy on retry, and a claim of two levels.
2. **What remains** is recorded in `evaluation/leakage/v0.2.0.yaml`: 100 reviewed overlaps, 46 of them
   cross-lingual.
   * 11 strong: all are set-up or intermediate steps of multi-step cases, e.g. "local rules → research
     official sources" as s1 of e2-comp-06, whose real test is s2.
   * 78 medium: a trained behaviour under a different decisive condition, which is what an evaluation
     *should* test.
   * 4 topic_only and 7 none (automated candidates judged coincidental).
3. The automated layers found **13 of the 116** reviewed (case/step, training example) pairs. Text
   and label similarity miss most real overlaps. This is why the report never claims "no leakage", and
   why the `leakage_dispositions` gate needs a human disposition for every entry. All 100 are still
   `open`.

The case author (an AI agent, in the same session that wrote the training data) is not independent of
the training data. The review is a proposal, not an independence certificate.

## 8. Known limitations

* **Size.** 63 cases (106 model calls) is below the `eval_readiness` floor of 200 cases. Eleven
  operations have fewer than 10 model calls. Per-operation numbers are indicative only; with n=5 a
  single failure moves a rate by 20 points.
* **Same author.** Cases, references and training data come from one author. The next batch should
  be written by people who have not seen the training set.
* **References mostly unreviewed.** Human review of the 106 reference outputs started on 2026-10-01
  (D-028); `gj validate` reports how many have a decision on their current content. Cases not fully
  reviewed stay `draft_unreviewed`.
* **No semantic similarity model.** There is no embedding or translation-based similarity, so
  cross-lingual paraphrases are found only by the human review.
* **Teacher forcing** measures each step in isolation. It does not measure how errors compound in
  free-running conversations. A free-running mode (feeding the model's own outputs forward) is future
  work.

## 9. Commands

```bash
python scripts/gj.py eval build-cases [--check]     # render / verify evaluation/cases/v0.2.0
python scripts/gj.py validate                       # validates v0.1.0 (frozen) and v0.2.0
python scripts/gj.py eval run --predictor reference # must pass 106/106
python scripts/gj.py eval run --predictor naive     # must fail (0/106 today)
python scripts/gj.py leakage                        # three families, reviewed overlaps
python scripts/gj.py eval review-reference CASE --reviewer ID --from decisions.yaml --independent-rating yes|no
```
