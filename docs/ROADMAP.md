# Roadmap

Milestone-level plan. Details for the active milestone are in `ACTIVE_MILESTONE.md`; history is in
`CHANGELOG.md`. Milestones marked *proposed* have no owner brief yet and may change.

| Milestone | Goal | Status |
|---|---|---|
| **M1** Dataset foundation | Schemas, validators, 93 examples, 30 eval cases, pipelines, release v0.1.0 | done |
| **M1.5** Human review & calibration tooling | Review system, audit, known issues, leakage layers, release gates | done |
| **M1.6** Dataset calibration v0.1.1 | Policies POL-A…F, deterministic validators, 36 traced revisions, evaluation v0.2.0, draft release v0.1.1 | done |
| **M1.7** Human review round 1 | Calibration agreement, decisions on the revisions and open known issues, overlap dispositions, policy confirmation | *proposed* — next; needs human reviewers |
| **M2** Synthetic scale-up | ~2,000 training examples via the generation pipeline (≤ 50 per run, all human-reviewed); rejected outputs for every failure mode; evaluation grown to ≥ 200 independently authored cases | planned (`DATASET_SPEC` §18, `docs/EVALUATION_EXPANSION_PLAN.md`) |
| **M3** Pilot fine-tune | Choose a ~4B open-weight base model with a commercial-use licence; first SFT (and optionally preference) run on a training-ready release; evaluate with evaluation v0.2+ | planned. Blocked until all release gates pass, including licensing |
| **M4** Iterate & integrate | Error analysis, dataset iterations, serving for the product | *proposed* |

## Standing constraints

* No model training before a release is `training_ready` (D-014).
* Generation and evaluation grow in parallel. Evaluation authorship stays independent (D-017).
* Product and mobile-app features are out of scope for this repository.
