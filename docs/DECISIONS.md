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

*Source:* DATASET_SPEC §14–16. *Status:* confirmed by product owner 2026-09-28.*

**D-015 — Releases are immutable, and every change is traced.** A changed example gets a new
`dataset_version` and an entry in the revision ledger (`data/revisions/v<ver>.yaml`): defect,
correction, rationale and snapshots. `gj split` refuses an incomplete ledger. There are no silent
edits.
*Source:* DATASET_SPEC §15. *Status:* confirmed by product owner 2026-09-28.*

**D-016 — Records are validated against the rules of their own `schema_version`.** Old data is never
re-judged by newer rules.
*Source:* DATASET_SPEC §2. *Status:* adopted.

## Evaluation

**D-017 — Evaluation is independent of training.**
* Separate seeds.
* Eval-side behavioural scenarios whose decision patterns differ from every training pattern.
* No shared scenario groups.
* Reviewed overlaps need human dispositions.
* No report claims "no leakage".

*Source:* docs/EVALUATION_V0.2_DESIGN.md, docs/LEAKAGE_CHECKS.md. *Status:* adopted.

**D-018 — Metrics are reported per metric and per dimension, with no overall score.** Multi-step
cases are scored per teacher-forced step, and a case passes only if all its steps pass.
*Source:* DATASET_SPEC §17. *Status:* adopted.

**D-019 — Evaluation cases are authored in `evaluation/builders/` and rendered to YAML.** The
generated YAML is never edited by hand.
*Source:* EVALUATION_V0.2_DESIGN §6. *Status:* adopted.

## Engineering process

**D-020 — The repository is the durable project state.** State lives in `docs/PROJECT_STATE.md`,
`ACTIVE_MILESTONE.md`, `DECISIONS.md` and `ROADMAP.md`, not in chat history. One milestone is handled
per primary session.
*Source:* docs/CONTEXT_MANAGEMENT.md. *Status:* adopted.
