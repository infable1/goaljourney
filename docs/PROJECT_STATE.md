# Project state

*Last updated: 2026-09-28 · after Milestone 1.6 and the orchestration setup. Update this file
before declaring any milestone complete (`/milestone-complete`).*

This file is the durable, factual snapshot of the repository. The repository is the source of
truth; chat history is not.

## Repository

| | |
|---|---|
| Repository | `infable1/goaljourney` — dataset, validation and evaluation pipeline for the GoalJourney Navigator model |
| Working branch | `claude/fervent-keller-j517cd`. It is the only branch on the remote: there is no `main` and no pull request yet |
| History | `995f513` M1 → `476d322` M1.5 → `c3b7cfb`…`13d837e` M1.6 → orchestration setup (latest commits: `git log --oneline -5`) |
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
* Active: see [`ACTIVE_MILESTONE.md`](ACTIVE_MILESTONE.md). Plan: [`ROADMAP.md`](ROADMAP.md).

## Model training

**Not started.** No base model is chosen, and no training code is in the repository. Training
exports are refused until every release gate passes. Today 1 of 11 passes (`gj gates`).

## Implemented capabilities

* **Data contract.**
  * JSON Schemas for 14 operations, with records validated against their own `schema_version`.
  * Semantic lint of ~170 rules: calendar, workload arithmetic, deadline autonomy, capabilities,
    evidence ceilings, fact provenance, Russian voice.
  * A contrastive self-test.
* **Data.** 93 agent-authored examples (RU 41 / EN 52) and 64 rejected outputs. The revision ledger
  `data/revisions/v0.1.1.yaml` records 36 revised examples.
* **Review.** A rubric, an append-only hash-chained decision log, a reviewer registry (empty) and
  expert tiers. The 30-item sample has 8 calibration items, and a per-version sample status file.
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

`make check` passes:

* 425 tests, 9 of them in `tests/test_orchestration.py`;
* the builder, ledger and sample drift checks;
* reference 106/106, naive 0/106.

`gj validate` has 1 warning: gj-vres-007 (KI-033).

## Blockers

1. **No human review yet.** 0 reviewers registered and 0 decisions. This blocks 8 of the 10 failing
   gates directly or indirectly.
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
