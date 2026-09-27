# GoalJourney Dataset Specification — v0.1.0

This document is the contract for the GoalJourney training and evaluation data: what an example
is, what each AI operation must return, which behaviours are enforced automatically, how examples
are reviewed, split, versioned and exported. The architectural rationale is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

**Status of v0.1.0:** 93 agent-authored synthetic examples and 30 evaluation cases, all passing
automated validation, **none human-reviewed yet** (release `draft_unreviewed`). Synthetic data is
not ground truth — see §12.

---

## 1. Scope

The dataset teaches a small (~4B) open-weight multilingual model to act as **GoalJourney
Navigator**: a planner / navigator / coach for one user and one goal. It is not a general assistant.
The model receives one JSON request (`operation` + context) and returns one JSON object whose
schema depends on the operation. Keys and enums are English; user-facing strings are Russian or
English, following the user.

## 2. Versions

All versions live in [`configs/versions.yaml`](configs/versions.yaml) and are stamped into every
release manifest and generation run.

| Version | Current | Covers |
|---|---|---|
| `dataset_version` | 0.1.0 | `data/{train,validation,test}/goaljourney-v<ver>.jsonl` + manifest |
| `schema_version` | 0.1.0 | `schemas/*.json` (`$id` contains `v0.1.0`), `schema_version` in every record |
| `navigator_prompt_version` | 0.1.0 | `prompts/navigator/v0.1.0/system.md` (runtime prompt used in SFT export and eval) |
| `generation_prompt_version` | 0.1.0 | `prompts/generation/v0.1.0/` (teacher prompts) |
| `pipeline_version` | 0.1.0 | `gjcore/`, `generation/` code |
| `evaluation_version` | 0.1.0 | `evaluation/cases/v0.1.0/` + check semantics |
| `base_model` | unset | chosen later; recorded here, never hard-coded |

Releases are immutable: `gj split` refuses to overwrite an existing dataset version with different
content (identical rebuilds are a no-op). Change content → bump `dataset_version`.

## 3. Layout

```
schemas/                   JSON Schema 2020-12 (entities, 14 operation outputs, record envelopes)
data/raw/examples/         authored examples, YAML, one file per behaviour family
data/generated/<run_id>/   pipeline candidates + rejected + run manifest (committed, reviewable)
data/reviewed/reviews.jsonl  append-only human review log (keyed by content hash)
data/{train,validation,test}/goaljourney-v<ver>.jsonl   immutable releases
data/manifests/goaljourney-v<ver>.json                  release manifest (hashes, counts, versions)
generation/scenarios/      scenario seeds for synthetic scale-up
generation/validators/     schema/semantic/record/similarity validators
generation/generators/     providers, teacher prompt rendering, candidate generator
generation/pipelines/      validate, stats, coverage, review, split, export, generate
evaluation/cases/v0.1.0/   evaluation cases with automated checks
evaluation/rubrics/        dataset-quality rubric and model-output rubric (human review)
evaluation/metrics/        check implementations and aggregation
evaluation/runners/        predictors (reference, naive, model), runner, case validator
prompts/                   navigator runtime prompt and teacher prompts (versioned)
configs/                   versions, dataset, generation, evaluation, export, coverage targets
```

## 4. Example record

Schema: [`schemas/example_record.json`](schemas/example_record.json).

| Field | Meaning |
|---|---|
| `id` | `gj-<family>-NNN` (authored) or `gj-gen-NNNNN` (generated) |
| `schema_version` | schema version the record was written against |
| `task_type` | operation → selects the output schema |
| `behavior[]` | behaviours trained (clarification, feasibility, journey, task, verification_protocol, verification_decision, verification_retry, route_adaptation, navigator, daily_prioritization, time_adaptation, goal_change, decision_summary, web_research, source_awareness, safety, memory, progress, scope, language, user_agency) |
| `language` | language of the ideal answer (`ru`/`en`) |
| `input_language` | language of the user's messages (`ru`/`en`/`mixed`) |
| `domain`, `difficulty`, `goal_size`, `tags` | diversity axes |
| `safety_category` | `allowed` · `sensitive` · `high_risk` · `needs_professional_support` · `restricted` |
| `scenario_group` | unit of splitting — a group never straddles train/validation |
| `input` | the model request (`schemas/input_context.json`) |
| `expected_output` | the ideal output (validated against the operation schema) |
| `contrastive[]` | rejected outputs: `{id, failure_modes[], output, critique}` |
| `annotations` | validator/reviewer knowledge, never shown to the model: `known_targets`, `critical_targets`, `irrelevant_targets`, `must_not_mention`, `rationale` |
| `provenance` | `source` (synthetic/human_authored/licensed_external), `method` (agent_authored/pipeline_generated/human_written/human_edited), `author`, `created`, `license`, run/prompt/model ids for generated data |
| `review_status`, `content_hash` | computed at release time; not authored |

**Content hash** = SHA-256 of canonical JSON of `{task_type, input, expected_output, contrastive}`.
A review approves one exact hash; editing trainable content makes the review `stale`.

Why this differs from the brief's suggested format: see `docs/ARCHITECTURE.md` §3.

## 5. Operations

One input schema (`input_context.json`), fourteen output schemas. Every user-facing output carries
`response_language` and `message_to_user`; `memory_extraction` and `web_research_decision` are
internal (message optional).

| Operation | Schema | Brief type | Core contract |
|---|---|---|---|
| `goal_clarification` | `goal_clarification.json` | A | ≤ 5 questions (lint: > 4 is an error, 1–3 expected); each has `targets` (controlled vocabulary) and `impact`; `ready_to_plan=true` ⇔ no questions |
| `feasibility_assessment` | `feasibility.json` | B | `feasible`/`uncertain`/`likely_unrealistic`; unrealistic ⇒ adjustment options; uncertain ⇒ missing info or research |
| `journey_generation` | `journey_generation.json` + `journey.json` | C | DAG of nodes in regions/milestones; first region detailed with tasks + protocols; pacing ≤ available time; dates ≤ deadline; levels & achievements tied to verified progress |
| `task_generation` | `task_generation.json` + `task.json` | D | 1–6 operational tasks with measurable results, fitting sessions, each with a verification protocol |
| `verification_protocol_design` | `verification_protocol_design.json` + `verification_protocol.json` | E | methods fit the task nature; photo never sufficient alone; self-report ⇒ `limited` ceiling |
| `verification_result` | `verification_result.json` | F, G | per-criterion results; verified ⇔ all met; insufficient ⇒ `needs_more_evidence`; rejected ⇒ some criterion `not_met`; attempt number follows history |
| `route_adaptation` | `route_adaptation.json` | H, K | change set vs the journey; completed nodes preserved; major changes and goal-deadline changes need confirmation; time changes set `new_weekly_hours_planned` within budget |
| `daily_plan` | `daily_plan.json` | J | ≤ 3 tasks (schema max 5), total ≤ available minutes, dependencies satisfied, near-due work first, `next_action` |
| `navigator_response` | `navigator_response.json` | I | contextual answer; proposed changes carry a decision summary and confirmation; off-topic ⇒ `in_scope=false`, no changes |
| `goal_change` | `goal_change.json` | L | minor / major / new goal; every completed node preserved or discarded with reason; new goal ⇒ separate goal, original paused with history |
| `web_research_decision` | `web_research_decision.json` | N | research only when current external facts change the route; hearsay listed as unsupported claims |
| `safety_classification` | `safety.json` | safety | category, role (full / planning support only / declined), referral, boundaries |
| `memory_extraction` | `memory_extraction.json` + `memory.json` | memory | user vs goal layer; third-party and unneeded sensitive data not stored |
| `progress_update` | `progress_update.json` | levels | progress, level and achievements from verified evidence only |

`decision_summary` (Type M, `decision_summary.json`) is embedded wherever important changes
happen: `{what_changed, why, impact, alternatives_considered[]}`, concise, in the user's language,
never hidden reasoning.

## 6. Journey grammar

Goal → Region (ordered) → Milestone (success criteria, target date) → Node. Node types: `task`,
`challenge`, `ai_checkpoint`, `decision_point` (with options), `verification`. Achievements are a
separate list whose unlock types are real progress only (`first_verified_task`,
`first_real_world_result`, `milestone_verified`, `region_completed`, `capability_demonstrated`,
`goal_completed`, `goal_exceeded`) — there is deliberately no streak/login type. Levels are
goal-specific (`index`, `title`, `unlock_milestone_id`).

Dependencies live only on nodes (`depends_on`) — a single source of truth, validated as a DAG and
as never pointing into a later region. Near-term nodes are `detail_level: full` with a task spec;
later nodes stay `outline` until their region opens (progressive disclosure against overplanning).

## 7. Verification policy

* Method must fit the task nature (skill → practical test/questions; writing → artifact review;
  software → URL/repository + functional checks; research → structured results with sources;
  physical/habit → structured self-report or data export; business → artifacts/structured results).
* **A photo or screenshot is never sufficient alone** (`VP_PHOTO_ONLY`, `VR_PHOTO_ONLY_VERIFIED`).
  It is valid as part of a combination (photo + explanation + follow-up questions).
* Self-report is legitimate when objective proof is impossible or intrusive; such protocols set
  `self_report_only=true`, `confidence_ceiling=limited`, and results carry `confidence=limited`.
  Demanding photo/video beyond such a protocol is an error.
* The model is text-only in v0.1: images/audio/video reach it as `evidence.description` from a
  captioner/transcriber or the user (`description_source`), URLs as a system-fetched summary.
* Privacy: protocols never ask for third-party personal data or private documents when a
  structured summary suffices.

## 8. Source awareness and web research

* Current external facts that change the plan (laws, prices, schedules, exam rules, product specs,
  location-specific rules) are never asserted from memory. They appear as `external_claims` with
  `needs_verification`, as research tasks in the route, or trigger `web_research_decision`.
* `verified_with_source` claims must cite a source whose URL is in the input's `research_results`
  (`CLAIM_SOURCE_NOT_IN_CONTEXT`); sources can't be invented.
* Simulated research results in the dataset use reserved domains (`example.org`, `example.com`)
  and generic or fictional entities, so the model learns the *pattern* (cite what was researched)
  without learning fabricated facts about real organisations.
* Hearsay ("a friend said…") is recorded as `unsupported_claims` and verified.

## 9. Safety

| Category | Role | Behaviour |
|---|---|---|
| `allowed` | `full_navigator` | no hedging, no unnecessary warnings (over-refusal is a failure mode) |
| `sensitive` | full navigator with explicit boundaries | e.g. debt, weight, legal paperwork; referral optional |
| `high_risk` | `planning_support_only` | referral required; dangerous methods declined; safer reframing offered |
| `needs_professional_support` | `planning_support_only` | named professional and urgency; emergency guidance where symptoms warrant |
| `restricted` | `declined` | brief refusal, no journey; legitimate alternative when one exists |

The navigator never presents itself as a doctor, lawyer, therapist, nutritionist or financial
adviser and never prescribes doses, diets, legal strategy or investments.

## 10. Memory

* **User layer** (`scope=user`): stable, cross-goal facts — schedule, work/learning style, general
  preferences, stable constraints. Never health or other sensitive data.
* **Goal layer** (`scope=goal`, `goal_id` required): everything bound to one goal.
* Third-party information is not stored; only its planning consequence is.
* Retrieval noise: `input.retrieved_memory` may contain items from other goals; outputs must not
  use them (tested with `annotations.must_not_mention`).

## 11. Language

* The answer follows the language of the user's own messages; with mixed input, the predominant
  language, then a stored language preference; the app locale is only a hint.
* Keys and enum values are English in both languages — no separate product logic per language.
* **Russian persona voice:** the navigator's self-reference avoids gendered past-tense forms
  ("Понятно", "Предлагаю", "Задачи заменены" rather than "Понял", "Заменил") so the persona has no
  grammatical gender until the product decides otherwise. Users are never assigned a gender.

## 12. Contrastive examples and failure modes

Bad behaviour is attached to a good example as `contrastive[]` outputs, never stored as a
standalone target. SFT uses only `expected_output`; preference export pairs it with each rejected
output. Rejected outputs must be **schema-valid** (the failure is behavioural, not formatting).

The catalogue ([`prompts/generation/v0.1.0/failure_modes.yaml`](prompts/generation/v0.1.0/failure_modes.yaml))
defines 30 failure modes. 14 are **auto**: the linter must detect every instance, and validation
fails if a tagged contrastive output is not caught (a self-test of the linter). The rest are
best-effort or human-only (e.g. `generic_plan`, `blind_compliance`, `ignored_preferences`).

v0.1.0 contains 64 contrastive outputs; every failure mode has ≥ 2 and the 15 failure types named
in the brief have 2–7 each.

## 13. Validation

`gj validate` runs, for every example: envelope schema → output schema → semantic lint →
metadata consistency → contrastive self-test; plus a YAML authoring guard, near-duplicate
detection across scenario groups, scenario-seed validation and evaluation-case validation (every
reference output must pass its own checks).

The **semantic linter** (`generation/validators/semantic.py`) holds ~115 coded rules, e.g.:

| Area | Rules (codes) |
|---|---|
| Common | `LANG_MISMATCH`, `LANG_SCRIPT`, `EXPOSED_REASONING`, `PRETENDS_PROFESSIONAL`, `MEMORY_LEAK`, `CLAIM_SOURCE_NOT_IN_CONTEXT` |
| Clarification | `Q_TOO_MANY`, `Q_ASKS_KNOWN`, `Q_IRRELEVANT_TARGET`, `Q_MISSED_CRITICAL`, `Q_READY_WITH_QUESTIONS` |
| Feasibility | `F_NO_ADJUSTMENTS`, `F_UNCERTAIN_UNEXPLAINED`, `F_NO_RISKS` |
| Journey | `J_CYCLE`, `J_BAD_REF`, `J_DEP_ORDER`, `J_DEADLINE`, `J_PAST_DATE`, `J_OVER_TIME`, `J_AVAILABLE_BLOCKED`, `J_NO_START`, `J_OVERPLAN`, `J_TASK_NO_PROTOCOL` |
| Tasks | `T_VAGUE_TITLE`, `T_UNMEASURABLE`, `T_EXCEEDS_SESSION`, `T_BAD_DEP` |
| Protocols | `VP_PHOTO_ONLY`, `VP_SELF_REPORT_CEILING`, `VP_WEAK_FOR_VERIFIABLE`, `VP_NATURE_MISMATCH`, `VP_CEILING_TOO_HIGH` |
| Verification | `VR_VERIFIED_UNMET`, `VR_PHOTO_ONLY_VERIFIED`, `VR_REJECT_WITHOUT_FAILURE`, `VR_SELF_REPORT_CONFIDENCE`, `VR_BASIS_MISMATCH`, `VR_OVER_CONFIDENT`, `VR_DEMANDS_OBJECTIVE_FOR_SELF_REPORT`, `VR_SELF_REPORT_DISMISSED`, `VR_ATTEMPT` |
| Adaptation | `RA_REMOVED_COMPLETED`, `RA_PROGRESS_NOT_PRESERVED`, `RA_MAJOR_NO_CONFIRM`, `RA_GOAL_DEADLINE_NO_CONFIRM`, `RA_OVER_TIME`, `RA_TIME_CHANGE_IGNORED`, `RA_DEADLINE_BEYOND_GOAL` |
| Daily plan | `DP_OVER_TIME`, `DP_TOO_MANY`, `DP_BLOCKED_TASK`, `DP_DONE_TASK`, `DP_IGNORED_DUE` |
| Navigator | `NAV_SILENT_CHANGE`, `NAV_NO_CONFIRM`, `NAV_OFF_TOPIC_CHANGES`, `NAV_SCOPE_MISMATCH`, `NAV_DECLINE_NO_OPTIONS` |
| Goal change | `GC_NO_CONFIRM`, `GC_PROGRESS_UNACCOUNTED`, `GC_DISCARDED_ALL`, `GC_NEW_GOAL_IN_PLACE` |
| Research | `WR_NO_FACTS`, `WR_NO_QUERIES`, `WR_INCONSISTENT`, `WR_UNSUPPORTED_IGNORED` |
| Safety | `S_RESTRICTED_PROCEED`, `S_HIGH_RISK_ROLE`, `S_NO_REFERRAL`, `S_OVER_REFUSAL`, `S_NO_BOUNDARIES`, `S_CATEGORY_MISMATCH` |
| Memory | `MEM_WRONG_GOAL`, `MEM_SENSITIVE_USER_SCOPE`, `MEM_THIRD_PARTY_STORED`, `MEM_UNKNOWN_ID` |
| Progress | `PU_ACTIVITY_BASED`, `PU_LEVEL_UNSUPPORTED`, `PU_UNVERIFIED_EVIDENCE`, `PU_PROGRESS_WITHOUT_VERIFICATION` |

Errors block; warnings are surfaced for review (`--strict` makes them blocking). Heuristic rules
(language script ratio, vagueness patterns, professional-authority phrases) catch clear cases, not
style — style is a human-review criterion.

## 14. Human review

Rubric: [`evaluation/rubrics/dataset_quality_rubric.yaml`](evaluation/rubrics/dataset_quality_rubric.yaml)
— 12 criteria (correctness, relevance, minimality, actionability, realism, dependency
correctness, verification validity, non-hallucination, user agency, safety, language quality,
contrastive quality), 1–4 anchors, applicability per operation. **Approval requires every
applicable score ≥ 3 and the hard gates `safety` and `non_hallucination` = 4.**

```
gj review export --out sheet.yaml     # pending examples with rendering + empty rubric
# reviewer fills decision / scores / notes
gj review apply sheet.yaml --reviewer NAME   # validates against the rubric, appends to the log
gj review status
```

## 15. Splits and releases

* **train / validation:** deterministic split by `scenario_group`, stratified by task type
  (seeded hash ordering, `validation_fraction` 0.15, strata with ≥ 4 examples contribute).
* **test:** the evaluation cases (authored separately), frozen into the release.
* **Leakage guard:** no training input may be a near-duplicate of an evaluation input (5-char
  shingle Jaccard ≥ 0.55 aborts the build). v0.1.0 maximum: 0.22.
* **Review policy:** `require_approved` (only approved content) or `allow_pending` (pending
  *authored* examples allowed, release marked `draft_unreviewed`). Generated candidates enter a
  release only when approved, under either policy.

## 16. Export formats

`gj export --format sft|preference|eval` writes to `exports/v<ver>/` (derivable, git-ignored):

* **sft**: `{"messages": [system, user, assistant], "metadata": {...}}` — system = navigator prompt,
  user = the request JSON, assistant = the output JSON. Chat templates are applied by the training
  framework, so the data stays base-model-agnostic.
* **preference**: `{"prompt": [system, user], "chosen": [...], "rejected": [...], "metadata": {..., "failure_modes"}}`.
* **eval**: `{"id", "messages": [system, user], "task_type", "dimensions", "checks", ...}`.

Evaluation of a model uses exactly the same prompt (`gjcore/prompting.py`).

## 17. Evaluation

30 cases in `evaluation/cases/v0.1.0/` (173 automated checks) cover the 12 dimensions: question
quality, planning quality, task quality, verification quality, route adaptation, user agency,
hallucination resistance, web research decisions, safety behaviour, language consistency,
structured output validity, memory isolation.

Metrics (automated, per metric and per dimension; **no overall score by design**):
schema validity, semantic validity, unnecessary question rate, missing critical question rate,
verification status accuracy, verification rigor, route preservation, hallucination rate, web
research decision accuracy, safety policy compliance, language match, memory leak rate, user
agency compliance, constraint compliance, task actionability, decision transparency, scope
adherence, progress integrity, feasibility judgement.

Human review of model outputs uses a separate rubric
([`evaluation/rubrics/model_output_rubric.yaml`](evaluation/rubrics/model_output_rubric.yaml)) and
a separate sheet (`gj eval review-sheet`); human scores are never merged into automated metrics.

Sanity instruments: the `reference` predictor must pass every check; the `naive` baseline (always
English, fixed questionnaire, verifies everything, never researches, everything "allowed") is
schema-valid on every case and must fail most behavioural checks.

## 18. Synthetic generation and scale-up (Milestone 2)

Pipeline: scenario seed → stage 1 (teacher writes the input) → stage 2 (teacher writes the ideal
output, with navigator principles, operation guide, rubric and at most one approved few-shot from
a different domain) → optional stage 3 (rejected output for a failure mode) → validation → human
review → release. Every stage is validated; failures are kept in `rejected.jsonl` with reasons.

Controls: provider-agnostic (`configs/generation.yaml`; Anthropic via the official SDK with
refusal fallback, any OpenAI-compatible endpoint, or offline replay); credentials only from the
environment; hard cap of 50 candidates per run; run manifest with versions, provider/model,
prompt file hashes and config snapshot.

Targets ([`configs/coverage_targets.yaml`](configs/coverage_targets.yaml)): ~2,000 training
examples weighted towards verification, adaptation and navigation; RU/EN 50/50; ≥ 8% mixed-input,
≥ 12% non-allowed safety, ≥ 35% with contrastive outputs, ≥ 40 per domain, ≥ 20 per failure mode.
`gj coverage` prints the gaps and how many seed scenarios can fill each.

Recommended scale-up loop: generate ≤ 50 → validate → review → promote → `gj coverage` → adjust
seeds → repeat; bump `dataset_version` for each release; grow evaluation cases to 200–500 in
parallel, authored separately and leakage-checked.

## 19. Authoring guidelines

* Write natural Russian/English; realistic personas; no real personal data; never infer a user's
  gender or pronouns.
* In YAML flow collections (`[a, b]`, `{k: v}`) quote any item containing prose, commas, `?` or
  `: ` — the validator's authoring guard flags likely mis-splits.
* Dates are relative to `input.today`; every milestone ≤ goal deadline.
* Keep the first region detailed and later regions as outlines.
* Contrastive outputs: realistic mistakes, schema-valid, precisely tagged.

## 20. Known limitations (v0.1.0)

* Examples were written by an AI agent under this spec; they need human review before training.
* Language and vagueness checks are heuristics; semantic lint cannot judge whether a plan is
  generic or a tone is right — those are human-review criteria.
* Near-duplicate detection is O(n²) character-shingle Jaccard; move to MinHash/LSH beyond ~20k items.
* Evaluation cases (30) are below the 200–500 target; they are a first suite, not a benchmark.
* `memory_extraction` (2) and `progress_update` (3) have few training examples.
