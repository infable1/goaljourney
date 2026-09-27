# Dataset System — Architectural Proposal (v0.1.0)

Status: accepted for Milestone 1. This is the short proposal (Step 2); the full
contract lives in [`DATASET_SPEC.md`](../DATASET_SPEC.md).

## 1. What the system has to guarantee

1. Every training target is a **structured, schema-valid JSON object** for one
   well-defined AI operation (clarify, assess, plan, verify, adapt, ...).
2. Every example is **behaviourally checked**, not just format-checked
   (dependencies form a DAG, a photo never verifies a task on its own, daily
   plans fit the time budget, major route changes need user confirmation, ...).
3. Train / validation / test are guarded against leakage (split by scenario group, layered
   exact / near-duplicate / paraphrase / template / seed checks, reviewed behavioural overlaps).
   The checks can show leakage exists, not that it is absent (`docs/LEAKAGE_CHECKS.md`).
4. Nothing is trained on until a **human** has reviewed the exact content
   (review log is keyed by content hash; edits invalidate approval).
5. Everything is **versioned and reproducible** (dataset, schema, prompt,
   pipeline, evaluation, base model); releases are immutable.

## 2. Data model

```
                ┌───────────────────────────────┐
                │  input context (one schema)   │  goal, journey, task, evidence,
                │  schemas/input_context.json   │  memory, events, research results,
                └──────────────┬────────────────┘  conversation, today's date
                               │ operation = one of 14
                               ▼
                ┌───────────────────────────────┐
                │ operation output (14 schemas) │  goal_clarification, feasibility,
                │ schemas/<operation>.json      │  journey_generation, ... progress_update
                └───────────────────────────────┘
```

* **One input schema, many output schemas.** The app always sends the same
  kind of context object; the `operation` field selects the output contract.
  This keeps the model's interface uniform and makes SFT export trivial
  (system prompt + context JSON → output JSON).
* **Entities are shared** (`goal`, `journey`, `task`, `verification_protocol`,
  `decision_summary`, `memory`, `evidence`), so the Journey grammar
  (Goal → Region → Milestone → Challenge/Task/AI Checkpoint/Decision Point/
  Verification → Achievement) is defined exactly once.
* **Language-independent structure.** Keys and enums are English; only
  user-facing strings (`message_to_user`, questions, decision summaries) are in
  the user's language, declared in `response_language`.

## 3. Example record (changed from the brief — and why)

The brief suggested `{id, version, language, category, difficulty, input,
expected_output, quality_tags, safety_category, source, review_status}`.
Changes:

| Change | Reason |
|---|---|
| `category` split into `task_type` (output contract) and `behavior[]` (A–N, safety, memory, progress) | One example often trains several behaviours (a route adaptation that is also a time adaptation with a decision summary). |
| `scenario_group` added | The unit of splitting. Examples from one scenario never straddle train/test. |
| `contrastive[]` added instead of standalone "bad" examples | A bad output is attached to the same input as the good one, tagged with `failure_modes`. SFT exports only the good output; preference export gets (chosen, rejected) pairs for free. Standalone negative examples would otherwise risk being trained on as targets. |
| `annotations` added (not model input) | Author knowledge the validators need: facts already known, questions that must be asked, strings that must not leak. |
| `version` split into `schema_version` (record) + dataset release version (manifest) | A record doesn't know which release it ends up in. |
| `review_status` moved to an append-only log (`data/reviewed/review_events.jsonl` since Milestone 1.5; hash-chained, with content snapshots) keyed by content hash | An in-file flag can be flipped silently and survives later edits. A hash-keyed log gives an audit trail and invalidates approvals when content changes. |
| `source` expanded to `provenance{source, method, author, license, ...}` | Honest labelling: these v0.1 examples are *agent-authored synthetic*, not human-authored ground truth. |

## 4. Pipeline

```
scenario specs ─► generate (teacher LLM, 2 stages: input, then output)
   (YAML)           │   provider-agnostic; fails loudly without credentials
                    ▼
               data/generated/<run_id>/candidates.jsonl  + run manifest
                    │
agent/human ───────►│
authored            ▼
data/raw/examples/*.yaml
                    │
                    ▼
            validate  = JSON Schema  +  semantic lint (~115 rules)
                        +  contrastive self-test (bad outputs must be caught)
                        +  near-duplicate / diversity check
                    │
                    ▼
            audit     = heuristic findings + known issues (review aids)
                    │
                    ▼
            review    = human decisions (rubric A–Q + overall) → data/reviewed/review_events.jsonl
                        (qualified reviewers, expert tier, snapshots, hash chain)
                    │
                    ▼
            split     = by scenario_group, stratified by behaviour,
                        layered leakage checks against evaluation cases and seeds
                    │   immutable release: data/{train,validation,test}/<ver>.jsonl
                    ▼   + data/manifests/<ver>.json (hashes, versions, counts)
            gates     = release gates → training_ready?
                    │
                    ▼
            export    = SFT chat JSONL | preference pairs (approved + training_ready only) | eval prompts
```

The automated validators never *approve* anything — they only reject or
flag. Approval is a human decision recorded in the review log. LLM-critic
scores (optional) are stored as advisory metadata.

## 5. Evaluation

* **Cases are authored separately** from training examples (different goals,
  different wording); `split` refuses to build a release if a training input
  is a near-duplicate of an evaluation input.
* Each case carries **machine-checkable assertions** (`checks`) tagged with a
  metric and one of 12 dimensions, plus human-review focus points.
* Metrics are reported **per metric and per dimension**. There is
  deliberately no single overall score.
* The runner is predictor-agnostic: `reference` (sanity: must score 100%),
  `naive` (a schema-valid but behaviourally poor baseline: proves the checks
  discriminate) and `model` (any provider via the same prompt as SFT export).
* Human review of model outputs uses a separate rubric and a separate report.

## 6. Code layout

| Path | Role |
|---|---|
| `schemas/` | JSON Schema 2020-12, single source of truth |
| `gjcore/` | shared utilities: paths, IO, schema registry, config, env, hashing |
| `generation/validators/` | schema + semantic + quality + dedup + leakage checks |
| `generation/generators/` | LLM providers, prompt rendering, candidate generation |
| `generation/pipelines/` | validate, stats, coverage, review, split, export |
| `evaluation/metrics/` | check implementations and metric aggregation |
| `evaluation/runners/` | predictors and the evaluation runner |
| `prompts/` | versioned prompts: `navigator/` (runtime model) and `generation/` (teacher) |
| `configs/` | versions, dataset, generation, evaluation, export, coverage targets |
| `scripts/gj.py` | the single CLI entry point |

Dependencies are deliberately minimal (`jsonschema`, `referencing`, `PyYAML`, `pytest`). LLM
providers sit behind one interface: the Anthropic teacher is called through the official
`anthropic` SDK (optional dependency, only needed for generation); open-weight models — including
the fine-tuned navigator under evaluation — are reached through any OpenAI-compatible endpoint;
a replay provider covers offline tests.

## 7. Known limitations accepted for v0.1

* The target model is text-only. Photo/audio/video evidence reaches it as a
  textual description (user caption or upstream captioner), and the dataset
  models that explicitly (`evidence.description_source`).
* Language checks are script-based heuristics (Cyrillic vs Latin ratio); they
  catch wrong-language answers, not bad style — style is a human-review item.
* Semantic lint cannot judge "is this plan generic?". Those failure modes are
  marked *human-only* in the failure-mode catalogue.
