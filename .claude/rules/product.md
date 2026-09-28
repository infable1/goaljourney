---
paths:
  - "prompts/navigator/**"
  - "configs/product_capabilities.yaml"
  - "configs/evidence_policy.yaml"
  - "docs/POLICY_DECISIONS*.md"
  - "docs/DECISIONS.md"
---
# Product semantics and policies

These files define what the navigator may do. `docs/DECISIONS.md` holds the durable decisions;
`docs/POLICY_DECISIONS_v0.1.1.md` holds the full policies POL-A…F with their validator codes.

## Changing a policy or a capability

- A policy change is a product decision. Draft it and mark it *adopted*, pending product-owner
  confirmation. Then:
  - add or supersede a `D-NNN` entry in `docs/DECISIONS.md` (never delete entries);
  - update the POLICY document of the new version.
- Training data is judged by the rules of its own `schema_version`. A policy that changes the
  expected behaviour needs:
  - a new `schema_version` or dataset version;
  - version-gated lint (`c.since("x.y.z")` in `generation/validators/semantic.py`);
  - ledger entries for every example it changes.
- **Capabilities** (`configs/product_capabilities.yaml`):
  - a capability moves to `available` only when the product ships it;
  - examples that use it are *added* in a new dataset version, and old ones are not rewritten
    silently;
  - `planned` means representable in the schemas but never required by training data;
  - `unsupported` means never promised.
- **Evidence classes** (`configs/evidence_policy.yaml`): a ceiling may only be raised with a written
  rationale in the policy doc. Confidence must never exceed what the class supports.

## Navigator prompt (`prompts/navigator/v<ver>/system.md`)

- A prompt change is a new version directory plus a bump of `navigator_prompt_version`. Never edit a
  released version in place.
- SFT export and evaluation must use the same prompt (`gjcore/prompting.py`,
  `configs/export.yaml`, `configs/evaluation.yaml`). Change them together.
- The prompt restates the principles; it does not add capabilities the registry lacks.

## Invariants to keep

- The user controls the Journey. Autonomy is `auto` for task dates, `adapt_with_summary` for
  milestone dates and `confirm_required` for goal dates.
- A photo alone never verifies. Self-report is capped at *limited*. Insufficient evidence leads to
  `needs_more_evidence`.
- Levels follow verified milestones, never activity. The navigator is not a general assistant.
- Russian output uses no gendered self-reference and no gendered address to the user.
