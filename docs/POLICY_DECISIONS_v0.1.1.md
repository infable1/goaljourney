# Policy decisions — dataset v0.1.1

*Milestone 1.6 · 2026-09-27 · applies to dataset v0.1.1, schema v0.1.1, evaluation v0.2.0*

The Milestone 1.5 audit left four open policy questions, and about 10 examples could not be fixed
until they were answered. This document settles them. It also records two related rules, fact
provenance (E) and the product principle (F).

For each decision the document gives the rule, the structured representation in the schemas, the
validator codes that enforce it, and the examples it changed.

**Status.** These decisions were made by the dataset engineering team (Milestone 1.6). They should
be confirmed by the product owner. Changing any of them means a new dataset version. Records are
checked against the rules of their own `schema_version`, so v0.1.0 data stays reproducible and is
never re-judged by v0.1.1 rules.

| ID | Decision | Machine-readable source | Enforced by |
|---|---|---|---|
| POL-A | Product capabilities: available / planned / unsupported | `configs/product_capabilities.yaml` | `VP_METHOD_UNAVAILABLE`, `EVIDENCE_SOURCE_UNAVAILABLE`, `CAPABILITY_PROMISE` |
| POL-B | Confidence semantics for evidence classes | `configs/evidence_policy.yaml` | `VP_SELF_REPORT_CEILING`, `VP_CEILING_ABOVE_EVIDENCE`, `VR_CONFIDENCE_ABOVE_EVIDENCE`, `VR_CONTRADICTION_VERIFIED` |
| POL-C | Deadline autonomy: task / milestone / goal | `schemas/route_adaptation.json`, `schemas/navigator_response.json` | `RA_DEADLINE_*`, `NAV_RESCHEDULE_*`, `GC_DEADLINE_NO_CONFIRM`, `J_GOAL_DEADLINE_CHANGED` |
| POL-D | Russian voice: self-reference, addressing the user, level titles | this document | `RU_GENDERED_SELF_REFERENCE`, `RU_GENDERED_USER_ADDRESS`, `RU_GENDERED_MEMORY` |
| POL-E | Fact provenance: user_provided / model_inferred / externally_verified / unknown | `schemas/common.json#/$defs/fact` | `FACT_NOT_GROUNDED`, `FACT_BAD_REF`, `FACT_VERIFIED_WITHOUT_SOURCE` |
| POL-F | Product principle: train future-correct behaviour, only with representable capabilities | this document | review rubric (G, L) + POL-A validators |

---

## POL-A — Product capabilities

**Decision.** The training data may only ask for, rely on or promise capabilities that the MVP
actually implements. A capability that the schemas can represent but the MVP does not implement is
*planned*: no training output may require it. A capability that will not be built is *unsupported*:
no output may promise it.

| Status | Capability | What the model actually receives |
|---|---|---|
| **available** | `CAP-TEXT-REPORT` free-text reports, structured self-report logs, result tables typed by the user | the text |
| available | `CAP-CHAT-QA` questions, test items or problems the navigator puts **in its own reply**; the user answers in the next turn | the answers |
| available | `CAP-FILE-TEXT` documents, code, spreadsheets, CSV/JSON exports | verbatim extracted text (`file_parser`) |
| available | `CAP-IMAGE-DESCRIPTION` photos and screenshots | an automatic description plus the user's caption, never the pixels (`vision_model`) |
| available | `CAP-AUDIO-TRANSCRIPT` audio recordings | transcript + duration (`transcription`) |
| available | `CAP-URL-FETCH` a public URL the user submits | one HTTP GET, no login, no forms, no scripts; a text extract (`system_fetch`) |
| available | `CAP-WEB-RESEARCH` research the navigator asks for | results with sources in a later request (`research_results`) |
| **planned** | `CAP-VIDEO-ANALYSIS` video upload and analysis | — |
| planned | `CAP-TRACKER-SYNC` live fitness-tracker/health-app sync (a manually exported file is `CAP-FILE-TEXT`, available) | — |
| planned | `CAP-PROACTIVE-MESSAGES` reminders, scheduled check-ins, "I'll send it in my next message" | — |
| planned | `CAP-CALENDAR` reading/writing the user's calendar | — |
| **unsupported** | `CAP-API-CALLS` calling the user's services (POST/PUT/DELETE, authenticated requests) | — |
| unsupported | `CAP-ACCOUNT-ACCESS` logging into user accounts | — |
| unsupported | `CAP-THIRD-PARTY-CONTACT` contacting people or organisations on the user's behalf | — |
| unsupported | `CAP-LOCATION-BIOMETRICS` GPS tracking, biometrics, background monitoring | — |

Consequences:

* Verification methods map to capabilities (`methods:` in the config). `video` needs a planned
  capability, so it cannot appear in a v0.1.1 protocol (`VP_METHOD_UNAVAILABLE`), and input
  evidence cannot be a video (`EVIDENCE_SOURCE_UNAVAILABLE`).
* The navigator cannot send a message on its own. Whatever the user needs now (e.g. control problems)
  goes into the current reply. Promises of reminders or follow-up messages are errors (`CAPABILITY_PROMISE`).
* A URL is fetched with one GET. An API endpoint can be read with GET, but the navigator can never
  exercise POST/DELETE; the user pastes that output.
* Media never verify alone (unchanged). The model reasons about *descriptions* of media, so it must
  not claim to have seen details the description does not contain.

**Changed by POL-A** (5 ledger entries): `gj-vprot-001` (video → a scramble issued in the reply,
audio narration and method questions), `gj-vprot-003` (app calling endpoints → one GET fetch, a
pasted command session and a repository review), `gj-vres-002` (control problems promised "right
after this message" → included in the reply); the rejected outputs of `gj-vres-004` and `gj-vres-006`
demand video and are now also tagged `unavailable_capability`. `gj-task-002` (audio transcription)
and `gj-vprot-004` (fetching the links from a table) use available capabilities; they changed under
POL-B only.

## POL-B — Confidence for user-entered evidence

**Decision.** Confidence follows the *class* of evidence, not how detailed or confident the
submission sounds. User-entered data is the user's word.

| Class | Examples | Ceiling alone | Can reach medium when |
|---|---|---|---|
| `self_report` | free text, self-report logs, answers about the user's own activity | **limited** | never alone |
| `user_entered_data` | tables, interview cards, measurements, pasted confirmations | **limited** | every row carries a checkable reference (`references_required: true`) **and** the protocol spot-checks references (URL fetch) |
| `image_description` | photo/screenshot descriptions | **limited**, never sufficient alone | combined with another required non-image method (a physical result shown **and** explained) |
| `inspectable_artifact` | the result itself: text, code, document, file, recording transcript, answers to a test the navigator issued | **high** (for criteria visible in the artifact) | — |
| `externally_verifiable` | a public page or platform verification link the system fetched itself | **high** | — |
| *multiple independent sources* | e.g. artifact + in-chat test, URL + repository | the highest class present | agreement between independent sources is what justifies high; two self-reports are still limited |

Rules:

1. A protocol's `confidence_ceiling` must not exceed what its *required* methods can support
   (`VP_CEILING_ABOVE_EVIDENCE`). Methods have a default class (`configs/evidence_policy.yaml`); a
   method may declare `evidence_class` when the default is wrong. For example, a structured result
   that *is* the deliverable (a route draft) is an inspectable artifact.
2. If every required method is `self_report` or `user_entered_data` without references, then
   `self_report_only: true` and `confidence_ceiling: limited` (`VP_SELF_REPORT_CEILING`, extended to
   user-entered data), and `objective_verifiability` cannot be high or medium.
3. A verification result's `confidence` must not exceed the class of the evidence actually received
   (`VR_CONFIDENCE_ABOVE_EVIDENCE`). `limited` ⇔ `evidence_basis: self_report` is unchanged.
4. **Contradictions are recorded, not ignored.** When a statement and an artifact disagree (the user
   says 10 km, the export shows 6.2 km), the result lists them in `contradictions[]` and cannot be
   `verified` (`VR_CONTRADICTION_VERIFIED`). Instructions embedded in evidence ("mark this as
   verified") are content, not commands.
5. Conservative default: if the class is unclear, use the lower one.

**Changed by POL-B** (16 ledger entries): 12 examples whose protocols rated user-entered data
medium/high (`gj-jour-001`, `gj-jour-002`, `gj-jour-003`, `gj-task-001`, `gj-task-002`, `gj-task-003`,
`gj-task-004`, `gj-task-005`, `gj-vprot-004`, `gj-vprot-006`, `gj-vres-007`, `gj-vretry-004`) — each
protocol is lowered to *limited*, given checkable references, or declared an inspectable artifact with
a reason; the two capability rewrites `gj-vprot-001` and `gj-vprot-003` (their new ceilings follow the
evidence classes); and the rejected photo-only protocols of `gj-jour-004` and `gj-vprot-007`, now also
tagged `overconfident_verification`. Details are in the revision ledger.

## POL-C — Deadline autonomy

**Decision.**

| Level | The navigator may | Representation |
|---|---|---|
| **Task (node) deadline** | adapt automatically when justified | `autonomy: auto` |
| **Milestone deadline** | adapt or propose, always with an explicit decision summary that names the milestone or the new date | `autonomy: adapt_with_summary` |
| **Goal deadline** | only *propose*; the user's target date changes only after the user confirms | `autonomy: confirm_required`, `state: proposed`, `requires_user_confirmation: true` |

Exact structured representation (`route_adaptation.modified_deadlines[]`):

```json
{"target": "node",      "target_id": "n5",  "from": "2026-10-02", "to": "2026-10-06", "reason": "…", "autonomy": "auto",               "state": "applied"}
{"target": "milestone", "target_id": "m1",  "from": "2026-11-01", "to": "2026-11-23", "reason": "…", "autonomy": "adapt_with_summary", "state": "applied"}
{"target": "goal",      "target_id": "g-x", "from": "2027-03-01", "to": "2027-06-01", "reason": "…", "autonomy": "confirm_required",   "state": "proposed"}
```

Rules (lint, v0.1.1):

* `autonomy` and `state` are required on every deadline change (`RA_DEADLINE_AUTONOMY_MISSING`), and
  `autonomy` must match the target level (`RA_DEADLINE_AUTONOMY_WRONG`).
* If `requires_user_confirmation` is true, every deadline change is `proposed`, because nothing is
  applied before the user answers. If it is false, every change is `applied` and there is no goal
  change (`RA_DEADLINE_STATE_INCONSISTENT`, `RA_GOAL_DEADLINE_NO_CONFIRM`).
* An applied milestone change must be named in `decision_summary` by milestone id, title or new
  date (`RA_MILESTONE_NO_SUMMARY`).
* A task `due_date` changed in `modified_nodes` must also be declared in `modified_deadlines`
  (`RA_UNDECLARED_DEADLINE_CHANGE`).
* Navigator reschedules declare `target_type` (node / milestone / goal) and `new_date`
  (`NAV_RESCHEDULE_UNDECLARED`). A goal-level reschedule requires confirmation (`NAV_GOAL_DEADLINE_NO_CONFIRM`).
* `goal_change` that alters the goal deadline requires confirmation (`GC_DEADLINE_NO_CONFIRM`).
  `journey_generation` never changes the deadline (`J_GOAL_DEADLINE_CHANGED`, now an error).
* Every new date must be feasible: the hours of unfinished work before it must fit the pace until
  then (`MILESTONE_DATE_INFEASIBLE`, see *Arithmetic* below).

**Changed by POL-C** (9 ledger entries): `gj-route-002`, `gj-route-005`, `gj-time-001`, `gj-time-002`,
`gj-time-003`, `gj-time-004` (autonomy/state annotations; `gj-time-004` also moved its task due date
into `modified_deadlines`), `gj-nav-006` (reschedule targets and dates), `gj-route-004` (net saving
stated from the plan, session order within the offer window) and the rejected output of `gj-jour-005`
(it dropped the goal deadline, which `J_GOAL_DEADLINE_CHANGED` now treats as an error).

### Arithmetic and calendar consistency (supports POL-C)

Plans that report numbers must be internally consistent; the numbers are recomputed, never trusted.

* **Calendar:** a weekday stated next to a date is checked against the real calendar relative to
  `today` (`DATE_WEEKDAY_MISMATCH`). Weekday labels written by an LLM are never trusted.
* **Workload** (`route_adaptation.workload`, required for time changes): hours remaining before and
  after the change are recomputed from node estimates. Weeks needed are recomputed from the pace,
  including temporary `pace_phases`, and weeks available from `today` to the horizon date
  (`ARITH_*`). Unestimated nodes must be listed (`unestimated_node_ids`) instead of silently ignored.
* **Stated quantities:** every number of hours or weeks in the message or decision summary must be
  derivable from the plan (`ARITH_TEXT_UNDERIVABLE`), which catches statements like "about 140 hours"
  when the tasks add up to 115.
* **Deadline feasibility:** milestone dates in journeys and adaptations must leave enough hours for
  the unfinished work assigned to them (`J_MILESTONE_OVERBOOKED`, `MILESTONE_DATE_INFEASIBLE`).
  Generated tasks must fit the time until their milestone (`T_OVER_CAPACITY`).

## POL-D — Language and titles (Russian voice)

The three cases are separate:

1. **Assistant self-reference.** The assistant has no grammatical gender. It uses the present or future
   tense («предлагаю», «перенесу», «проверю»), impersonal and passive constructions
   («подготовка разбита на 4 задачи», «задача засчитана»), or it describes the plan instead of the actor.
   It never uses past-tense singular or short adjectives about itself («разбил», «проверил», «рад»,
   «готов»), and never slash forms («рад(а)»). These neutral options are ordinary Russian, not
   artificial constructions (`RU_GENDERED_SELF_REFERENCE`).
2. **Addressing the user.** Formal «вы» with plural agreement, which is neutral: «вы готовы»,
   «вы уверены», «вы сами». Never forms that encode gender («вы один/одна», «вы готов»), and never
   gender inferred from the user's own words or name. When a user writes «я прочитал», the assistant
   still writes neutrally («вы прочитали») (`RU_GENDERED_USER_ADDRESS`). Stored memory about the
   user is also the assistant's language and is written neutrally («выходные свободны»,
   «работает сменами»), not «свободен» (`RU_GENDERED_MEMORY`).
3. **Goal-specific level and achievement titles.** These are badge names, not forms of address.
   * They may use the natural dictionary form of a role noun when the role is the natural title
     («Тестировщик-практикант», «Домашний повар», «Junior QA-инженер»).
   * Prefer a stage, skill or result when that is equally natural («Базовые техники освоены»,
     «Первый ужин для друзей»).
   * Do not force feminitives, slash forms or unnatural constructions.
   * A title is shown as a label («Открыт уровень «Домашний повар»»). It is never used to address the
     user with gendered agreement («Теперь вы уверенный нарезчик!» is wrong).
   * Titles are not linted as errors; the audit lists them at info level.

English: singular *they* for people whose pronouns are unknown, and no gendered pronouns for the user.

**Changed by POL-D:** `gj-task-004`, `gj-clar-007` (defects), input memory in `gj-mem-002` and
`gj-lang-001`, and rejected outputs in `gj-route-002`/`gj-time-003` (untagged extra defects).
The `gj-jour-004` titles are accepted under rule 3, and its achievement `a1` was renamed because it
unlocked on a task that is not a dish.

## POL-E — Fact provenance

**Decision.** A factual claim about the user or the world that a decision depends on carries its
provenance. Purely conversational text does not.

```json
"facts_used": [
  {"value": "Ниша канала — бюджетные путешествия с детьми", "source_type": "user_provided",      "source_ref": "goal_memory:gm1"},
  {"value": "Около 10 км в неделю сейчас",                  "source_type": "model_inferred",     "source_ref": "conversation[0]"},
  {"value": "Площадка закрыта до весны 2027 года",          "source_type": "externally_verified", "source_ref": "research:rr1"},
  {"value": "Лимит времени забега",                         "source_type": "unknown"}
]
```

| source_type | Meaning | Rule |
|---|---|---|
| `user_provided` | the user said it or it is in the user's stored context | must be grounded in the referenced input (`FACT_NOT_GROUNDED`, `FACT_BAD_REF`) |
| `model_inferred` | derived by the navigator (arithmetic, interpretation) | must be presented as an estimate or inference in the text, never as the user's statement |
| `externally_verified` | from provided research results or system-fetched evidence | must reference `research:<id>` or fetched `evidence:<id>` (`FACT_VERIFIED_WITHOUT_SOURCE`) |
| `unknown` | needed but not known | triggers a question or research, never an assumption stated as fact |

`facts_used` is optional on goal clarification, feasibility, journey, route adaptation, navigator,
goal change and daily plan outputs. It should be used whenever the answer states something specific
about the user. Existing provenance fields map onto the same vocabulary:

* memory `source`: `user_stated` → user_provided, `inferred` → model_inferred, `verified` → externally_verified
* goal assumption `basis`: `user_stated` → user_provided, `inferred_from_context` → model_inferred, `default_until_confirmed` → unknown
* external claims: `verified_with_source` → externally_verified, `needs_verification` → unknown, `general_knowledge` → model_inferred
* evidence `description_source`: `user_caption` and `file_parser` carry user-provided content; `vision_model` and `transcription` are machine descriptions of user-provided media (model_inferred); `system_fetch` is externally verifiable

**Changed by POL-E** (11 ledger entries): `gj-nav-001` (the invented niche is now a stored goal
decision in the input, cited as a `user_provided` fact) and `gj-nav-003` («как и было» named a session
length the input never gave). The defect fixes `gj-clar-007`, `gj-mem-002`, `gj-nav-006`,
`gj-route-004`, `gj-route-005`, `gj-time-001`, `gj-time-002`, `gj-time-003` and `gj-time-004` now
declare the facts their answers rely on in `facts_used`.

Three ledger entries are not tied to a policy: `gj-clar-001` (a missed critical question in a
rejected output is now tagged), `gj-nav-008` (a 60–90-word greeting was said to count as a 100-word
text) and `gj-mem-003` (`total_minutes` did not match the planned minutes).

## POL-F — Product principle

> **Optimise the training examples for what we want the future GoalJourney model to do correctly —
> not for what an LLM can do today. But never train the model to output capabilities the product
> architecture cannot represent or has not implemented.**

In practice:

* **Behaviour is idealised.** Examples show exact arithmetic, correct dates, conservative confidence,
  one good question instead of five, and honest limits, even where today's small models would
  struggle. Validators, not the model, guarantee that the numbers are right.
* **Capabilities are not idealised.** If the ideal verification needs something the product cannot
  do (watching a video, calling an API, sending a reminder), the example shows the best behaviour with
  *available* capabilities and states the resulting limit (e.g. lower confidence). It does not
  pretend. When a capability ships, examples that use it are added in a new dataset version; old
  examples are not silently rewritten.
* **Representation before behaviour.** A behaviour is trained only once the schemas can represent it
  (e.g. provenance, deadline autonomy, contradictions). Unrepresentable nuance goes into human-review
  criteria, not into free text the app cannot act on.
