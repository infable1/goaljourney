# GoalJourney Dataset Specification — v0.1.1

This document is the contract for the GoalJourney training and evaluation data: what an example
is, what each AI operation must return, which behaviours are enforced automatically, how examples
are reviewed, split, versioned and exported. The architectural rationale is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

**Status of v0.1.1:** 93 agent-authored synthetic examples; human review is in progress and was
not complete when v0.1.1 was built (release `draft_unreviewed`; live counts: `gj review stats`).
Synthetic data is not ground truth — see §14.

* **Milestone 1.5** added the human-review system, audits, layered leakage checks and release gates.
* **Milestone 1.6** made the following changes:
  * decided the open policies ([`docs/POLICY_DECISIONS_v0.1.1.md`](docs/POLICY_DECISIONS_v0.1.1.md));
  * revised 36 examples through a revision ledger (v0.1.0 is immutable);
  * added deterministic validators for dates, arithmetic, deadline autonomy, capabilities, evidence
    ceilings, provenance and Russian voice;
  * replaced the evaluation set with v0.2.0: 63 cases, atomic, composite and longitudinal
    ([`docs/EVALUATION_V0.2_DESIGN.md`](docs/EVALUATION_V0.2_DESIGN.md)).

Audit: [`docs/DATASET_AUDIT_v0.1.1.md`](docs/DATASET_AUDIT_v0.1.1.md). v0.1.1 is not
training-ready.

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
| `dataset_version` | 0.1.1 | `data/{train,validation,test}/goaljourney-v<ver>.jsonl` + manifest; derived versions list every change in `data/revisions/v<ver>.yaml` |
| `schema_version` | 0.1.1 | `schemas/*.json` (`$id` contains `v0.1.1`); earlier versions frozen in `schemas/archive/v<ver>/`; every record is validated with the schemas and lint rules of its own `schema_version` |
| `navigator_prompt_version` | 0.1.1 | `prompts/navigator/v0.1.1/system.md` (runtime prompt used in SFT export and eval; adds POL-A…E) |
| `generation_prompt_version` | 0.1.1 | `prompts/generation/v0.1.1/` (teacher prompts; policies and new failure modes) |
| `pipeline_version` | 0.4.0 | `gjcore/`, `generation/` code (0.4.0: review governance modes, solo_owner default, gate scopes, training-eligibility accounting in release manifests; 0.3.0: v0.1.1 validators, revision ledger, review log v0.3, eval builders) |
| `evaluation_version` | 0.2.0 | `evaluation/cases/v0.2.0/` (generated from `evaluation/builders/v0_2_0/`) + check semantics; v0.1.0 kept frozen |
| `base_model` | unset | chosen later; recorded here, never hard-coded |

Releases are immutable: `gj split` refuses to overwrite an existing dataset version with different
data (identical data files are a no-op; the stored manifest is kept as built even if a newer pipeline
would describe it differently). Change content → bump `dataset_version`. The review rubric has its own
version (`evaluation/rubrics/dataset_review_rubric_v0.2.1.yaml`, 0.2.1; 0.2.0 is kept in
`dataset_review_rubric.yaml`), stamped into every review decision.

## 3. Layout

```
schemas/                   JSON Schema 2020-12 (entities, 14 operation outputs, record envelopes)
data/raw/examples/         authored examples, YAML, one file per behaviour family
data/generated/<run_id>/   pipeline candidates + rejected + run manifest (committed, reviewable)
data/reviewed/review_events.jsonl   append-only, hash-chained human review log (decisions per content hash)
data/reviewed/snapshots/   exact reviewed content, one file per content hash (never overwritten)
review/                    reviewer registry, review sample manifest + per-version sample status, known issues, audit findings
data/revisions/            revision ledger per derived dataset version + content snapshots
data/scenarios/            behavioural scenario registry (train and eval sides)
data/{train,validation,test}/goaljourney-v<ver>.jsonl   immutable releases
data/manifests/goaljourney-v<ver>.json                  release manifest (hashes, counts, versions)
generation/scenarios/      scenario seeds for synthetic scale-up
generation/validators/     schema/semantic/record/similarity validators
generation/generators/     providers, teacher prompt rendering, candidate generator
generation/pipelines/      validate, stats, coverage, generate, review(+store, sampling), audit, leakage, gates, split, export
evaluation/cases/v0.2.0/   evaluation cases with automated checks (generated; v0.1.0/ frozen)
evaluation/builders/       evaluation authoring source (`gj eval build-cases`)
evaluation/seeds/          independent evaluation seeds
evaluation/leakage/        evaluation-side leakage metadata (scenario groups, templates, reviewed overlaps)
evaluation/rubrics/        dataset review rubric (v0.2.0), legacy v0.1 rubric, model-output rubric
evaluation/metrics/        check implementations and aggregation
evaluation/runners/        predictors (reference, naive, model), runner, case validator
prompts/                   navigator runtime prompt and teacher prompts (versioned)
configs/                   versions, dataset, generation, evaluation, export, coverage targets,
                           review, release gates, licensing status, product capabilities, evidence policy
docs/                      architecture, policy decisions, dataset audits, human review guide, leakage checks,
                           evaluation design and expansion plan
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
A review approves one exact hash; editing trainable content returns the example to `pending`
(detail `content_changed`) until it is reviewed again.

v0.1.1 adds `topic_group` (the v0.1.0 topical group, kept for traceability) and `revision` (dataset
version, revision ids, previous content hash) for revised rows.

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
* The model is text-only: images and audio reach it as `evidence.description` from an image
  describer or a transcriber (`description_source`), files as extracted text, and URLs as one
  system-fetched extract.
* **Capabilities (POL-A).** Only *available* capabilities may be required, relied on or promised
  (`configs/product_capabilities.yaml`). Video analysis, tracker sync, proactive messages and the
  calendar are *planned*; API calls, account access and contacting third parties are *unsupported*.
  Codes: `VP_METHOD_UNAVAILABLE`, `EVIDENCE_SOURCE_UNAVAILABLE`, `CAPABILITY_PROMISE`.
* **Confidence follows the evidence class (POL-B, `configs/evidence_policy.yaml`).**
  * `self_report`, `user_entered_data` and `image_description` → at most *limited*;
  * `inspectable_artifact` and `externally_verifiable` → up to *high*;
  * user-entered data with checkable references plus a URL spot-check → *medium*;
  * an image together with a non-image required method → *medium*.

  Codes: `VP_CEILING_ABOVE_EVIDENCE`, `VR_CONFIDENCE_ABOVE_EVIDENCE`. A contradiction between a claim
  and the evidence is recorded in `contradictions` and blocks `verified` (`VR_CONTRADICTION_VERIFIED`).
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
* **Russian voice (POL-D):**
  * The navigator's self-reference avoids gendered past-tense forms («Понятно», «Предлагаю», «Задачи
    заменены» rather than «Понял», «Заменил»).
  * The user is never addressed with a gendered form, even when the user describes themselves with
    one.
  * Stored memory is written without gendered forms.
  * Level and badge titles may use natural role nouns.

  Codes: `RU_GENDERED_SELF_REFERENCE`, `RU_GENDERED_USER_ADDRESS`, `RU_GENDERED_MEMORY`.

## 12. Contrastive examples and failure modes

Bad behaviour is attached to a good example as `contrastive[]` outputs, never stored as a
standalone target. SFT uses only `expected_output`; preference export pairs it with each rejected
output. Rejected outputs must be **schema-valid** (the failure is behavioural, not formatting).

The catalogue ([`prompts/generation/v0.1.1/failure_modes.yaml`](prompts/generation/v0.1.1/failure_modes.yaml))
defines 36 failure modes. v0.1.1 adds six: `calendar_error`, `arithmetic_error`,
`unavailable_capability`, `overconfident_verification`, `ignored_contradiction` and
`gendered_language`.

* **Auto modes.** The linter must detect every instance, and validation fails if a tagged contrastive
  output is not caught (a self-test of the linter).
* **Other modes** are best-effort or human-only, e.g. `generic_plan`, `blind_compliance`,
  `ignored_preferences`.
* **Untagged defects.** At v0.1.1, a rejected output with lint errors outside its tagged modes gets a
  warning, so untagged extra defects surface.

v0.1.1 contains 64 contrastive outputs covering 32 of the 36 modes (each ≥ 2). Four new modes have
no rejected example yet: `calendar_error`, `arithmetic_error`, `ignored_contradiction` and
`gendered_language`.

## 13. Validation

`gj validate` runs, for every example: envelope schema → output schema → semantic lint →
metadata consistency → contrastive self-test; plus a YAML authoring guard, near-duplicate
detection across scenario groups, scenario-seed validation and evaluation-case validation (every
reference output must pass its own checks).

The **semantic linter** (`generation/validators/semantic.py`, with `calendar.py`, `workload.py`,
`quantities.py`, `policy.py`, `provenance.py` and `russian.py`) holds ~170 coded rules. Rules added in
v0.1.1 apply only to records with `schema_version` ≥ 0.1.1. Inputs are linted too: protocols given in
the input, weekdays in earlier assistant turns, and memory wording. Examples:

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
| Calendar (v0.1.1) | `DATE_WEEKDAY_MISMATCH` |
| Arithmetic (v0.1.1) | `ARITH_REMAINING_BEFORE/AFTER`, `ARITH_UNESTIMATED`, `ARITH_WEEKS_NEEDED/AVAILABLE`, `ARITH_FITS`, `ARITH_HORIZON_DATE`, `ARITH_PACE`, `ARITH_TEXT_UNDERIVABLE`, `MILESTONE_DATE_INFEASIBLE`, `J_MILESTONE_OVERBOOKED`, `T_OVER_CAPACITY` |
| Deadline autonomy (v0.1.1) | `RA_DEADLINE_AUTONOMY_MISSING/WRONG`, `RA_DEADLINE_STATE_INCONSISTENT`, `RA_MILESTONE_NO_SUMMARY`, `RA_UNDECLARED_DEADLINE_CHANGE`, `RA_WORKLOAD_MISSING`, `RA_UNFIT_NO_DECISION`, `NAV_RESCHEDULE_UNDECLARED`, `NAV_GOAL_DEADLINE_NO_CONFIRM`, `GC_DEADLINE_NO_CONFIRM`, `J_GOAL_DEADLINE_CHANGED` |
| Capabilities & evidence (v0.1.1) | `VP_METHOD_UNAVAILABLE`, `EVIDENCE_SOURCE_UNAVAILABLE`, `CAPABILITY_PROMISE`, `VP_CEILING_ABOVE_EVIDENCE`, `VR_CONFIDENCE_ABOVE_EVIDENCE`, `VR_CONTRADICTION_VERIFIED`, `VR_CONTRADICTION_BAD_REF` |
| Provenance (v0.1.1) | `FACT_BAD_REF`, `FACT_NOT_GROUNDED`, `FACT_PROVENANCE_UPGRADED`, `FACT_VERIFIED_WITHOUT_SOURCE`, `MEM_SOURCE_NOT_GROUNDED` |
| Russian voice (v0.1.1) | `RU_GENDERED_SELF_REFERENCE`, `RU_GENDERED_USER_ADDRESS`, `RU_GENDERED_MEMORY` |

**Fact provenance (POL-E).** Answers that rely on facts list them in `facts_used`, each with
`source_type` (`user_provided | model_inferred | externally_verified | unknown`) and a `source_ref`
into the context (`conversation[i]`, `user_memory:<id>`, `research:<id>`, `events[i]`, …). An
inferred fact is never presented as user-provided or verified. Conversational text itself does not
carry provenance fields.

Errors block; warnings are surfaced for review (`--strict` makes them blocking). Heuristic rules
(language script ratio, vagueness patterns, professional-authority phrases) catch clear cases, not
style — style is a human-review criterion.

**Audit heuristics** (`gj audit`, `generation/pipelines/audit.py`) are separate from lint: they flag
*candidates* for reviewers (Problems 1–9 of Milestone 1.5 plus weekday/date consistency — generic
tasks, user-entered data rated as objective, product-capability assumptions, milestone dates changed
without consent, unsupported generalisations, retrieved-memory leaks, Russian gendered forms, …) and
never block. A rule graduates to lint only once its precision is established on reviewed data.

## 14. Human review

Full workflow: [`docs/HUMAN_REVIEW_GUIDE.md`](docs/HUMAN_REVIEW_GUIDE.md). Principle: *would we be
comfortable teaching a model this behaviour?*

**Pipeline stages.** raw → validated (`gj validate`) → human review (`gj review …`) → approved →
split (`gj split`) → training export (`gj export`, gated). Only `approved` content can reach a
training file (§16).

**Rubric** ([`evaluation/rubrics/dataset_review_rubric_v0.2.1.yaml`](evaluation/rubrics/dataset_review_rubric_v0.2.1.yaml), v0.2.1; v0.2.0 plus a clarified safety anchor for restricted goals):
categorical ratings (`good | minor_issues | major_issues | unacceptable | not_applicable`) on
A product usefulness, B goal understanding, C question minimality, D actionability, E realism,
F dependency correctness, G verification quality, H evidence interpretation, I user agency,
J adaptation quality, K explanation quality, L external-fact discipline *(hard gate)*, M safety
*(hard gate)*, N language quality, plus P contrastive quality and Q privacy & memory, and an
**overall** verdict O (`excellent | acceptable | needs_revision | incorrect`). No summed score.
Approval requires overall excellent/acceptable, no major/unacceptable rating, hard gates good or n/a,
and every applicable criterion rated. The v0.1 numeric rubric is kept only for reference.

**Log.** Decisions are appended to `data/reviewed/review_events.jsonl` (schema
`schemas/review_event.json`): example id, content hash, reviewer id + snapshot of their roles and
languages, timestamp, action (approve / revise / reject), old and new status, rubric ratings,
overall, issues, notes, acknowledged findings, snapshot path, previous-event hash and own hash. The
chain makes edits, deletions and reordering detectable (`gj review verify-log`). The reviewed
content is preserved in `data/reviewed/snapshots/<hash>.json`.

**Status** (derived, never authored; review log v0.3.0):

| Status | Detail |
|---|---|
| `pending` | `not_reviewed`, `content_changed` (content changed since the last decision) or `awaiting_expert` |
| `approved` | `decided` |
| `needs_revision` | `decided` |
| `rejected` | `decided` |

Rules:

* The latest decision per reviewer counts. With one reviewer, their latest decision on the current
  content hash is final.
* The most conservative decision wins.
* An adjudicator's decision is final.
* The log is append-only: a changed example gets a new decision; old ones are never rewritten.

**Governance mode** (`configs/review.yaml` `governance.mode`, D-026). `solo_owner` (the default
since pipeline 0.4.0): one human owner reviews; the inter-reviewer gates `reviewer_diversity` and
`calibration_agreement` are **N/A** — reported as N/A, never as passed, and never satisfied by
self-agreement. `multi_reviewer`: several independent reviewers; those two gates are blocking. A
config without `governance.mode` (every config before D-026) means `multi_reviewer`. The mode never
changes how decisions resolve, so historical multi-reviewer events keep their meaning in either
mode.

**Qualifications and tiers** (`configs/review.yaml`): reviewers are registered in
`review/reviewers.yaml` and must be human; one owner entry is enough. Approval requires a reviewer
who reads the example's languages (RU; mixed input needs RU+EN). Examples with a non-`allowed`
safety category or a risk tag are `expert_review_required` and need sign-off from `domain_expert`s
covering their expert domains. The owner may hold `domain_expert` only for domains they are
qualified in. Otherwise the item stays `pending` / `awaiting_expert` and is not training-eligible.
No example is ever approved automatically, and an AI review copilot never records a decision, never
counts as a reviewer or an expert, and never changes a rating
([guide §14](docs/HUMAN_REVIEW_GUIDE.md)). A rating that the reviewer changed after seeing findings
or AI critique is recorded with `--independent-rating no`.

**Review and training states** (`review_store.training_eligibility`) are kept apart:

| State | Meaning |
|---|---|
| human-reviewed | at least one human decision on the current content hash |
| expert-reviewed | every required expert domain covered by a human `domain_expert` approval |
| training-eligible | status `approved` (which includes the expert tier) |
| not eligible | `not_reviewed`, `content_changed`, `awaiting_expert`, `needs_revision` or `rejected`, always with that reason |
| training-ready release | a release whose every *applicable* gate passes (§15) |

**Sample.** `gj review sample` builds a deterministic 30-item manifest
(`review/review_manifest_v<ver>.json`, schema `schemas/review_manifest.json`): 40% random (drawn first,
unbiased), 30% highest risk, 20% contrastive, 10% edge; coverage repair (every operation/behaviour,
RU, EN, mixed, contrastive, ≥ 3 expert-tier); 8 calibration items reviewed by everyone first (in
`solo_owner` mode they are ordinary sample items).
A new dataset version keeps the sample in force unless a new one is drawn deliberately.
v0.1.1 keeps the v0.1.0 sample (`configs/review.yaml` `sampling.sample_version`), regenerated from
the frozen v0.1.0 inputs. `gj review sample-status` writes `review/review_sample_status_v<ver>.json`.
For each item it records:

* whether the content changed since sampling, and the revision ids behind the change;
* the known issues that name the example;
* the human status. Automation never sets it.

```
gj review list --manifest           gj review show ID [--show-automated]
gj review template ID --out f.yaml  gj review approve|revise|reject ID --reviewer ME --from f.yaml
gj review export --format md|sheet|json --manifest --out …    gj review apply sheet.yaml --reviewer ME
gj review history ID                gj review stats             gj review verify-log
```

## 15. Splits and releases

* **train / validation:** deterministic split by `scenario_group`, stratified by task type
  (seeded hash ordering, `validation_fraction` 0.15, strata with ≥ 4 examples contribute).
  From v0.1.1, scenario groups are **behavioural scenarios**
  (`data/scenarios/behavioural_scenarios.yaml`: operation | trigger | condition | decision) rather
  than topics. The old topical group is kept as `topic_group`.
* **test:** the evaluation cases (authored separately), frozen into the release.
* **Leakage guard** (layers and limits: [`docs/LEAKAGE_CHECKS.md`](docs/LEAKAGE_CHECKS.md)): the build
  aborts on any hard finding — identical input, character near-duplicate (5-char shingle Jaccard ≥ 0.55),
  lexical paraphrase (TF-IDF cosine ≥ 0.50), shared scenario group, a scenario on the wrong registry
  side, reused seed id, identical decision pattern. Multi-step evaluation cases are checked per step.
  Template and similar-decision-pattern candidates and seed similarity are warnings that need a human
  disposition (release gate). The report groups the layers into lexical, semantic/template and
  scenario families. These checks can show that leakage exists; they cannot show that it does not.
* **Revisions (no silent edits).** A version derived from an earlier release carries a ledger
  `data/revisions/v<ver>.yaml` (schema `schemas/revision_ledger.json`). It has one entry per changed
  example, and each entry records:
  * the defect, the correction and the rationale;
  * the known issues and policies involved;
  * `reviewer_status`, and once a human has decided (`confirmed` or `disputed`), a `review` block with
    the reviewer, timestamp, reviewed content hash, `independent_rating` and notes (schema 0.1.2,
    `gj revisions review`, D-027);
  * computed content hashes, changed paths and snapshots of both versions.

  `gj revisions check` fails on any unrecorded or stale change; `gj split` refuses to build without a
  clean ledger. The release manifest lists `revision_ids` and `previous_content_hash` for revised rows.
* **Review policy:** `require_approved` (only approved content) or `allow_pending` (pending
  *authored* examples allowed, release marked `draft_unreviewed`). Generated candidates enter a
  release only when approved, under either policy. Content that is `needs_revision` or `rejected` is
  always excluded; under `allow_pending`, `pending` authored content of any detail (`not_reviewed`,
  `content_changed`, `awaiting_expert`) is released only as a draft.
* **Training eligibility in the manifest.** Every release manifest (pipeline ≥ 0.4.0) records
  `review_mode` and `training_eligibility`: the eligible count, counts per reason, and every
  pool example that is not training-eligible, with its reason, status, origin, whether it is in the
  release as a draft row, and the missing expert domains for `awaiting_expert`. Nothing is dropped
  silently. Earlier manifests (v0.1.0, v0.1.1) are frozen as built and lack these keys.
* **Release status:** `draft_unreviewed` (pending rows) → `reviewed_not_training_ready` (all rows
  approved but an applicable release gate fails) → `training_ready` (every *applicable* gate in
  [`configs/release_gates.yaml`](configs/release_gates.yaml) passes). Gates, by scope:
  * **always:** strict validation, 100% approval, acknowledged findings, no open medium/high known
    issues, leakage clean and dispositioned, coverage minimums, evaluation readiness, licensing
    resolved;
  * **multi_reviewer only:** ≥ 2 reviewers (`reviewer_diversity`) and calibration agreement
    (`calibration_agreement`). In `solo_owner` mode these are N/A: shown, never counted as passed,
    and never blocking.

  Every gate guards training readiness only; none blocks review work. `gj gates` evaluates them
  live and prints the mode, the state of each gate (PASS / FAIL / N/A) and the applicable count.

## 16. Export formats

`gj export --format sft|preference|eval` writes to `exports/v<ver>/` (derivable, git-ignored).
Training formats are gated: by default (`--review-policy require_approved`) only rows whose exact
content is approved *now* are written, and only if `gj gates` passes. `--allow-draft` writes to
`exports/v<ver>-draft/` with `training_eligible: false` on every record and a `DRAFT_NOT_FOR_TRAINING`
marker (for tooling smoke tests); `--review-policy allow_pending` always implies a draft. The eval
format is not gated.

* **sft**: `{"messages": [system, user, assistant], "metadata": {...}}` — system = navigator prompt,
  user = the request JSON, assistant = the output JSON. Chat templates are applied by the training
  framework, so the data stays base-model-agnostic.
* **preference**: `{"prompt": [system, user], "chosen": [...], "rejected": [...], "metadata": {..., "failure_modes"}}`.
* **eval**: `{"id", "messages": [system, user], "task_type", "dimensions", "checks", ...}`.

Evaluation of a model uses exactly the same prompt (`gjcore/prompting.py`).

## 17. Evaluation

Evaluation v0.2.0 ([`docs/EVALUATION_V0.2_DESIGN.md`](docs/EVALUATION_V0.2_DESIGN.md)) has 63 cases
from independent seeds: 43 atomic, 14 composite (2 steps) and 6 longitudinal (5–9 steps). That is
106 model calls with 658 automated checks. Composite and longitudinal cases are teacher-forced:
every step runs on the canonical state of the earlier steps and is scored on its own. A case passes
only if all its steps pass.

The cases cover the 12 v0.1.0 dimensions plus `state_consistency`, `numeric_consistency` and
`evidence_integrity`. They are authored in `evaluation/builders/v0_2_0/` and rendered by
`gj eval build-cases`. Evaluation v0.1.0 (30 atomic cases) stays frozen and validated.

Metrics (automated, per metric and per dimension; **no overall score by design**):
schema validity, semantic validity, unnecessary question rate, missing critical question rate,
verification status accuracy, verification rigor, route preservation, hallucination rate, web
research decision accuracy, safety policy compliance, language match, memory leak rate, user
agency compliance, constraint compliance, task actionability, decision transparency, scope
adherence, progress integrity, feasibility judgement; from v0.2.0 also state consistency, numeric
consistency, evidence integrity, capability compliance, fact provenance and deadline autonomy.

Human review of model outputs uses a separate rubric
([`evaluation/rubrics/model_output_rubric.yaml`](evaluation/rubrics/model_output_rubric.yaml)) and
a separate sheet (`gj eval review-sheet`); human scores are never merged into automated metrics.

Sanity instruments: the `reference` predictor must pass every check; the `naive` baseline (always
English, fixed questionnaire, verifies everything, never researches, everything "allowed") is
schema-valid on every case and must fail most behavioural checks.

Known weaknesses of eval v0.2.0:

* the same author as the training data;
* 100 reviewed overlaps without a human disposition (11 strong, all set-up or intermediate steps);
* 63 cases, against a gate of 200.

The path to 200–500 independent cases is in
[`docs/EVALUATION_EXPANSION_PLAN.md`](docs/EVALUATION_EXPANSION_PLAN.md). Evaluation-side provenance
(scenario group, behaviour template, seed origin, reviewed overlaps) lives in
`evaluation/leakage/v<ver>.yaml`.

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

## 20. Known limitations (v0.1.1)

* **Authorship and review.** Examples, revisions, validators and evaluation cases were written by an
  AI agent under this spec. The 36 v0.1.1 revisions fix the six high-severity defects and the
  policy-dependent issues, but they are **pending human review**. Of the 34 known issues:
  * 22 are fixed pending review;
  * 11 are open (2 medium);
  * 1 is won't-fix.
* **Policy confirmation.** The policies (POL-A…F) were decided by dataset engineering and still need
  product-owner confirmation.
* **Validator limits.**
  * Dates, weekdays and hour/week/month arithmetic are now checked deterministically; money and
    distances are not.
  * Vagueness and gendered-form checks remain heuristic.
  * Lint cannot judge whether a plan is generic or whether a tone is right. Those are human-review
    criteria.
* Near-duplicate and paraphrase detection is O(n²) and same-language only. Cross-lingual overlaps
  (8 reviewed) are invisible to automation; move to MinHash/LSH and multilingual embeddings at scale.
* Evaluation cases (63 in v0.2.0) are below the 200–500 target and share their author with the
  training data.
* Every scenario group has one example; `memory_extraction` (2) and `progress_update` (3) are thin;
  mixed-language input is 3%.
* Licensing questions in `configs/licensing_status.yaml` are unresolved.
