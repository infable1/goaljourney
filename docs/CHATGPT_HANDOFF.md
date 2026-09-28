# ChatGPT handoff — GoalJourney

*Written 2026-09-28, from repository state at commit `7e74c99`. Current branch: inspect with
`git branch --show-current` — Claude Code branches here are ephemeral session branches, not durable
product state. This file is documentation only; it changes no dataset, schema, evaluation or
product content.*

Lets a **new ChatGPT session** pick up GoalJourney without earlier chat history. The repository —
not this file, not chat history — is the source of truth (`docs/CONTEXT_MANAGEMENT.md`, D-020).
Where this file and the repository disagree, trust the repository.

## How the next ChatGPT session should use this file

1. Read this handoff fully before acting.
2. If the repository is available, inspect it directly (`git status`, `git log`, the files cited
   here) rather than trusting an older conversation.
3. Treat repository files as truth over this handoff, and this handoff over remembered chat.
4. Keep `confirmed` / `adopted` / `open` statuses distinct (§I) — never present adopted or
   historical items as confirmed.
5. Do not invent missing information (base model, price, timeline). If it isn't in the repository,
   say it's undecided.
6. Continue from the current milestone (§H); don't propose skipping ahead to generation, training
   or export while it's blocked.
7. End your response by telling the product owner explicitly what they need to decide or do next.

---

## A. Project identity

* **Name:** GoalJourney (model component: "GoalJourney Navigator").
* **Description:** GoalJourney helps one user reach one personal goal. This repository is the
  **dataset, validation and evaluation pipeline** for a specialised, small (~4B) open-weight
  multilingual model that clarifies a goal, builds a living route (the Journey), verifies progress
  from evidence, and adapts the route — not the mobile app, and not a general assistant.
* **User promise:** *"I have a difficult goal, but now I always know what to do next."*
* **Direction:** calibration (M1.6) is done; human review (M1.7, proposed) is next, before any
  scale-up generation, training or release.

## B. Product vision

**Goal → dynamic AI onboarding (clarification) → feasibility check → Journey (route) → Tasks →
Verification → Progress → Route adaptation → daily navigation → goal completion / reflection**
(`DATASET_SPEC.md` §5–6). The navigator asks only useful questions, proposes a route the user
controls, verifies progress from task-specific evidence, and adapts the route as reality changes.
It is a goal navigator, not a general assistant (D-007): off-topic requests get a brief redirect.

## C. Core product principles

All durable decisions below are **Status: adopted** in `docs/DECISIONS.md` — decided by dataset
engineering, awaiting product-owner confirmation; none are marked `confirmed`.

* User controls the Journey; major route/goal changes need confirmation; verified progress is never
  silently discarded (D-001).
* Deadline autonomy is tiered: task dates auto-adapt, milestone dates adapt with a stated summary,
  goal dates only change after user confirmation (D-002).
* A photo/screenshot alone never verifies completion (D-003).
* Self-report is capped at *limited* confidence; insufficient evidence → `needs_more_evidence`, not
  rejection (D-004).
* Only capabilities the product actually has are used or promised — no video analysis, reminders,
  calendar access, API calls, or account access (`configs/product_capabilities.yaml`, D-005).
* Levels/achievements follow verified progress, never app activity (D-006).
* Safety: no medical/legal/financial prescriptions; high-risk goals get referral; restricted goals
  get a legitimate alternative (D-008).
* Facts keep provenance (user_provided/model_inferred/externally_verified/unknown); current
  external facts come only from provided research (D-009).
* Russian output is gender-neutral for both the assistant and the user (D-010).
* Model/provider stays replaceable; base model is unset until chosen, recorded only in
  `configs/versions.yaml` (D-012).
* Real user data never enters training automatically (D-013).
* Training-ready data needs per-example human approval and passing release gates; automation never
  approves (D-014).
* Releases are immutable; content changes need a new `dataset_version` and ledger entry (D-015).

## D. Monetization

**Not documented in the repository** (this repo covers the pipeline, not the app/pricing). The
following is carried from prior product discussion only — **historical context pending formal
confirmation**, not a decided fact:

* Free: one active goal. Premium: unlimited active goals.
* Basic necessary research must not be blocked when required for safe/correct operation.
* Premium may include deeper planning, more frequent adaptation, harder verification, deeper
  memory, advanced statistics, deep research, customizable map themes.

No pricing numbers exist anywhere in the repository; do not invent any.

## E. AI model strategy

**Confirmed by the repository:** no foundation-model training from scratch; `base_model` in
`configs/versions.yaml` is `unset` (D-012); target is a small (~4B) open-weight multilingual model
(`DATASET_SPEC.md` §1); languages are Russian and English; teacher/provider access sits behind one
interface (Anthropic SDK, OpenAI-compatible, or replay), SFT exports are chat-template-agnostic,
and evaluation prompts the model exactly as SFT export does (`docs/ARCHITECTURE.md` §6). No model
training has started; no training code exists yet; export is refused unless a release is
`training_ready` (today 1/11 gates pass).

**Not confirmed by the repository** — carried from prior discussion only: LoRA/QLoRA as the
fine-tuning method, the working name "GoalJourney-4B", any specific base-model family/vendor.

## F. Dataset state

* **v0.1.0** (M1): 93 agent-authored examples, immutable, frozen.
* **M1.5:** added human-review system, heuristic audit, leakage layers, release gates.
* **M1.6 — Dataset Calibration v0.1.1** (done): decided POL-A…F; revised 36 examples via a traced
  ledger (13 defect fixes, 23 policy alignments; v0.1.0 untouched); added deterministic validators
  (calendar, workload arithmetic, deadline autonomy, capabilities, evidence ceilings, provenance,
  Russian voice); replaced evaluation with v0.2.0.
* **Training pool:** 93 examples → release v0.1.1 split: train 81 / validation 12.
* **Evaluation:** v0.2.0 = 63 cases (43 atomic, 14 composite, 6 longitudinal) = 106 model calls, 658
  checks. v0.1.0 (30 cases) kept frozen but superseded (18/30 had reviewed template overlap with
  training).
* **Release status:** `v0.1.1` is `draft_unreviewed`, **not training-ready**. Live `gj gates`: **1
  of 11 pass** (`leakage_hard_clean`). Failing: `validation_strict` (1 row, `gj-vres-007`),
  `review_all_approved` (0/93), `findings_acknowledged`, `known_issues_closed` (KI-008, KI-012),
  `reviewer_diversity`, `calibration_agreement`, `leakage_dispositions` (100 overlaps undecided),
  `coverage_minimums`, `eval_readiness` (63/200 target), `licensing_resolved` (5 unresolved).
* **Human review:** 0 approved decisions, 0 registered reviewers, no `data/reviewed/` entries yet.
* **Known issues:** 34 total — 22 fixed pending review, 11 open (2 medium: KI-008, KI-012), 1
  won't-fix, plus KI-033 (fails `validation_strict`, needs reviewer decision).
* **Leakage:** 8 layers / 3 families; no hard finding today, but 100 reviewed overlaps
  (`evaluation/leakage/v0.2.0.yaml`, +27 from v0.1.0) have no human disposition.
* **Licensing:** 5 unresolved items in `configs/licensing_status.yaml` — teacher/authoring LLM
  output rights, example ownership/redistribution, base-model licence (blocked on model choice),
  nominative third-party names, reviewer rights assignment.

## G. Completed milestones

* **M1 — Dataset foundation.** Schemas, validators, 93 examples, 30 eval cases, release v0.1.0.
  Commit `995f513`.
* **M1.5 — Human review & calibration tooling.** Review system, audit, known issues, leakage,
  gates. Commit `476d322`.
* **M1.6 — Dataset calibration v0.1.1.** Policies POL-A…F, validators, 36 traced revisions,
  evaluation v0.2.0, draft release v0.1.1. Commits `c3b7cfb`…`13d837e`.
* **Project orchestration.** `CLAUDE.md`, path-scoped rules, skills, subagents. Commit `7e74c99`
  (current HEAD).

## H. Current milestone

**M1.7 — Human Review Round 1**, status **proposed, not started** (`docs/ACTIVE_MILESTONE.md`),
0% progress. Objective: get the first qualified human decisions on v0.1.1 data and evaluation
references so review-dependent gates can move; trains no model, generates no data. Tasks: register
≥2 RU / ≥2 EN reviewers, rate 8 calibration items, check agreement (κ ≥ 0.40, ≥75%), review the 36
ledger revisions, decide KI-008/KI-012/KI-033, disposition the ~127 evaluation overlaps, review
v0.2.0 references, confirm POL-A…F and licensing owners.

**Every decision task is reserved for a human reviewer or the product owner** — an AI session's
role here is limited to preparing packets and applying already-decided fixes, never deciding.

## I. Product owner decisions

* **Confirmed by product owner:** none. `docs/DECISIONS.md` defines "confirmed" as owner-decided;
  every `D-001`…`D-020` entry is currently `adopted` only.
* **Adopted, awaiting confirmation:** all of D-001…D-020, and all of POL-A…F
  (`docs/POLICY_DECISIONS_v0.1.1.md`, explicitly awaiting owner confirmation).
* **Open/unresolved:** the 5 licensing items; which base model and its licence; owner sign-off on
  POL-A…F; the monetization model (§D — not in any decision document).

## J. Open issues

* Human review: 0 reviewers, 0 decisions — blocks 8 of 10 failing gates.
* Reviewer roster empty (`review/reviewers.yaml`).
* POL-A…F need explicit owner confirmation.
* ~127 evaluation overlaps need human dispositions.
* 5 licensing items unresolved, all block `training_ready`.
* KI-008, KI-012 open (medium); KI-033 needs a reviewer's choice; 22 more fixed-pending-review.
* Coverage short of targets: eval 63/200 cases, approved training rows 0/1000.
* Full picture: live `gj gates` (§F) — 1/11 pass.

## K. Human review plan

Per `DATASET_SPEC.md` §14 and `docs/HUMAN_REVIEW_GUIDE.md`, not yet executed:

* Independent reviewers register in `review/reviewers.yaml` (humans only).
* 8 shared calibration items rated independently first (rv-0.1.0-02, -06, -07, -09, -12, -20, -29,
  -30; -06/-20 changed in v0.1.1).
* Agreement measured via `gj review stats`/`gj gates`: ≥75% pairwise agreement, κ ≥ 0.40.
* Each of the 36 ledger revisions needs a human `reviewer_status`.
* Each reviewed evaluation overlap needs a human disposition.
* Decisions recorded via `gj review approve|revise|reject` into an append-only, hash-chained log;
  automation never approves; validation passing is never treated as review.

No reviewers are registered today. **Do not invent or register fictional reviewers.**

## L. What must NOT happen yet

* Large-scale dataset generation (Milestone 2, ~2,000 examples) — not started.
* Final training-dataset export (`gj export` without `--allow-draft`) — release isn't training-ready.
* Any model training — no training code exists; `base_model` is unset.
* Production AI deployment.
* Uncontrolled real-user data collection for training (D-013).

## M. Immediate next steps

**Product owner**
1. Register ≥2 RU and ≥2 EN reviewers (plus domain experts) in `review/reviewers.yaml`.
2. Confirm or amend POL-A…F.
3. Assign owners and resolve the 5 licensing items.
4. Decide whether M1.7 is the next milestone, or issue a different brief.

**Claude Code (after owner decisions)**
1. Once reviewers are registered, prepare calibration/review packets (`/dataset-review` skill).
2. Apply reviewer-decided fixes for KI-008/KI-012/KI-033 via the revision ledger — never deciding
   the fix itself.
3. Record evaluation-overlap dispositions reviewers make; keep `PROJECT_STATE.md` /
   `ACTIVE_MILESTONE.md` current.

**Future (wait)**
1. Milestone 2 scale-up generation — waits on M1.7, capped at 50 candidates/run, human-reviewed.
2. Milestone 3 pilot fine-tune — waits on every release gate passing, including licensing and a
   chosen base model.
3. Any monetization/pricing decision — not yet represented in this repository.

---

## Sources used

`CLAUDE.md`, `README.md`, `DATASET_SPEC.md`, `docs/PROJECT_STATE.md`, `docs/ACTIVE_MILESTONE.md`,
`docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/POLICY_DECISIONS_v0.1.1.md`,
`docs/DATASET_AUDIT_v0.1.1.md`, `docs/EVALUATION_V0.2_DESIGN.md`, `docs/ARCHITECTURE.md`,
`configs/release_gates.yaml`, `configs/licensing_status.yaml`, and live `git status`/`git log`/
`gj validate`/`gj revisions check`/`gj eval build-cases --check`/`gj gates` at commit `7e74c99`.
