# Product Owner Decision Checklist — D-001…D-020

*Prepared 2026-09-28, ahead of Milestone 1.7 (Human Review Round 1). Source: `docs/DECISIONS.md`,
`docs/POLICY_DECISIONS_v0.1.1.md`, `DATASET_SPEC.md`, `docs/ARCHITECTURE.md`, `README.md`,
`docs/ROADMAP.md`, `docs/HUMAN_REVIEW_GUIDE.md`.*

All 20 decisions in `docs/DECISIONS.md` are currently `Status: adopted` — decided by dataset
engineering, not yet confirmed by the product owner. This document does not change any status. It
exists so the product owner can work through each decision and record one of: **confirmed / revise
/ reject / needs discussion**. Nothing here is a recommendation; the status column is left for the
owner to fill in.

Recording the outcome is a repository change: superseding or confirming a `D-NNN` entry belongs in
`docs/DECISIONS.md` itself (never delete an entry — see `.claude/rules/product.md`), not in this
checklist. This file is the discussion aid, not the record.

---

## A. Product behaviour (D-001, D-002, D-006, D-007, D-008)

### D-001 — The user controls the Journey
- **Current decision:** the navigator proposes; the user decides. Major route changes (removing
  several nodes or a milestone) and any goal change need the user's confirmation. Completed or
  verified progress is never silently discarded.
- **Why it matters:** this is the top-level trust contract with the user; it shapes every other
  autonomy rule (D-002) and every adaptation example in the dataset.
- **If confirmed:** no change — training data continues to require confirmation before large route
  edits, and to preserve verified progress across adaptations.
- **Trade-off:** more confirmation prompts can feel slower than a fully autonomous planner.
- **Unresolved dependency:** none identified; DATASET_SPEC §5–6 and POL-C already operationalise it.
- **PO outcome:** **reject**. Superseded by confirmed D-021: the navigator owns route composition and substantial route changes; the user may add tasks, the navigator adapts the route and has final route decision; goal changes remain user-only.
- **Implementation note:** v0.1.1's existing schema/validator contract is not rewritten in place; D-021 requires a new versioned contract/revision work.
- **Recommended status:** ☐ confirmed ☑ reject ☐ revise ☐ needs discussion

### D-002 — Goal deadlines change only after confirmation
- **PO outcome:** **accept** → confirmed by product owner 2026-09-28.
- **Confirmed rule:** task deadline may be adapted automatically; milestone deadline adaptation requires a summary; goal deadline change requires confirmation.
- **Recommended status:** ☑ confirmed ☐ revise ☐ reject ☐ needs discussion

### D-006 — Levels and achievements follow verified progress, never app activity
- **PO outcome:** **accept** → confirmed by product owner 2026-09-28.
- **Recommended status:** ☑ confirmed ☐ revise ☐ reject ☐ needs discussion

### D-007 — The navigator is a goal navigator, not a general assistant
- **PO outcome:** **accept** → confirmed by product owner 2026-09-28.
- **Recommended status:** ☑ confirmed ☐ revise ☐ reject ☐ needs discussion

### D-008 — Safety
- **PO outcome:** **accept** → confirmed by product owner 2026-09-28.
- **Recommended status:** ☑ confirmed ☐ revise ☐ reject ☐ needs discussion

## B. AI behaviour (D-009, D-010, D-011)

### D-009 — Facts keep their provenance
- **PO outcome:** **accept** → confirmed by product owner 2026-09-28.
- **Recommended status:** ☑ confirmed ☐ revise ☐ reject ☐ needs discussion

### D-010 — Russian voice is gender-neutral
- **PO outcome:** **revise**, superseded by confirmed **D-024**.
- **New product rule:** user gender comes from the explicit user profile; the navigator may use gender-marked forms when addressing the user and may store that profile gender. Gender is not inferred from indirect signals.
- **Implementation note:** v0.1.1 keeps its existing versioned contract; D-024 requires versioned schema, memory and prompt work before it governs a new release.
- **Recommended status:** ☐ confirmed ☑ revise ☐ reject ☐ needs discussion

### D-011 — Train future-correct behaviour, with representable capabilities only
- **Current decision:** examples show idealised behaviour (exact arithmetic, correct dates,
  conservative confidence) but never a capability the product doesn't actually implement (POL-F).
- **Why it matters:** balances two failure modes — training on today's flawed behaviour, or
  training on capabilities the product can't deliver, which would make the model unreliable in
  production.
- **If confirmed:** representation-before-behaviour stays the rule: a behaviour is trained only
  once schemas can represent it; capability status stays gated by D-005/POL-A.
- **Trade-off:** the dataset cannot yet teach some genuinely useful future behaviours (video
  review, proactive reminders) until the product builds them.
- **Unresolved dependency:** tied to D-005's capability registry; a capability status change
  requires a new dataset version (see `.claude/rules/product.md`).
- **PO outcome:** **accept** → confirmed by product owner 2026-09-28.
- **Recommended status:** ☐ confirmed ☐ revise ☐ reject ☐ needs discussion

---

## C. Verification (D-003, D-004, D-005)

### D-003 — A photo or screenshot alone never verifies completion
- **PO outcome:** **revise**, superseded by confirmed **D-022**. A photo/screenshot may fully verify when
  the task criterion is directly and reliably determinable from the image; otherwise it may be part of
  a combined verification.
- **Implementation note:** v0.1.1 keeps its existing versioned contract; D-022 requires versioned
  schema/validator/prompt work before it governs a new release.
- **Recommended status:** ☐ confirmed ☑ revise ☐ reject ☐ needs discussion

### D-004 — Self-report is legitimate, but its confidence is limited
- **Current decision:** self-report, user-entered data and image descriptions cap confidence at
  *limited*. Insufficient evidence leads to `needs_more_evidence`, never rejection.
- **Why it matters:** sets the honesty ceiling on what the model can claim it has verified, and
  protects users from being penalized when evidence is merely incomplete rather than
  contradictory.
- **If confirmed:** the evidence-class → confidence-ceiling table in POL-B (limited / medium /
  high) stays the enforced rule, with `VP_CEILING_ABOVE_EVIDENCE` and
  `VR_CONFIDENCE_ABOVE_EVIDENCE` as gates.
- **Trade-off:** users who did complete honest work but can only self-report it never get a "high
  confidence" verification, which may feel unrewarded.
- **Unresolved dependency:** none identified beyond ordinary human review of the 16 ledger entries
  POL-B changed.
- **Recommended status:** ☐ confirmed ☐ revise ☐ reject ☐ needs discussion

### D-005 — Only capabilities the product has are used or promised
- **PO outcome:** **revise**, superseded by confirmed **D-023**. Video, proactive reminders, calendar
  access, API calls, account access and third-party contact are planned roadmap capabilities; they remain
  unavailable to the current v0.1.1 training contract until shipped.
- **Implementation note:** the current training contract remains unchanged; versioned follow-up work
  incorporates the new capability roadmap.
- **Recommended status:** ☐ confirmed ☑ revise ☐ reject ☐ needs discussion

### D-013 — User data never enters training automatically
- **Current decision:** no real user data is in the dataset. Any future use of product data needs
  explicit consent, anonymisation, a documented source and human review.
- **Why it matters:** core privacy commitment; the entire v0.1.x dataset is agent-authored
  synthetic data specifically to avoid this risk.
- **If confirmed:** the dataset stays 100% synthetic until a separate, explicitly consented
  pipeline is built and reviewed — a significant future undertaking if ever pursued.
- **Trade-off:** synthetic data may miss some real-world nuance and edge cases that only real user
  interactions would surface.
- **Unresolved dependency:** none for the current milestone; relevant if/when a future milestone
  proposes incorporating real user data.
- **PO outcome:** **accept** → confirmed by product owner 2026-09-28.
- **Recommended status:** ☐ confirmed ☐ revise ☐ reject ☐ needs discussion

### D-014 — Training-ready data requires approval gates
- **Current decision:** only content a qualified human approved by exact content hash reaches a
  training file; the release must also pass every gate in `configs/release_gates.yaml`; automation
  never approves; gates are never loosened to force a pass.
- **Why it matters:** this is the single gate standing between "dataset exists" and "model can be
  trained" — currently 1 of 11 gates pass, and 0 examples are approved.
- **If confirmed:** Milestone 1.7 (human review) and M3 (pilot fine-tune) stay blocked exactly as
  planned until real human approvals and gate passes occur; no shortcut is taken.
- **Trade-off:** slower path to a trainable model; requires sustained human reviewer time and at
  least 2 RU + 2 EN reviewers plus domain experts.
- **Unresolved dependency:** directly blocks/depends on Milestone 1.7 (reviewer registration,
  calibration) and the 5 open licensing items in `configs/licensing_status.yaml`.
- **PO outcome:** **accept** → confirmed by product owner 2026-09-28.
- **Recommended status:** ☐ confirmed ☐ revise ☐ reject ☐ needs discussion

### D-015 — Releases are immutable, and every change is traced
- **Current decision:** a changed example gets a new `dataset_version` and a revision-ledger entry
  (defect, correction, rationale, snapshots). `gj split` refuses an incomplete ledger. No silent
  edits.
- **Why it matters:** guarantees reproducibility and auditability of exactly what any trained
  model saw, and that v0.1.0 stays a frozen, comparable baseline.
- **If confirmed:** the current 36-entry v0.1.1 ledger (13 defect fixes, 23 policy alignments)
  stays the model for all future content changes.
- **Trade-off:** even small fixes require a full ledger entry and version bump — more process
  overhead than editing in place.
- **Unresolved dependency:** none identified; already enforced by `gj revisions check`/`sync` and
  tests.
- **PO outcome:** **accept** → confirmed by product owner 2026-09-28.
- **Recommended status:** ☐ confirmed ☐ revise ☐ reject ☐ needs discussion

### D-016 — Records are validated against the rules of their own `schema_version`
- **Current decision:** old data is never re-judged by newer rules; each record is checked against
  its own recorded `schema_version`.
- **Why it matters:** lets the schema/rules evolve (e.g. v0.1.0 → v0.1.1's new POL-A…F validators)
  without silently invalidating or falsely failing frozen historical data.
- **If confirmed:** v0.1.0 stays reproducible under its original rules forever; new rules apply
  only to v0.1.1+ content.
- **Trade-off:** the dataset can carry old examples that would fail the *current* rules but are
  still considered valid under their own version — a reviewer must know which rules applied when
  judging older content.
- **Unresolved dependency:** none identified.
- **Recommended status:** ☐ confirmed ☐ revise ☐ reject ☐ needs discussion

---

## E. Evaluation / release (D-017, D-018, D-019)

### D-017 — Evaluation is independent of training
- **Current decision:** separate seeds; eval-side scenarios whose decision patterns differ from
  every training pattern; no shared scenario groups; reviewed overlaps need human dispositions; no
  report ever claims "no leakage".
- **Why it matters:** without this, evaluation scores would be inflated by the model having seen
  equivalent scenarios during training — the independence claim is what makes the eval numbers
  meaningful at all.
- **If confirmed:** the current 63-case v0.2.0 eval set, its 8 leakage layers/3 families, and the
  policy of never claiming "no leakage" stay the standard going forward, including for the planned
  ≥ 200-case M2 expansion.
- **Trade-off:** authoring fully independent eval scenarios is slower and more expensive than
  reusing/perturbing training scenarios.
- **Unresolved dependency:** 100 reviewed overlaps in `evaluation/leakage/v0.2.0.yaml` (plus 27 in
  v0.1.0) currently have no human disposition — this is explicitly Milestone 1.7 task 6.
- **Recommended status:** ☐ confirmed ☐ revise ☐ reject ☐ needs discussion

### D-018 — Metrics are reported per metric and per dimension, with no overall score
- **Current decision:** no single overall score; multi-step cases are scored per teacher-forced
  step, and a case passes only if all its steps pass.
- **Why it matters:** prevents a single composite number from hiding a serious weakness in one
  dimension (e.g. safety) behind strength in another (e.g. language quality) — mirrors the "no
  averaging" principle in the human-review rubric (§14, criterion O).
- **If confirmed:** all future eval reports stay per-metric/per-dimension, and the "all steps must
  pass" rule for multi-step cases stays in force.
- **Trade-off:** harder to communicate a single "how good is the model" headline number to
  stakeholders outside the team.
- **Unresolved dependency:** none identified.
- **Recommended status:** ☐ confirmed ☐ revise ☐ reject ☐ needs discussion

### D-019 — Evaluation cases are authored in `evaluation/builders/` and rendered to YAML
- **Current decision:** the generated YAML under `evaluation/cases/v0.2.0/` is never hand-edited;
  it's rendered from Python builders via `gj eval build-cases`.
- **Why it matters:** keeps eval cases reproducible, diffable at the source level, and prevents
  silent drift between generated files and their logical source.
- **If confirmed:** the builder → render → `--check` drift-check workflow stays the only way to
  change eval cases.
- **Trade-off:** authoring in Python builders has a steeper learning curve than editing YAML
  directly.
- **Unresolved dependency:** none identified; already enforced (`gj eval build-cases --check`
  passes today).
- **Recommended status:** ☐ confirmed ☐ revise ☐ reject ☐ needs discussion

---

## F. Engineering process (D-020)

### D-020 — The repository is the durable project state
- **Current decision:** state lives in `docs/PROJECT_STATE.md`, `ACTIVE_MILESTONE.md`,
  `DECISIONS.md` and `ROADMAP.md`, not in chat history. One milestone is handled per primary
  session.
- **Why it matters:** this is a process decision (how the team/agent works), not a product
  decision — but it directly affects how reliably the product decisions above are tracked and
  recovered across sessions.
- **If confirmed:** no product-facing change; the orchestration setup (`CLAUDE.md`, skills,
  subagents, state files) stays the working model for future sessions.
- **Trade-off:** requires discipline to update the state files at every checkpoint; if skipped,
  the repository's "source of truth" claim degrades.
- **Unresolved dependency:** `docs/PROJECT_STATE.md` currently names the working branch as
  `claude/fervent-keller-j517cd`, while the actual current branch is
  `claude/blissful-einstein-vtgg7w` — a small state-file drift worth the owner noting, though not
  a product decision.
- **Recommended status:** ☐ confirmed ☐ revise ☐ reject ☐ needs discussion

---

## Decision Dependencies

**Must be resolved before Human Review Round 1 (Milestone 1.7) can start meaningfully:**
- None of D-001…D-020 are a hard *technical* blocker to beginning review — reviewers can rate
  examples against the current rubric regardless of whether the owner has formally confirmed the
  policies. However, `docs/POLICY_DECISIONS_v0.1.1.md` explicitly states POL-A…F "should be
  confirmed by the product owner" and reviewers are asked to judge examples against these very
  policies (`docs/HUMAN_REVIEW_GUIDE.md` §1.3). Confirming **D-003, D-004, D-005 (verification/
  capabilities)**, **D-009, D-010 (AI behaviour)** and **D-008 (safety)** first gives reviewers a
  stable rubric to rate against, rather than rating against policy that might still change.
  Reasoning: these six decisions are exactly the ones the review rubric's hard gates (L, M) and
  most-cited criteria (G, H, N) are built on.
- Milestone 1.7 task 8 in `docs/ACTIVE_MILESTONE.md` already names this: "Confirm POL-A…F, and
  assign owners for the 5 licensing items | product owner" — i.e. the milestone's own plan treats
  policy confirmation as parallel, owner-side work, not a strict prerequisite gate.

**Must be resolved before Model Training (Milestone 3):**
- **D-014** (approval gates) — training is contractually blocked on this until every release gate
  passes; this is not negotiable without a new decision.
- **D-013** (no automatic real user data) — any change here would itself require a new decision
  and likely a new dataset version before training could use different data sources.
- **D-005 / D-011** (capabilities and representable behaviour) — the base model's promised
  capabilities must match what's actually shipped, or the trained model will make promises the
  product can't keep.
- **D-017** (eval independence) — training readiness gates depend on a leakage report that never
  claims "no leakage" and has human dispositions on all overlaps; this must hold before a model
  trained on this data is evaluated as ready.
- Reasoning: M3 in `docs/ROADMAP.md` is explicitly "blocked until all release gates pass, including
  licensing," and `docs/PROJECT_STATE.md` confirms 1/11 gates currently pass.

**Can safely remain provisional for now (revisit later, not urgent):**
- **D-006, D-007** (levels/achievements, off-topic redirect) — stable product-scope decisions with
  no open dependency or pending review item naming them.
- **D-015, D-016, D-018, D-019** (immutability, schema-version validation, no-overall-score
  reporting, builder-authored eval cases) — these are already fully enforced by tooling and tests
  today; confirming them changes nothing operationally in the short term.
- **D-020** (repository-as-state) — a process decision with no product consequence; can be
  confirmed at the owner's convenience.
- Reasoning: none of these appear as a named blocker in `docs/PROJECT_STATE.md` §Blockers or
  `docs/ACTIVE_MILESTONE.md` §Blockers, and none gate a release or review action directly.

## What the product owner needs to provide before Human Review Round 1

(Summarised from `docs/HUMAN_REVIEW_GUIDE.md` and `docs/ACTIVE_MILESTONE.md`; the agent does not
perform any of these steps.)

1. **Reviewer registration** (`review/reviewers.yaml`, currently empty: `reviewers: []`) — at
   least 2 reviewers who read Russian and 2 who read English (mixed-input examples need a reviewer
   who reads both), plus `domain_expert`s covering whichever of medical, mental_health, legal,
   financial, physical_safety, privacy or safety_policy the expert-tier examples touch. Reviewers
   must be real humans (`human: true`); an AI agent cannot be registered.
2. **Reviewer language coverage** — enforced by `configs/review.yaml`: approval of a Russian
   example needs a reviewer who reads Russian; approval of a mixed-language example needs a
   reviewer who reads both Russian and English.
3. **Calibration requirement** — every reviewer must independently rate the same 8 calibration
   items first (`rv-0.1.0-02, -06, -07, -09, -12, -20, -29, -30`; items -06 and -20 changed in
   v0.1.1) before doing the rest of the sample.
4. **Agreement target (release gate)** — on the calibration items, every reviewer pair with ≥ 8
   shared items must agree on the decision (approve/revise/reject) in ≥ 75% of items with Cohen's
   kappa ≥ 0.40 (`configs/release_gates.yaml`, gate `calibration_agreement`).
5. **Review statuses** — decisions are `approved`, `needs_revision` or `rejected` (derived, never
   authored); `pending` covers `not_reviewed`, `content_changed` or `awaiting_expert`. Only
   `approved` content can ever reach a training file. With multiple reviewers, the most
   conservative decision wins until an adjudicator resolves it.
6. **Expert-review requirements** — examples with a non-`allowed` safety category or an explicit
   risk tag are `expert_review_required` and stay `pending` (detail `awaiting_expert`) until a
   `domain_expert` covering every required domain has signed off; this covers 10 examples in
   v0.1.0.
7. **Time expectation** — roughly one working day per reviewer for the 30-item sample, plus about
   half a day for the 8 calibration items and the disagreement discussion that follows.

## Files this checklist does not change

Per the task scope, this document changes nothing else: `docs/DECISIONS.md` statuses,
`data/raw/examples/`, `evaluation/cases/`, `configs/release_gates.yaml`, `schemas/`, and
`docs/ACTIVE_MILESTONE.md`'s milestone status all remain exactly as they were.
