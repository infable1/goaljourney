---
name: release-check
description: Build and check an immutable GoalJourney dataset release, read the release gates, gate exports, and run the pre-training readiness checklist. Use when bumping dataset_version, running `gj split`, `gj gates` or `gj export`, deciding whether a release is training_ready, or before anyone proposes fine-tuning.
---
# Release and pre-training checks

Gate thresholds and rationale: `configs/release_gates.yaml`. Split logic: `generation/pipelines/split.py`.
Never loosen a gate, a threshold or a review policy to get a pass (CLAUDE.md).

## A. Build a new release

1. **Version.**
   - Bump `dataset_version` in `configs/versions.yaml`, plus any other version whose artefact
     changed: schema, prompts, pipeline or evaluation.
   - `gj split` refuses to overwrite a released version, and releases never change.
2. **Ledger.**
   - `data/revisions/v<new>.yaml` must account for every change since the base release.
   - Run `gj revisions sync` (hashes and snapshots), then `gj revisions check`.
3. **Health.**

   ```bash
   python3 scripts/gj.py validate --strict      # warnings block here; list every failing id
   make check
   ```

   `--strict` failing on a known issue (e.g. KI-033 → `gj-vres-007`) blocks `training_ready`, not a
   draft release. Report it, and don't suppress it.
4. **Frozen artefacts are untouched.** This must print nothing:
   `git diff --stat --diff-filter=MD <base-release-commit> -- data/train data/validation data/test schemas/archive evaluation/cases/v0.1.0`.
   New files for the new version are expected; modified or deleted old ones are not.
5. **Build.**

   ```bash
   python3 scripts/gj.py split --dry-run         # selection, leakage guard, ledger, group split — no files written
   python3 scripts/gj.py split                   # default review policy: require_approved
   ```

   `--review-policy allow_pending` produces a `draft_unreviewed` release. Use it only when the
   milestone explicitly calls for a draft, and say so in the report.
6. **Gates.** Run `python3 scripts/gj.py gates`, and `--purpose preference` for DPO.
   - Report every failing gate with its reason line. Failing gates are expected until human review,
     licensing and coverage are done.
   - They are findings, not tasks to "fix" by editing gates.
   - State the review mode. Gates scoped `multi_reviewer` show **N/A** in `solo_owner` mode (D-026).
     Report them as N/A, never as passed.
   - Report the manifest's `training_eligibility`: eligible count, and ineligible examples by
     reason.
7. **Afterwards.**
   - `gj audit --write` and `gj review sample-status --write` (new version files).
   - Update `docs/PROJECT_STATE.md` (versions table — a test checks it), `CHANGELOG.md` and the
     milestone progress.

## B. Exports

```bash
python3 scripts/gj.py export --format sft|preference|eval [--version V] [--out exports/...]
```

- Training formats export only approved rows, and refuse a release whose gates fail.
- `--allow-draft` marks the output `training_eligible: false`. It is for pipeline smoke tests only,
  never for training.
- `exports/` is git-ignored. Never commit exports.

## C. Pre-training readiness checklist

Training starts only if the active milestone calls for it **and** every item holds. This skill
reports readiness; it never starts training.

| # | Check | Evidence |
|---|---|---|
| 1 | `gj gates` passes every gate applicable in the review mode (solo_owner: 9, multi_reviewer: 11) for the release and purpose; every train/validation row is `approved` by a qualified human (D-030: no expert sign-off required) | command output, manifest `training_eligibility` |
| 2 | Licensing LIC-001…005 resolved by a person, with evidence | `configs/licensing_status.yaml` |
| 3 | Base model chosen and recorded, and its licence permits the use (LIC-003) | `configs/versions.yaml` `base_model` |
| 4 | Prompt parity: the SFT export and the eval runner use the same navigator prompt version | `configs/export.yaml`, `configs/evaluation.yaml` |
| 5 | The eval set is frozen for the run, its leakage overlaps have human dispositions, and it has not been trained on | `gj leakage`, `evaluation/leakage/*.yaml` |
| 6 | The baseline eval of the untuned base model is recorded, so gains can be measured | eval report summary in the milestone docs |
| 7 | Checkpoints, logs and exports are written outside git (ignored paths) | `.gitignore`, `git status` |
| 8 | Training config, data version and seeds recorded for reproducibility | the run record the M3 milestone defines |

A model-training skill will be added with the M3 training code (`docs/ROADMAP.md`). Until then,
report readiness and stop.
