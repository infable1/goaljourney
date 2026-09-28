---
paths:
  - "tests/**"
  - "Makefile"
  - "generation/validators/**"
  - "evaluation/metrics/**"
  - "pyproject.toml"
---
# Tests, validators and metrics

## Running

- Fast: run `gj validate` (~4 s) and a targeted `python3 -m pytest -q tests/<file>.py -k <name>`.
- Before any commit that changes code or data: run `make check` (~2 min). All of it must pass.
- `gj gates` fails by design until human review is done. That is not a test failure to "fix".

## Never weaken

- Don't skip, xfail, delete or loosen a test, a validator rule, a check or a release gate to get
  green. A failing test is a finding: fix the root cause, or report it.
- If a check is genuinely wrong (a false positive), fix it precisely:
  1. add a test for the false positive;
  2. keep the true positives failing;
  3. record the change in the next audit or CHANGELOG entry.

## Validators (`generation/validators/`)

- New or changed rules that alter results for existing data are version-gated
  (`c.since("<schema_version>")`). v0.1.0 records must still be judged by v0.1.0 rules. Verify
  this: the lint output for released v0.1.0 data must not change.
- **Errors block; warnings surface** (`--strict` blocks warnings).
- **Every rule has a code** and a test in `tests/`, and is mapped to a failure mode in
  `FAILURE_MODE_CODES` if it detects one. The contrastive self-test relies on that mapping.
- **Known heuristic false positives.** Rephrase around them in authored text; don't disable the rule.
  - `ARITH_TEXT_UNDERIVABLE` reads "N weeks left" as remaining work.
  - `RU_GENDERED_SELF_REFERENCE` reads a sentence-initial noun plus a feminine past-tense verb
    («Библиотека перенесла») as self-reference.

## Metrics (`evaluation/metrics/`)

- A new check must pass on every reference output and fail the naive baseline somewhere. Both are
  enforced by tests.
- There is no overall score (D-018). Metrics are reported per metric and per dimension, and a case
  passes only if all its units pass.

## Tests that guard frozen artefacts

- Tests must never build a release or write committed files as a side effect. For example,
  `test_existing_release_is_idempotent` skips when the current version is not released.
- `tests/test_orchestration.py` checks that `CLAUDE.md` stays under 200 lines and that the
  `.claude/` files are well-formed. It also checks that `docs/PROJECT_STATE.md` matches
  `configs/versions.yaml`. Update the state file, not the test.
