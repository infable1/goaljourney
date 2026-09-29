# Project state

*Last updated: 2026-09-29 · during Milestone 1.7 (Human Review Round 1): calibration round recorded,
rv-0.1.0-02 adjudication pending. Update this file before declaring any milestone complete
(`/milestone-complete`).*

This file is the durable, factual snapshot of the repository. The repository is the source of
truth; chat history is not.

## Repository

| | |
|---|---|
| Repository | `infable1/goaljourney` — dataset, validation and evaluation pipeline for the GoalJourney Navigator model |
| Working branch | Default branch `claude/fervent-keller-j517cd` (there is no `main`). The M1.7 review round after `ae21c7d` is on `claude/sleepy-dijkstra-nzrf3t`, which also merged the rv-0.1.0-29 record from `claude/compassionate-noether-1o9iyx`; it is not merged into the default branch. No open pull request (infable1/goaljourney#1 and infable1/goaljourney#2 were closed unmerged) |
| History | `995f513` M1 → `476d322` M1.5 → `c3b7cfb`…`13d837e` M1.6 → orchestration setup → M1.7 review round `fdf6d4c`…`0182552` (latest commits: `git log --oneline -5`) |
| Language / stack | Python ≥ 3.10; jsonschema, referencing, PyYAML, pytest; CLI `scripts/gj.py`; `make check` |
| Mobile app / product code | not in this repository |

## Versions (`configs/versions.yaml` is authoritative)

| Artefact | Version | Notes |
|---|---|---|
| dataset | 0.1.1 | release `draft_unreviewed`: train 81, validation 12, test 63 eval cases. v0.1.0 is immutable and kept |
| schema | 0.1.1 | v0.1.0 archived in `schemas/archive/v0.1.0/` |
| pipeline | 0.3.0 | v0.1.1 validators, revision ledger, review log v0.3, eval builders |
| evaluation | 0.2.0 | 63 cases / 106 model calls (43 atomic, 14 composite, 6 longitudinal). v0.1.0 (30 cases) frozen |
| navigator prompt / generation prompts | 0.1.1 / 0.1.1 | `prompts/navigator/v0.1.1/`, `prompts/generation/v0.1.1/` |
| base model | unset | chosen later, recorded in `configs/versions.yaml` |

## Milestones

* Done: M1 (dataset foundation), M1.5 (human review system, audits, leakage, gates) and M1.6
  (dataset calibration v0.1.1).
* Active: M1.7 (Human Review Round 1), in progress; see [`ACTIVE_MILESTONE.md`](ACTIVE_MILESTONE.md).
  Plan: [`ROADMAP.md`](ROADMAP.md). Review state (from `gj review stats`, `gj gates`):
  * **Reviewers:** 2 registered humans, `po-reviewer` and `po-reviewer-two`; both `dataset_reviewer`,
    languages ru and en, no expert domains. No `adjudicator` and no `domain_expert` is registered.
  * **Decisions:** 17 review events (`po-reviewer` 9, `po-reviewer-two` 8), all stamped rubric 0.2.0.
    16 are on the 8 calibration items; 1 (`rev-da39af4d1363`, approve of `gj-daily-002`) is on an
    example outside the review sample. Pool status: approved 7, needs_revision 2, pending 84. Review
    sample: 8/30 items decided.
  * **Calibration:** all 8 items rated by both reviewers (`po-reviewer-two` from a blind packet).
    Decision agreement 7/8 (0.875),
    κ 0.60, so `calibration_agreement` passes. Overall-verdict agreement is 3/8 (κ 0.05).
  * **rv-0.1.0-02 (gj-safe-003, `high_risk`):** the reviewers disagree (revise vs approve), so it
    stays `needs_revision`. An adjudication record (approve, excellent) is prepared in git-ignored
    `scratch/` only and is **not recorded**: no adjudicator is registered. It needs `medical` and
    `physical_safety` sign-off before it can be `approved`.
  * **rv-0.1.0-30 (gj-safe-006, `restricted`):** both reviewers chose revise (external-fact
    discipline); it needs a content revision and `legal` sign-off.
  * **Rubric:** 0.2.1 is in force (D-025, restricted-goal safety anchor); 0.2.0 is kept for the
    events stamped with it.

## Model training

**Not started.** No base model is chosen, and no training code is in the repository. Training
exports are refused until every release gate passes. Today 3 of 11 pass (`gj gates`:
`findings_acknowledged`, `calibration_agreement`, `leakage_hard_clean`).

## Implemented capabilities

* **Data contract.**
  * JSON Schemas for 14 operations, with records validated against their own `schema_version`.
  * Semantic lint of ~170 rules: calendar, workload arithmetic, deadline autonomy, capabilities,
    evidence ceilings, fact provenance, Russian voice.
  * A contrastive self-test.
* **Data.** 93 agent-authored examples (RU 41 / EN 52) and 64 rejected outputs. The revision ledger
  `data/revisions/v0.1.1.yaml` records 36 revised examples.
* **Review.** A rubric (0.2.1; 0.2.0 kept), an append-only hash-chained decision log (17 events), a
  reviewer registry (2 human dataset reviewers) and expert tiers. The 30-item sample has 8
  calibration items, and a per-version sample status file (regenerated in `0182552`).
* **Audit.** Heuristic audit (`gj audit`) and the known-issues register
  `review/known_issues_v0.1.1.yaml`.
* **Leakage.** 8 layers in 3 families (lexical, semantic/template, scenario). The reviewed overlap
  list is `evaluation/leakage/v0.2.0.yaml`.
* **Releases.** Immutable releases (`gj split`), 11 release gates (`gj gates`) and gated exports
  (`gj export`).
* **Evaluation.** Builders (`gj eval build-cases`), teacher-forced multi-step units and a
  reference/naive/model runner.
* **Generation.** Synthetic generation pipeline (`gj generate`). It is provider-agnostic, capped at
  50 candidates per run, and not yet used at scale.
* **Orchestration.**
  * `CLAUDE.md` and `.claude/settings.json` (auto-compaction at 75%).
  * 6 path-scoped rules and 6 skills: `/start-session`, `/milestone-complete`, `/dataset-review`,
    `/dataset-generation`, `/evaluation`, `/release-check`.
  * 6 subagents in `.claude/agents/`.
  * These state files; see `docs/CONTEXT_MANAGEMENT.md`.

## Health (at last update)

`make -k check` passes (at `0182552`, every target):

* 424 tests passed and 2 skipped, 9 of them in `tests/test_orchestration.py`;
* the builder, ledger and sample drift checks;
* reference 106/106, naive 0/106;
* leakage: 0 hard findings;
* `gj review verify-log`: 17 events, 0 errors, 1 warning. The warning is the expected fork left by
  merging two branches that both appended to the log (guide §11).

`gj validate` has 1 warning: gj-vres-007 (KI-033).

## Blockers

1. **Human review is only at the calibration stage.** 2 dataset reviewers, 17 decisions; 22 of the
   30 sample items and the 36 ledger revisions (all `pending_human_review`) are not reviewed.
   * `review_all_approved`: 7/93 approved.
   * `reviewer_diversity` fails: `po-reviewer` approved all 7 approved rows, a 100% share (cap 80%);
     `po-reviewer-two` approved 6 of them.
   * No `adjudicator`, so the rv-0.1.0-02 disagreement cannot be resolved.
   * No `domain_expert`: expert-tier items cannot be approved. rv-0.1.0-02 needs `medical` and
     `physical_safety`, rv-0.1.0-30 needs `legal`, rv-0.1.0-28 needs `financial`.
2. **Policies POL-A…F** need product-owner confirmation (`docs/POLICY_DECISIONS_v0.1.1.md`).
3. **Licensing:** 5 open items (`configs/licensing_status.yaml`) block any training-ready release.
4. **Open known issues:** KI-008 and KI-012 (medium), and KI-033, which fails `validation_strict` and
   needs a reviewer's choice.
5. **Evaluation overlaps:** 100 reviewed overlaps have no disposition, and eval size is 63/200 cases.

## Where to look

| Need | File |
|---|---|
| Data contract | `DATASET_SPEC.md` |
| Policies | `docs/POLICY_DECISIONS_v0.1.1.md` |
| Latest audit | `docs/DATASET_AUDIT_v0.1.1.md` |
| Evaluation design | `docs/EVALUATION_V0.2_DESIGN.md` |
| Review workflow | `docs/HUMAN_REVIEW_GUIDE.md` |
| Leakage | `docs/LEAKAGE_CHECKS.md` |
| History | `CHANGELOG.md` |
| Durable decisions | `docs/DECISIONS.md` |
| Context / session rules | `docs/CONTEXT_MANAGEMENT.md` |
