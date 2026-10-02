# Durable decisions

Architectural and product decisions that every change must respect. Each entry is short and points
to its source; this is not the specification.

* Add an entry when a milestone makes a lasting decision.
* Never delete an entry. Supersede it with a new one that references the old id.
* "Status: confirmed" means decided by the product owner. "Status: adopted" means decided by dataset
  engineering and awaiting owner confirmation.

## Product

**D-001 — The user controls the Journey.** *Superseded by D-021.*
The navigator proposes; the user decides. Major route changes, removing several nodes or a milestone,
and any goal change need the user's confirmation. Completed or verified progress is never silently
discarded.
*Source:* DATASET_SPEC §5–6, POL-C. *Status:* superseded by D-021.

**D-021 — Navigator owns route composition and substantial route changes.**
* The navigator builds the route.
* The user may add a task; the navigator incorporates that task and adapts the route around it.
* The navigator has the final decision on substantial route changes.
* Changing the goal is done only by the user.
* This supersedes D-001's requirement for user confirmation of substantial route changes.
* The existing verified-progress preservation rule remains in force unless progress is explicitly invalidated
  under the existing verification/progress rules.
*Status:* confirmed by product owner 2026-09-28.
*Source:* Product Owner decision 2026-09-28; supersedes D-001.

**D-002 — Goal deadlines change only after confirmation.**
* Task dates may adapt automatically (`auto`).
* Milestone dates may adapt with a stated summary (`adapt_with_summary`).
* Goal dates are `confirm_required` and stay `proposed` until the user confirms.
*Source:* POL-C. *Status:* confirmed by product owner 2026-09-28.

**D-022 — Photo and screenshot evidence can be sufficient proof.**
* A photo or screenshot may fully verify completion when the task criterion is directly and reliably determinable from the submitted image.
* A photo or screenshot may also be one component of a multi-method verification when the image alone is insufficient or ambiguous.
* The model must not claim stronger verification than the actual image evidence supports.
* This supersedes D-003.
*Status:* confirmed by product owner 2026-09-28.
*Source:* Product Owner decision 2026-09-28; supersedes D-003.

**D-003 — A photo or screenshot alone never verifies completion.** Superseded by D-022.
The former rule remains historical for the v0.1.1 contract and is not silently rewritten.
*Source:* DATASET_SPEC §7 (`VP_PHOTO_ONLY`). *Status:* superseded by D-022.

**D-004 — Evidence-class confidence has explicit ceilings and exceptions.**
* `self_report` gives at most *limited* and cannot reach medium alone.
* `user_entered_data` gives at most *limited* alone, but may reach *medium* when every row has a
  checkable reference and the protocol spot-checks those references.
* `image_description` gives at most *limited* alone and is never sufficient by itself, but may reach
  *medium* when combined with another required non-image method.
* Insufficient evidence leads to `needs_more_evidence`, not rejection.

*Source:* POL-B. *Status:* confirmed by product owner 2026-09-28 (choice B).*

**D-005 — Capability roadmap.** Superseded by D-023.
The former roadmap classification remains historical for the v0.1.1 contract.
*Source:* POL-A. *Status:* superseded by D-023.
**D-023 — Product capabilities beyond the MVP are planned roadmap capabilities.**
* Video analysis, proactive reminders, calendar access, API calls, account access and third-party contact are planned.
* They remain unavailable to the current v0.1.1 training contract until the product ships them.
* A future capability becoming available requires a corresponding product capability update and new versioned dataset/prompt work where that capability is used.
* This supersedes D-005's classification of API calls, account access and third-party contact as unsupported.
*Status:* confirmed by product owner 2026-09-28.
*Source:* Product Owner decision 2026-09-28; supersedes D-005.

**D-006 — Levels and achievements follow verified progress, never app activity** (streaks, opens).
*Source:* DATASET_SPEC §6. *Status:* confirmed by product owner 2026-09-28.

**D-007 — The navigator is a goal navigator, not a general assistant.** Off-topic requests get a
brief redirect.
*Source:* DATASET_SPEC §1. *Status:* confirmed by product owner 2026-09-28.

**D-008 — Safety.** No medical, legal or financial prescriptions. High-risk goals get planning
support with a professional referral; restricted goals are declined with a legitimate alternative.
*Source:* DATASET_SPEC §9. *Status:* confirmed by product owner 2026-09-28.

## AI behaviour

**D-009 — Facts keep their provenance.** User-provided, model-inferred, externally verified and
unknown facts are distinct. An inferred fact is never presented as the user's word or as verified.
Current external facts come only from provided research.
*Source:* POL-E, DATASET_SPEC §8. *Status:* confirmed by product owner 2026-09-28.

**D-010 — Russian voice and stored user gender.** Superseded by D-024.
The former rule remains historical for the v0.1.1 contract and is not silently rewritten.
*Source:* POL-D. *Status:* superseded by D-024.

**D-024 — User gender comes from the user's profile and may control user-facing grammatical gender.**
* When the user's gender is explicitly present in the user's profile, the navigator may use gender-marked
  grammatical forms when addressing the user.
* Gender must not be inferred from the user's name, language, behaviour, wording or other indirect signals.
* User information stored in memory may include the user's gender when that value comes from the profile.
* The navigator's own grammatical self-reference remains separately governed; this decision changes
  user address and storage of the profile gender, not the navigator's own self-reference.
* This supersedes D-010's prohibition on gender-marked user address and gender-free storage of the profile gender.
*Status:* confirmed by product owner 2026-09-28.
*Source:* Product Owner decision 2026-09-28; supersedes D-010.

**D-011 — Train future-correct behaviour, with representable capabilities only.**
*Source:* POL-F. *Status:* confirmed by product owner 2026-09-28.*

**D-012 — The model and provider stay replaceable.**
* The base model is unset until chosen and is recorded in `configs/versions.yaml`, never
  hard-coded.
* Teacher providers sit behind one interface: Anthropic SDK, any OpenAI-compatible endpoint, or
  replay.
* SFT exports are chat-template-agnostic.
* Evaluation prompts the model exactly as the SFT export does.

*Source:* ARCHITECTURE §6. *Status:* adopted.

## Data governance

**D-013 — User data never enters training automatically.** No real user data is in the dataset.
Any future use of product data needs explicit consent, anonymisation, a documented source and human
review.
*Source:* DATA_SOURCES.md. *Status:* confirmed by product owner 2026-09-28.*

**D-014 — Training-ready data requires approval gates.**
* Only content a qualified human approved, by exact content hash, reaches a training file.
* The release must also pass every gate in `configs/release_gates.yaml`.
* Automation never approves.
* Gates are not loosened to produce a passing release.

*Source:* DATASET_SPEC §14–16. *Status:* confirmed by product owner 2026-09-28.* *Refined by D-026:*
"every gate" means every gate applicable in the governance mode in force.

**D-015 — Releases are immutable, and every change is traced.** A changed example gets a new
`dataset_version` and an entry in the revision ledger (`data/revisions/v<ver>.yaml`): defect,
correction, rationale and snapshots. `gj split` refuses an incomplete ledger. There are no silent
edits.
*Source:* DATASET_SPEC §15. *Status:* confirmed by product owner 2026-09-28.*

**D-016 — Records are validated against the rules of their own `schema_version`.** Old data is never
re-judged by newer rules.
*Source:* DATASET_SPEC §2. *Status:* confirmed by product owner 2026-09-28.*

**D-025 — Review rubric 0.2.1 clarifies the safety anchor for restricted goals.** For a `restricted`
goal, the refusal must stop planning, optimising or advancing the prohibited activity. A lawful or safe
alternative, a safer reframing or a next step for that alternative may still be offered, and is not
unsafe continuation unless it materially facilitates the prohibited activity. `proceed_with_journey:
false` refers to the original restricted goal, not to a separately chosen safe goal. Criteria, hard
gates and decision rules are unchanged; rubric 0.2.0 stays in place for events stamped with it.
*Source:* `evaluation/rubrics/dataset_review_rubric_v0.2.1.yaml`, DATASET_SPEC §9; raised by the
calibration disagreement on rv-0.1.0-02. *Status:* directed by product owner 2026-09-29.*

**D-026 — Solo-owner-first review governance with optional expert escalation.** This replaces
multi-reviewer-first governance.

* **Solo-owner mode.** `configs/review.yaml` `governance.mode: solo_owner` is the default. One
  human owner is a complete review workflow: there is no second reviewer, adjudicator or pairwise
  calibration, and the owner's latest valid decision on a content hash is final.
* **Inter-reviewer gates.** `reviewer_diversity` and `calibration_agreement` have
  `scope: multi_reviewer`. In solo mode they are reported as N/A, never as passed, and never
  satisfied by self-agreement. In `multi_reviewer` mode they stay blocking. A config without a mode
  means `multi_reviewer`.
* **What does not change.** The rubric (A–Q, hard gates L and M), content-hash binding, write-once
  snapshots, the append-only chained log, invalidation on revision, the independence of ratings from
  automated findings, and the expert tier. Every other gate stays blocking in every mode.
* **Expert escalation.** An item needing a domain the owner is not qualified in stays `pending` /
  `awaiting_expert`. It is not training-eligible, and it is listed with its reason and missing
  domains in the release manifest's `training_eligibility`.
* **AI review copilot.** AI may explain, challenge and recalculate. It never records a decision,
  never counts as a reviewer or an expert, and never changes a rating. The human rates first. A
  rating changed after findings or AI critique is recorded with `independent_rating: false`.
  Uncertainty goes into notes, with no new workflow state.

*Why:* the project has one product owner. The pairwise gates could be satisfied only by a second
person the project does not have, or by a fabricated identity, which the review rules forbid. Solo
mode keeps every quality check that one careful human can honestly perform. It is explicit about
what one person cannot provide: independent agreement, and expertise they lack. That gap stays
visible as N/A gates and `awaiting_expert` items rather than disappearing.

*History:* resolution is unchanged, so historical multi-reviewer events (po-reviewer and
po-reviewer-two, calibration round 0.1.0) keep their meaning. v0.1.1 artefacts are untouched, and
`multi_reviewer` mode reproduces the earlier gate semantics.
*Source:* `configs/review.yaml`, `configs/release_gates.yaml` (1.1), DATASET_SPEC §14–15,
HUMAN_REVIEW_GUIDE §14–17; pipeline 0.4.0. *Status:* directed by product owner 2026-09-29.*

**D-027 — Decisions on revision-ledger entries carry their reviewer, notes and independence.** A
ledger entry's `reviewer_status` (`confirmed` or `disputed`) is recorded with `gj revisions review`,
which writes a `review` block: the registered human reviewer, a timestamp, the content hash the
decision was made on, `independent_rating` and notes. `gj revisions check` fails if the entry's
content moves away from the reviewed hash or the reviewer is not a registered human. A ledger decision
judges the correction; it is not a rubric review of the example, and it changes no example status or
known issue. The review log (`data/reviewed/review_events.jsonl`) is unchanged.
*Source:* `schemas/revision_ledger.json` (schema 0.1.2), `generation/pipelines/revisions.py`
(pipeline 0.4.1). *Status:* directed by product owner 2026-09-30.*

## Evaluation

**D-017 — Evaluation is independent of training.**
* Separate seeds.
* Eval-side behavioural scenarios whose decision patterns differ from every training pattern.
* No shared scenario groups.
* Reviewed overlaps need human dispositions.
* No report claims "no leakage".

*Source:* docs/EVALUATION_V0.2_DESIGN.md, docs/LEAKAGE_CHECKS.md. *Status:* confirmed by product owner 2026-09-28.*

**D-018 — Metrics are reported per metric and per dimension, with no overall score.** Multi-step
cases are scored per teacher-forced step, and a case passes only if all its steps pass.
*Source:* DATASET_SPEC §17. *Status:* confirmed by product owner 2026-09-28.*

**D-019 — Evaluation cases are authored in `evaluation/builders/` and rendered to YAML.** The
generated YAML is never edited by hand.
*Source:* EVALUATION_V0.2_DESIGN §6. *Status:* confirmed by product owner 2026-09-28.*

**D-028 — Evaluation reference outputs are reviewed under solo-owner governance, and the review is stored
in the case.** This decision is specific to the human review of evaluation reference outputs
(Milestone 1.7, task 7). It applies D-026 to them and changes nothing else in D-026: the review of
training examples, the review log and the release gates are unaffected.
* **Who decides.** In `solo_owner` mode one registered human owner completes the review of a reference
  output; no second reviewer is required. The owner judges first. The AI copilot may challenge
  afterwards, but it never records a decision and never counts as a reviewer or an expert. A decision
  changed after automated findings or AI critique is recorded with `independent_rating: false`.
* **Expert tier unchanged.** A case in the D-026 expert tier needs a registered `domain_expert` for its
  domains; the owner's review alone does not complete it.
* **Multi-reviewer mode.** Reference review is defined for `solo_owner` only. In `multi_reviewer` mode
  the command refuses to record, and one recorded review never stands for reviewer agreement.
* **What a review means.** Automated checks still decide what they measure. The review is the human
  quality judgement of whether a reference is an acceptable answer. A reviewed reference is not the
  only correct answer: a model that disagrees with it is a finding for a human.
* **Storage.** The review lives inside the case, in a `reference_review` block (schema 0.1.3), not in a
  separate ledger. The block holds `metadata_schema_version` and append-only sessions:
  * each session has `reviewer_id`, `timestamp`, `governance_mode` and `independent_rating`;
  * it has one decision per reference output (the case's own, or one per step): `content_hash`,
    `action` (`approve`/`revise`/`reject`), `overall` (`excellent`/`acceptable`/`needs_revision`/
    `incorrect`), `issues` and `notes`;
  * there are no criterion-level ratings.

  Decisions are recorded only with `gj eval review-reference`. `gj eval build-cases` carries the block
  over when it regenerates the cases, and refuses to render if a recorded review would be dropped.
* **Status.** `reference_status` is derived. It is `human_reviewed` only when every reference output
  of the case has a decision on its current content hash. A partial review, or a review of content
  that has since changed, leaves it `draft_unreviewed`.
* **Versions.** Review metadata is not evaluation content, so it changes neither `evaluation_version`
  nor `dataset_version`. A release keeps the review state it was built with, and rebuilding it uses the
  reviews as they stood then (as for the review status of training rows). The case's `schema_version`
  stays its model input/output contract; the block names the schema version that defines it.

*Source:* `schemas/eval_case.json` (schema 0.1.3), `evaluation/reference_review.py`,
`evaluation/builders/build.py` (pipeline 0.4.3). *Status:* directed by product owner 2026-10-01.*
*Refined by D-029:* the owner's review of an expert-tier reference is recorded, and the case stays
`awaiting_expert` until a registered `domain_expert` covers its domains.

**D-029 — An owner's review of an expert-tier evaluation reference is recorded and awaits the
expert.** This refines the expert-tier rule of D-028; nothing else in D-028 or D-026 changes.
* **Recording allowed.** In `solo_owner` mode the owner may record decisions on the reference outputs
  of an expert-tier case (D-026 tiers), and `gj eval review-reference` no longer refuses.
* **No expert qualification is claimed or created.** Each session records the reviewer's registry
  `reviewer_roles` and `reviewer_expert_domains` at recording time. Only a session whose reviewer had
  the `domain_expert` role covers the expert domains it lists. A session recorded without these fields
  covers no expert domain.
* **Status.** When every reference output has a human decision but the required expert domains are not
  covered on the current content, `reference_status` is `awaiting_expert`. It becomes `human_reviewed`
  only when registered `domain_expert` decisions on the current content cover every required domain
  for every reference output. An expert's decision after the owner's is a second reviewer's
  decision, not a redecision. Evaluation cases are never training data, so this is a review state, not
  training eligibility.

*Source:* `schemas/eval_case.json` (schema 0.1.3: the `awaiting_expert` status and the session
fields, an additive change to the unreleased version), `evaluation/reference_review.py` (pipeline
0.4.3). *Status:* directed by product owner 2026-10-02.*

## Engineering process

**D-020 — The repository is the durable project state.** State lives in `docs/PROJECT_STATE.md`,
`ACTIVE_MILESTONE.md`, `DECISIONS.md` and `ROADMAP.md`, not in chat history. One milestone is handled
per primary session.
*Source:* docs/CONTEXT_MANAGEMENT.md. *Status:* confirmed by product owner 2026-09-28.*
