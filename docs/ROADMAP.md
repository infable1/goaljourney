# Roadmap

Milestone-level plan. Details for the active milestone are in `ACTIVE_MILESTONE.md`; history is in
`CHANGELOG.md`. Milestones marked *proposed* have no owner brief yet and may change.

| Milestone | Goal | Status |
|---|---|---|
| **M1** Dataset foundation | Schemas, validators, 93 examples, 30 eval cases, pipelines, release v0.1.0 | done |
| **M1.5** Human review & calibration tooling | Review system, audit, known issues, leakage layers, release gates | done |
| **M1.6** Dataset calibration v0.1.1 | Policies POL-A…F, deterministic validators, 36 traced revisions, evaluation v0.2.0, draft release v0.1.1 | done |
| **M1.7** Human review round 1 | Owner decisions on the sample, the revisions and open known issues; overlap dispositions; policy confirmation | in progress (see `ACTIVE_MILESTONE.md`): calibration items decided; qualified domain experts and the rest of the review are open |
| **M1.7a** Solo-owner review governance (D-026) | Move from multi-reviewer-first governance to solo-owner-first governance with optional expert escalation: governance modes, gate scopes (pairwise gates N/A in solo mode, never passed), training-eligibility accounting in release manifests, AI copilot and "unsure" guidance; historical events and v0.1.1 unchanged | done 2026-09-29 (pipeline 0.4.0, release gates 1.1) |
| **M2** Synthetic scale-up | ~2,000 training examples via the generation pipeline (≤ 50 per run, all human-reviewed); rejected outputs for every failure mode; evaluation grown to ≥ 200 independently authored cases | planned (`DATASET_SPEC` §18, `docs/EVALUATION_EXPANSION_PLAN.md`) |
| **M3** Pilot fine-tune | Choose a ~4B open-weight base model with a commercial-use licence; first SFT (and optionally preference) run on a training-ready release; evaluate with evaluation v0.2+ | planned. Blocked until all release gates pass, including licensing |
| **M4** Iterate & integrate | Error analysis, dataset iterations, serving for the product | *proposed* |

## Standing constraints

* No model training before a release is `training_ready` (D-014): every gate applicable in the
  governance mode in force passes (D-026). Expert-tier coverage still needs qualified human experts.
* Generation and evaluation grow in parallel. Evaluation authorship stays independent (D-017).
* Product and mobile-app features are out of scope for this repository.
