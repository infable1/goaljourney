---
paths:
  - ".env*"
  - ".gitignore"
  - ".claude/settings*.json"
  - "gjcore/env.py"
  - "generation/generators/providers.py"
  - "configs/generation.yaml"
  - "configs/evaluation.yaml"
  - "configs/licensing_status.yaml"
  - "DATA_SOURCES.md"
  - "scripts/**"
---
# Secrets, credentials, privacy and licensing

## Secrets

- Credentials are read only from the environment, or from the git-ignored `.env` via `gjcore/env.py`.
  `.env.example` lists variable names with empty values.
- Never write, print, log or commit a key, token or endpoint secret: not in code, configs, tests,
  docs, commit messages or run manifests.
- Missing credentials fail with an explicit message. Never fall back to a hard-coded key.
- Project settings deny reading `.env`. Don't work around that: ask the user to set variables
  themselves.
- Before committing, check the staged diff for anything that looks like a secret. Keep `.gitignore`
  covering these:
  - `.env`;
  - model checkpoints and weights;
  - `exports/`;
  - `evaluation/reports/*/`;
  - caches;
  - `.claude/settings.local.json`.

## Network and external calls

- The only outbound calls are provider calls in `generation/generators/providers.py` and model
  evaluation endpoints. The product capability `CAP-URL-FETCH` is a *product* feature: the pipeline
  never fetches URLs from the dataset.
- Don't add new services, telemetry or MCP servers without an explicit decision in
  `docs/DECISIONS.md`.

## Privacy and data rights

- No real user data in the repository. Synthetic personas only. Never infer gender.
- Product data may enter training only through an explicit, consented, anonymised and reviewed
  process (D-013). No such process exists yet.
- The licensing items in `configs/licensing_status.yaml` (LIC-001…005) block any training-ready
  release. Only a person records their resolution, with evidence.
- Record provenance for every data source in `DATA_SOURCES.md`.
