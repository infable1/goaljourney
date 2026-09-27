# Data Sources, Provenance and Licensing

Last updated: 2026-09-27 (dataset v0.1.0, pipeline 0.2.0)

## Summary

| Source | Used in v0.1.0 | Licence / terms | Commercial use | Notes |
|---|---|---|---|---|
| Agent-authored synthetic examples (`data/raw/examples/`) | 93 examples | Proprietary to the project (`proprietary-internal` in each record) | See "LLM-authored content" below | Written by an AI coding agent (Claude Code) under `DATASET_SPEC.md`; not human-reviewed yet; audited in `docs/DATASET_AUDIT_v0.1.0.md` |
| Human review decisions (`data/reviewed/`) | none yet | Project records | See LIC-005 | Reviewers' decisions, notes and rewrites; rights must be assigned by reviewer agreements |
| Agent-authored evaluation cases (`evaluation/cases/v0.1.0/`) | 30 cases | Proprietary to the project | See below | Authored separately from training examples |
| Scenario seeds (`generation/scenarios/`) | 30 seeds | Proprietary to the project | Yes | Input to future synthetic generation |
| External datasets | **None** | — | — | No external dataset, benchmark or prompt set was used |
| Real user data | **None** | — | — | See "Privacy" |
| Web-scraped data | **None** | — | — | Nothing was scraped |

## Provenance in the data itself

Every record carries `provenance`:

```json
{"source": "synthetic", "method": "agent_authored", "author": "claude-code-agent",
 "created": "2026-09-27", "license": "proprietary-internal"}
```

Generated candidates additionally record `generation_run_id`, `prompt_version` and
`generator_model`; each run directory holds a `manifest.json` with the provider, model, prompt file
hashes and config snapshot. Every release manifest records all versions and per-example content
hashes and review status.

## LLM-authored content — open legal item

All v0.1.0 examples and evaluation cases were written by an AI model, and the scale-up pipeline
uses a teacher LLM. **Before training a model on this data for commercial use, verify the terms of
service of every model provider used to create it** — some providers restrict using their outputs
to develop competing models. This has not been assessed legally yet. The open questions (teacher-model
terms, ownership of AI-authored content, base-model licence, third-party names, rights to reviewer
decisions) are tracked in [`configs/licensing_status.yaml`](configs/licensing_status.yaml); the release
gate `licensing_resolved` blocks any training-ready release until each is resolved and recorded there.

## Simulated facts

Research results inside examples (e.g. a venue closing, an exam format change) are **simulated**:
they use reserved domains (`example.org`, `example.com`) and generic or fictional entities
("CloudOps Associate", "арт-пространство «Точка»"). They teach the citation pattern, not facts.
Where a real organisation or exam is mentioned (e.g. IELTS, PMP, App Store), current facts about it
are deliberately *not* asserted — they are marked as needing verification.

## Software dependencies

| Package | Version | Licence | Purpose |
|---|---|---|---|
| jsonschema | 4.26.0 | MIT | schema validation |
| referencing | 0.37.0 | MIT | `$ref` resolution |
| PyYAML | 6.0.1 | MIT | YAML authoring format |
| pytest | 9.1.1 | MIT | tests |
| anthropic (optional) | 1.8.0 | MIT | teacher model calls during generation only |

## Base model

Not chosen yet (`configs/versions.yaml → base_model` is `null`). When chosen, record here: model
name and revision, licence, whether commercial fine-tuning and deployment are permitted, and any
attribution requirements. Candidates must be open-weight with a licence permitting commercial
fine-tuning.

## Privacy

* No real user data is used, and no pipeline in this repository reads application conversations.
* Any future real-user training pipeline must be a separate system requiring explicit opt-in
  consent, anonymisation, human review and its own entry in this file. It must not be added to
  these pipelines.
* Examples avoid real personal data; personas are invented and never assigned a gender by the model.

## Adding a source

Do not incorporate any data with unclear licensing. For each new source add a row above with:
origin/URL, licence, commercial-use verdict (with who verified it and when), attribution
requirements, and how records are marked (`provenance.source = licensed_external`,
`provenance.external_source_id`).
