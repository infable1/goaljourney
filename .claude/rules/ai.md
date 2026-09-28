---
paths:
  - "prompts/**"
  - "generation/generators/**"
  - "gjcore/prompting.py"
  - "evaluation/runners/**"
  - "configs/generation.yaml"
  - "configs/evaluation.yaml"
  - "configs/export.yaml"
---
# Models, providers and prompts

## Replaceability (D-012)

- **Providers.** Every LLM call goes through `generation/generators/providers.py`: Anthropic via the
  official SDK, any OpenAI-compatible endpoint, or offline replay. Don't call a vendor API anywhere
  else, and don't add a vendor-specific code path to pipelines.
- **Model ids** live in configs or come from CLI flags (`--provider`, `--model`). Never hard-code
  them in code or prompts. The navigator's base model stays `null` in `configs/versions.yaml` until
  it is chosen.
- **SFT export** stays chat-template-agnostic: `{"messages": [system, user, assistant]}`. The
  training framework applies the template.

## Two kinds of prompt

| Kind | Location | Governs |
|---|---|---|
| Navigator runtime prompt | `prompts/navigator/v<ver>/system.md` | What the trained model sees. The eval runner must prompt the model exactly as the SFT export does (`gjcore/prompting.py`) |
| Teacher (generation) prompts | `prompts/generation/v<ver>/` | Stage 1 input, stage 2 ideal output, stage 3 rejected output; operation guides and the failure-mode catalogue |

- A change to either kind is a new version directory plus a bump in `configs/versions.yaml`.
  Released versions are never edited in place.
- The teacher prompt must carry the current policies. A policy change without a teacher-prompt
  update yields off-policy candidates.

## Generation safety valves

- Keep the per-run cap (`configs/generation.yaml`, 50 candidates). Every batch must be reviewable by
  humans, so never raise the cap to push volume.
- `--dry-run` renders prompts without credentials. Use it before any paid run.
- Every run writes a manifest: provider, model, prompt file hashes and a config snapshot. Don't
  bypass it.
- Candidates are never approved automatically, and never enter a release without human approval.

## Evaluation runner

- Predictors are `reference` (must pass everything), `naive` (must fail) and `model`.
- A new check or metric must discriminate: the naive baseline should fail it.
- Human scores are never merged into automated metrics.
