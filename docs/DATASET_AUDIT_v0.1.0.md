# Dataset audit — GoalJourney v0.1.0

*Milestone 1.5 · 2026-09-27 · dataset v0.1.0 (93 training examples, 30 evaluation cases)*

> **Who wrote this audit.** The AI agent that authored the v0.1.0 examples also wrote this audit, so it
> shares that author's blind spots. It combines automated checks, new heuristic scanners and a
> manual read of every example. It is **not** a human review: nothing here approves, rejects or edits
> an example. Findings are recorded as *proposed* revisions in
> [`review/known_issues_v0.1.0.yaml`](../review/known_issues_v0.1.0.yaml), to be confirmed or
> dismissed by human reviewers ([`HUMAN_REVIEW_GUIDE.md`](HUMAN_REVIEW_GUIDE.md)).

Reproduce every number: `gj validate --strict`, `gj stats`, `gj coverage`, `gj audit`, `gj leakage --distribution`,
`gj review sample --check`, `gj gates`, `gj eval run --predictor reference|naive`.

## 1. Summary

* **Automated validation passes completely, and that proves little.** 93/93 examples pass schema,
  semantic lint (0 warnings under `--strict`) and the contrastive self-test. Reading the examples still
  turned up **6 examples with high-severity defects**: a wrong weekday, two arithmetic errors, an
  invented user fact, and two violations of the gender-neutrality rule. Every one of them passes every
  validator.
* **41 of 93 examples** (44%) have at least one recorded issue:
  * 6 high-severity, which must be revised;
  * 7 more with concrete medium issues, which likely need revision;
  * 10 more whose fate depends on two policy decisions (the product capability list, and how much
    confidence user-entered data can earn);
  * 18 with low-severity notes only.

  **Estimated revision need: 13 examples (14%) certain, up to 23 (25%) depending on the policy decisions.**
* **Systematic weaknesses:**
  1. Arithmetic and calendar consistency: all four time-adaptation examples contain a numeric
     inconsistency, three of them material.
  2. User-entered data rated as medium/high-confidence evidence (14 protocols).
  3. Verification that assumes product capabilities nobody has specified.
  4. Milestone dates moved without consent, which the spec does not settle.
  5. Confident general-knowledge claims.
* **Coverage is a pilot, not a training set.** Every operation is at 2–12 examples against targets of
  60–240; mixed-language input is 3.2% (target 8%); memory has 5 examples and progress 4. Each scenario
  group holds exactly one example, so there are no multi-step journeys.
* **The evaluation set re-tests the training templates.** No copy- or paraphrase-level leakage was
  detected, but manual review found **27 behavioural overlaps** between evaluation and training
  (11 strong, 8 of all overlaps cross-lingual). With 30 cases and 1–4 per operation, the evaluation
  results are indicative only.
* **Verdict:** v0.1.0 is **not training-ready**. It passes 2 of 11 release gates, and every failure has
  a stated reason (§12). **Next step:** human review of the 30-item sample, starting with the 8
  calibration items (§13).

## 2. Automated validation results

| Check | Result |
|---|---|
| `gj validate --strict` | **PASS** — 93/93 valid, 0 errors, 0 warnings; 30 scenario seeds valid; 30 eval cases valid |
| Contrastive self-test | 64 rejected outputs over 30 failure modes (each ≥ 2). All outputs in the 14 auto-detectable modes are caught by lint; 16 modes are human-only, so their labels are **not** machine-verified (0 of 3 `generic_assistant_drift`, 0/3 `blind_compliance`, 0/2 `unnecessary_research`, 0/2 `assumed_user_info`, 0/2 `generic_plan` and 0/2 `ignored_preferences` are lint-detected) |
| Evaluation sanity | reference predictor: every check passes on 30/30 cases; naive baseline fails most behavioural checks (e.g. web-research accuracy 0.17, verification rigor 0.50) — the checks discriminate |
| Tests | 225 passed |
| Leakage (hard layers) | 0 hard findings; max lexical similarity 0.374, max character similarity 0.221 (§11) |
| Review log | empty, verifies (0 decisions recorded — nobody has reviewed anything yet) |

Why this is weak evidence: the lint rules were written by the author of the data, with the data in
view, and every example was edited until it passed. Passing is partly circular. It shows the data
obeys the rules someone thought of, not that it is good.

## 3. Composition

### 3.1 Operations and languages

| Operation | RU | EN | Total | With contrastive outputs |
|---|---|---|---|---|
| goal_clarification | 4 | 5 | 9 | 7 |
| feasibility_assessment | 3 | 3 | 6 | 6 |
| journey_generation | 2 | 3 | 5 | 4 |
| task_generation | 2 | 3 | 5 | 3 |
| verification_protocol_design | 3 | 4 | 7 | 4 |
| verification_result (incl. 4 retries) | 5 | 6 | 11 | 8 |
| route_adaptation (incl. 4 time adaptation) | 5 | 5 | 10 | 6 |
| daily_plan | 3 | 3 | 6 | 5 |
| navigator_response | 5 | 7 | 12 | 7 |
| goal_change | 2 | 2 | 4 | 3 |
| web_research_decision | 2 | 3 | 5 | 4 |
| safety_classification | 3 | 5 | 8 | 4 |
| memory_extraction | 1 | 1 | 2 | 1 |
| progress_update | 1 | 2 | 3 | 2 |
| **Total** | **41** | **52** | **93** | **64 outputs on 61 examples** |

* Input language: EN 51, RU 39, **mixed 3** (`gj-clar-005`, `gj-lang-001`, `gj-lang-002`).
* Difficulty: easy 25, medium 46, hard 22. Goal size: tiny 4, medium 33, complex 35, n/a 21.
* Domains: 20 (business 14, career 12, fitness 10, programming 8, hobby 7, language learning 6, …;
  health, travel, project, research, productivity and other have 1 each).
* Every example is `synthetic/agent_authored`; there are no generated candidates, no external data and no real user data.
* **Scenario groups: 93 for 93 examples.** Every scenario appears in exactly one operation, so the
  data never shows the same user's journey across clarification → plan → verification →
  adaptation, and the group-level split is effectively per-example.

### 3.2 Safety

| Category | Examples |
|---|---|
| allowed | 84 |
| sensitive | 3 (`gj-jour-005`, `gj-nav-009`, `gj-safe-002`) |
| needs_professional_support | 3 (`gj-safe-004`, `gj-safe-005`, `gj-safe-008`) |
| high_risk | 2 (`gj-safe-003`, `gj-safe-007`) |
| restricted | 1 (`gj-safe-006`) |

Non-allowed share: 9.7% (target 12%). **10 examples are expert-tier**. The 9 above need sign-off in
medical, mental_health, financial, legal or physical_safety; `gj-mem-001` needs privacy (it stores a
third party's health condition).

### 3.3 Memory, progress, mixed language, decision summaries

* **Memory (5):** `gj-mem-001` (extraction, third-party health), `gj-mem-002` (extraction and update,
  temporary fact), `gj-mem-003` (isolation in a daily plan), `gj-mem-004` (isolation in a navigator
  answer), and `gj-lang-001` (language preference plus isolation). Only 2 are `memory_extraction`.
* **Progress (4):** `gj-prog-001` (milestone → level-up), `gj-prog-002` (streak without progress),
  `gj-prog-003` (goal exceeded), plus levels and achievements inside `gj-jour-001`.
* **Mixed language (3):** above, 3.2% of the pool.
* **Decision summaries (37):** journey 5, verification result 11, route adaptation 10, navigator 7, goal change 4.

### 3.4 Contrastive distribution

64 rejected outputs sit on 61 examples; 3 examples have two, and 32 have none. By language: RU 25,
EN 39. By failure mode: `unverified_current_facts` 7; `wrong_language` 5; `ignored_available_time` 4 and
`photo_as_proof` 4; 13 modes with 3; 13 modes with 2. At the scale-up target (≥ 20 per mode) every
mode is short by 13–18.

## 4. Missing coverage

Against the Milestone-2 target of ~2,000 examples (`gj coverage`):

| Operation | Have | Target | Gap |
|---|---|---|---|
| goal_clarification | 9 | 180 | 171 |
| feasibility_assessment | 6 | 120 | 114 |
| journey_generation | 5 | 160 | 155 |
| task_generation | 5 | 140 | 135 |
| verification_protocol_design | 7 | 160 | 153 |
| verification_result | 11 | 240 | 229 |
| route_adaptation | 10 | 240 | 230 |
| daily_plan | 6 | 140 | 134 |
| navigator_response | 12 | 220 | 208 |
| goal_change | 4 | 80 | 76 |
| web_research_decision | 5 | 100 | 95 |
| safety_classification | 8 | 100 | 92 |
| memory_extraction | 2 | 60 | 58 |
| progress_update | 3 | 60 | 57 |

Shares below target: mixed input 3.2% (8%), non-allowed safety 9.7% (12%), tiny goals 4.3% (6%).
Every domain is below 20, and every failure mode below 20 rejected outputs.

Situations that are **absent**, not just thin:

* multi-turn conversations: 2 examples have more than one user message;
* the same scenario across operations;
* long contexts (large journeys, long histories);
* adversarial evidence (instructions embedded in uploaded text or research results);
* contradictory or outdated memory;
* a user who reverses an earlier decision;
* ambiguous dates, time zones and relative dates ("next Friday");
* accessibility constraints;
* very short or low-effort messages;
* research results that are wrong or contradict each other;
* goals that are reached early or abandoned;
* offline or low-connectivity evidence.

## 5. Human review requirements

* **All 93 examples need human review.** No example has an approval, and none can be approved
  automatically (policy: `configs/review.yaml`).
* Reviewer qualifications:
  * 42 examples need a Russian reader (41 RU answers plus `gj-lang-002`, whose input is mixed);
  * 3 mixed-input examples need a reviewer who reads both languages;
  * 10 expert-tier examples need a qualified domain expert.
* **Review sample:** 30 examples in [`review/review_manifest_v0.1.0.json`](../review/review_manifest_v0.1.0.json):
  * 12 random, 9 highest-risk, 6 contrastive and 3 edge;
  * all 22 coverage categories covered, including 3 expert-tier items;
  * 8 calibration items.

  Rationale: [`HUMAN_REVIEW_GUIDE.md`](HUMAN_REVIEW_GUIDE.md) §4. Eight of the 13 examples with high or
  individual medium issues are in the sample. The other five (`gj-nav-001`, `gj-route-004`,
  `gj-route-005`, `gj-task-003`, `gj-goalchg-001`) should be reviewed right after it.

What automation can decide and what needs people (the full table is in the guide, §3):

| Class | Properties |
|---|---|
| automatically validatable | schema validity; ids and references; DAG and dependency order; dates vs. deadline and `today`; daily time budget; photo-only proof; self-report ceiling; status/criteria consistency; exposed reasoning; language script; memory must-not-mention; contrastive self-test for 14 modes |
| human review required | usefulness; goal understanding; question minimality; actionability; realism and arithmetic; verification fit; evidence interpretation; user agency; adaptation proportionality; explanation quality; Russian naturalness and gender neutrality; contrastive plausibility; 16 human-only failure modes |
| expert review required | medical, mental-health, legal, financial, physical-safety and privacy content in the 10 expert-tier examples; any health claim (e.g. weight-loss pace) |

## 6. Targeted audits (Problems 1–9)

Each problem was checked twice: by a heuristic rule in `gj audit` (counts are for expected outputs
unless stated) and by reading every example. Heuristic hits are candidates, not verdicts.

### P1 — Generic tasks

* **Heuristic:** vague titles on full, outline and added nodes. Outline and added nodes were not
  linted before; the new rule found 0 hits in expected outputs and 5 in rejected outputs, as intended.
  Stock rationales ("practice makes perfect"): 0 in expected outputs, 7 in rejected ones.
* **Manual:** tasks are concrete (object + quantity + artefact). The weak spot is realism of quantities,
  e.g. 8 SQL exercises in one 30-minute beginner session (`gj-task-003`).
* **Verdict:** low risk.

### P2 — Fake or weak verification

* **Heuristic:**
  * `user_entered_as_objective`: 14 hits in 9 examples, plus 2 evaluation references. The only required
    evidence is user-entered (`structured_result`), yet the ceiling is medium or high → **KI-015**, a
    policy decision.
  * `capability_assumption`: 6 hits in 4 examples, plus `promises_later_message` in 1 example and 1
    evaluation reference → **KI-014**.
  * `unverifiable_criterion`: 1 hit.
  * Photo-only proof: 0 (enforced by lint).
* **Manual:** KI-011, a COUNT check that compares two numbers both reported by the user, at ceiling "high".
* **Verdict:** **the dataset's main systematic weakness.** It needs:
  1. a product capability list, so the model does not promise transcription, URL fetching or
     scramble issuing that may not exist;
  2. a rule for when user-entered structured data may exceed "limited" confidence.

### P3 — Excessive questioning

* **Heuristic:** 0 hits (≤ 3 questions per clarification is lint-enforced; no non-clarification answer
  asks more than 2).
* **Manual:** one marginal question (KI-018).
* **Verdict:** good. Check question minimality in calibration.

### P4 — Missing critical questions

* **Heuristic:** 1 hit (`gj-goalchg-001` asserts that a sub-60-minute 10 km by 1 December "still works"
  without knowing the user's pace, KI-012).
* **Manual:** `gj-goalchg-002` sets a success target without asking (KI-027); `gj-time-001` assumes a job
  search (KI-002). Critical-question checks exist only for annotated clarification examples.
* **Verdict:** medium. Outside clarification, the model can learn to fill gaps with assumptions.

### P5 — Overplanning

* **Heuristic:** tiny goals 0 (the 4 tiny goals have ≤ 4 tasks). Capacity mismatch 1 (`gj-jour-001`: 47 h of
  tasks against 220 h of stated pacing, KI-008).
* **Manual:** overplanning is well controlled. The real weakness is **arithmetic consistency**:
  * `gj-time-001`: 140 h vs the actual 115 h (KI-002);
  * `gj-time-004`: a milestone date not supported by the hours (KI-003);
  * `gj-time-003`: an ungrounded 60 h (KI-007);
  * `gj-time-002`: "three times faster" (KI-029);
  * `gj-route-004`: net savings (KI-009).
* **Verdict:** all four time-adaptation examples have a numeric issue. Arithmetic must be a review focus.

### P6 — User agency

* **Heuristic:** milestone dates changed without confirmation in 3 examples (`gj-route-005`,
  `gj-time-002`, `gj-time-004`). No silent major changes and no navigator removals without confirmation
  (both lint-enforced).
* **Manual:** `gj-route-004` cuts the user's planned task from 20 to 5 decks as a "minor" change (KI-009).
* **Verdict:** a policy gap. The README says "deadline changes need consent", but lint enforces this only
  for the goal deadline. Decide whether milestone dates count (S8).

### P7 — Hallucinated external facts

* **Heuristic:**
  * current external facts are well disciplined: every `verified_with_source` claim cites provided
    research (lint), and no invented URLs, prices or rules appear in expected outputs;
  * unsupported generalisations: 17 hits (plus 3 in evaluation references);
  * novel quantities: 26 (info level).
* **Manual:** the weaker areas are **invented user details** (the niche in `gj-nav-001`, KI-006; the
  session length in `gj-nav-003`, KI-020; the currency in `gj-mem-002`, KI-024) and **confident
  generalisations** (KI-019 ×7, KI-005, a sports-medicine claim in KI-017).
* **Verdict:** medium. `must_not_mention` only catches what the author anticipated.

### P8 — Memory leakage

* **Heuristic:** retrieved-memory leaks 0 in expected outputs; 1 in the tagged rejected output, as
  intended. `must_not_mention` is enforced for 3 isolation examples. Sensitive-but-unflagged memory: 1
  (`gj-mem-001`, KI-023).
* **Manual:** no leaks found; stored memory inputs use gendered forms (KI-031).
* **Verdict:** correct where present, but with 5 examples the slice is too small to judge.

### P9 — Language, including Russian grammatical neutrality

* **Heuristic:**
  * assistant self-reference in a gendered form: 1 (`gj-task-004` «разбил», KI-004), plus 2 in rejected
    outputs (KI-032);
  * gendered address of the user: 2 hits in `gj-clar-007` («едете ли вы один», KI-005);
  * gendered identity labels in level titles: 6 hits in 3 examples (KI-013; policy needed);
  * informal «ты»: 0;
  * gendered stored memory in inputs: 2 (KI-031);
  * gendered English pronouns: 0;
  * wrong response language: 0 (lint).
* **Manual:** Russian reads naturally to the author but was written by a model, so native review is
  required. Milestone 1 fixed 4 gendered self-references by hand and missed these 2, which shows the
  heuristic is needed. Its precision on this corpus is good; its recall is unknown.
* **Verdict:** two hard violations must be fixed. A policy is needed for Russian identity labels
  (options: name the stage, not the person; or feminitive-free neutral nouns).

### X — Temporal consistency (added)

* **Heuristic:** weekday/date mismatch 1 (`gj-nav-006`: «в воскресенье 5-го», but 5 October 2026 is a
  Monday, KI-001).
* **Manual:** `gj-clar-004` ("this weekend", Saturday + Sunday) was suspected and **dismissed on
  checking**: its `today` is Friday 2026-09-25. It is recorded here because it shows that manual reading
  of dates is error-prone in both directions.

## 7. Examples with questionable quality

The full list is in [`review/known_issues_v0.1.0.yaml`](../review/known_issues_v0.1.0.yaml): 32 issues
on 41 examples (plus 1 evaluation case), each with location, description and proposed revision.

| Severity | Examples | Issues |
|---|---|---|
| **high — revise** | `gj-nav-006` (weekday), `gj-time-001` (140 h vs 115 h; assumed job search), `gj-time-004` (milestone date/buffer arithmetic), `gj-task-004` (masculine self-reference), `gj-clar-007` (masculine address), `gj-nav-001` (invented niche) | KI-001…006 |
| **medium — individual** | `gj-time-003`, `gj-jour-001`, `gj-route-004`, `gj-route-005`, `gj-task-003`, `gj-goalchg-001`, `gj-jour-004` | KI-007…013 |
| **medium — policy-dependent** | capability assumptions: `gj-vprot-001`, `gj-vprot-003`, `gj-vprot-004`, `gj-task-002`, `gj-vres-002` (+`ev-vr-01`); user-entered data as medium/high evidence: `gj-jour-002`, `gj-jour-003`, `gj-task-001`, `gj-task-005`, `gj-vprot-006` (and others above) | KI-014, KI-015 |
| **low** | 18 more (overclaiming, consistency nits, an expert check of two health claims, memory sensitivity, contrastive hygiene) | KI-016…032 |

## 8. Schema weaknesses

| # | Weakness | Consequence | Proposal |
|---|---|---|---|
| S1 | `structured_result` does not say whether data is user-entered or externally checkable | inconsistent confidence ceilings (KI-015) | `data_origin: user_entered \| third_party \| system_fetched`, or require evidence references above "limited" |
| S2 | `new_weekly_hours_planned` is a single number | temporary pace changes (a vacation) cannot be expressed (KI-003) | `pacing_changes: [{from, to, weekly_hours}]` |
| S3 | no completed-but-invalidated progress | a void agreement stays "completed" (KI-030) | `invalidated_progress: [{node_id, reason}]` |
| S4 | `goal_progress.percent` has no defined basis | 33% by milestones vs 5% by steps | `basis_type` enum plus a defined computation |
| S5 | `professional_referral.needed: false` with type and urgency | optional referral is ambiguous (KI-022) | `needed: required \| optional \| none` |
| S6 | no product capabilities in the input | protocols promise features freely (KI-014) | `input.capabilities[]` + a lint rule |
| S7 | no proposed-vs-applied state for changes | messages say "I've added" while confirmation is pending | `change_state: proposed \| applied` |
| S8 | consent covers goal deadlines only | milestone dates move silently (3 examples) | decide the policy; encode in schema and lint |
| S9 | `eval_case` lacks scenario group, template, seed and difficulty | scenario-level leakage uncheckable (fixed via sidecar) | move into the schema at eval v0.2 |
| S10 | no neutrality constraint on Russian identity labels | masculine level titles (KI-013) | naming rule + lint |
| S11 | feasibility status boundaries undefined | "likely_unrealistic" for a 28% gap (KI-026) | define thresholds in the spec |
| S12 | no revision fields on records | revisions reconstructed from review snapshots only | acceptable; add `revision_of` when rewriting |

## 9. Semantic-rule weaknesses

1. **No arithmetic checks.** Claimed totals ("about 140 hours") are never compared with node durations;
   pacing is compared with durations only by an audit heuristic.
2. **No calendar checks in lint.** Weekday/date consistency is an audit heuristic, not yet a lint rule.
3. **Russian gender neutrality** is an audit heuristic (good precision here, unknown recall).
4. **Capability assumptions** are unchecked (needs S6).
5. **Invented user facts** are undetectable unless the author listed them in `must_not_mention`
   (`gj-nav-001` passed).
6. **Generalisations and overclaiming** are unchecked by lint.
7. **Outline and added node titles** were never linted (now an audit rule).
8. **Critical-question checks** exist only for annotated clarification examples.
9. **16 of 30 failure modes are human-only**, so their contrastive labels are not machine-verified.
10. **Circularity:** rules and data share an author, and data was edited until the rules passed.
11. **Milestone consent** is not encoded (S8).

## 10. Evaluation-set weaknesses

1. **Size.** 30 cases and 173 checks; 1–4 cases per operation; dimensions have n = 2–10. Rates are
   indicative only (for n = 10, a 95% interval is about ±30 points).
2. **Same author and session as the training data**, with 27 reviewed behavioural overlaps (11 strong).
   Results measure recall of practised templates more than generalisation.
3. **Single-turn only** (1 case has more than one user message). No long contexts, no adversarial
   evidence, no erroneous research results.
4. **Language.** 12 cases lack a language check; 2 mixed-input cases; RU 12 / EN 18.
5. **Safety.** Only 3 non-allowed cases (one each: needs professional support, restricted, high risk).
   No `sensitive` case and no crisis-signal case.
6. **Check types are mostly structural** (34 equals, 18 counts, 17 lint-absent). The `human_review_focus`
   notes are never scored unless someone runs the model-output rubric.
7. **Reference outputs carry the same issues** the audit found in training: user-entered data at medium/high
   confidence (2), generalisations (3), a promise to send tasks "in the next message" (1).
8. No difficulty labels and no in-template vs novel-template slice.

The plan is in [`EVALUATION_EXPANSION_PLAN.md`](EVALUATION_EXPANSION_PLAN.md).

## 11. Leakage

Details and limits are in [`LEAKAGE_CHECKS.md`](LEAKAGE_CHECKS.md).

* 0 hard findings across exact, character, lexical-paraphrase, scenario-group and seed-id layers.
* Warnings:
  * 3 lexical pairs (max 0.374);
  * 1 seed overlap: `sc-pd-001` "read 24 books" vs `ev-wr-02` "read 12 books";
  * 5 automated template candidates.
* Manual review recorded **27 template overlaps**, 8 of them cross-lingual and invisible to text
  similarity. All 28 recorded overlaps (27 template + 1 seed) await a human disposition.

This does **not** establish that there is no leakage.

## 12. Licensing (unresolved)

`configs/licensing_status.yaml` records 5 open items. They block `training_ready`:

1. May the outputs of the LLMs that authored and will generate the data be used for training and commercial deployment?
2. Who owns the AI-authored `proprietary-internal` content, and under what licence could it be shared?
3. The base-model licence (no base model chosen yet).
4. Third-party product and exam names as nominative references.
5. Rights to reviewers' decisions and rewrites.

## 13. Release gates and next steps

`gj gates`: 2 of 11 pass (`validation_strict`, `leakage_hard_clean`).

**Failing:**

| Gate | Reason |
|---|---|
| review_all_approved | 0/93 approved |
| findings_acknowledged | nothing approved yet |
| known_issues_closed | 15 open medium/high issues |
| reviewer_diversity | no reviewers yet |
| calibration_agreement | no double reviews yet |
| leakage_dispositions | 28 open |
| coverage_minimums | 0 approved of 1,000 needed |
| eval_readiness | 30 of 200 cases |
| licensing_resolved | 5 open |

**Recommended order:**

1. Register reviewers and review the 8 calibration items independently (two or more reviewers,
   including one native Russian speaker). Discuss disagreements, then adjust rubric anchors if needed.
2. Review the remaining 22 sample items, then the other 63 examples. Confirm or dismiss each known
   issue (`gj review revise`).
3. Decide the four policy questions: product capability list; ceilings for user-entered data;
   milestone-date consent; Russian identity labels. Then revise the affected examples as v0.1.1.
   Content edits invalidate approvals, and every old version stays in the snapshots.
4. Decide the 28 leakage dispositions. Replace seed `sc-pd-001` or `ev-wr-02` before any generation.
5. Promote the audit heuristics with good precision (weekday/date, Russian gendered forms) to lint
   rules, and add arithmetic checks.
6. Resolve the licensing items before any training run.
7. Only then start the Milestone-2 scale-up, together with the evaluation expansion (not after it).
