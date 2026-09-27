# review/

Human review of the training data. Workflow: [`docs/HUMAN_REVIEW_GUIDE.md`](../docs/HUMAN_REVIEW_GUIDE.md).

| File | What it is | Written by |
|---|---|---|
| `reviewers.yaml` | registry of people allowed to record decisions (id, roles, languages, expert domains) | reviewers, by hand |
| `review_manifest_v0.1.0.json` | deterministic 30-item review sample (strata, coverage, calibration items, stable `rv-0.1.0-NN` ids). Frozen once reviews reference it | `gj review sample --write` |
| `known_issues_v0.1.0.yaml` | issues found by inspecting v0.1.0, each with a *proposed* revision; nothing is applied until a reviewer confirms it | inspection (agent); updated by reviewers |
| `audit_findings_v0.1.0.json` | heuristic audit findings (Problems 1–9 + temporal) plus the known issues; review aids, not verdicts | `gj audit --write` |

Decisions themselves live in `data/reviewed/review_events.jsonl` (append-only, hash-chained) and
the reviewed content in `data/reviewed/snapshots/`. Neither exists until the first human decision is
recorded. **No example has been reviewed yet.**
