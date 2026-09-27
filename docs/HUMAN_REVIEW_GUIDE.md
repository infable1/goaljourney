# Human review guide — GoalJourney dataset

Every review question comes down to one test:

> **Would we be comfortable teaching a model this behaviour?**

A 4B model learns from each example as a demonstration. It cannot tell a slightly wrong date, a
gendered form of address or an invented fact from the parts we meant it to learn. Review each example
as if it were the only one the model will ever see for that situation.

The examples were written by an AI agent. They pass every automated check, and they still contain
errors (see [`DATASET_AUDIT_v0.1.0.md`](DATASET_AUDIT_v0.1.0.md)). **Passing validation is not evidence
of quality.** Your judgement is the quality gate.

## 1. Before you start

1. Add yourself to [`review/reviewers.yaml`](../review/reviewers.yaml): a stable pseudonymous `id`,
   `roles`, the `languages` you can judge natively or near-natively, `expert_domains` only if you are
   professionally qualified, and `human: true`. Automated agents cannot record decisions.
2. Read the rubric ([`evaluation/rubrics/dataset_review_rubric.yaml`](../evaluation/rubrics/dataset_review_rubric.yaml))
   and this guide.
3. Skim [`DATASET_SPEC.md`](../DATASET_SPEC.md) §5–§12 (operations, journey grammar, verification,
   research, safety, memory, language). The rubric assumes those rules.

## 2. Roles and qualifications

| Role | Can do | Notes |
|---|---|---|
| `dataset_reviewer` | approve, revise or reject examples in the languages they list | Russian and mixed-input examples need a reviewer who reads Russian; mixed input needs both languages |
| `domain_expert` | the same, and signs off expert-tier examples in their `expert_domains` | expert-tier examples stay `approved_pending_expert` until approvals cover every required domain |
| `adjudicator` | resolves disagreements; their latest decision on a content version is final | use sparingly, and write the reasoning in `notes` |

**Expert tier** means a non-`allowed` safety category or an explicit risk tag, which covers 10
examples in v0.1.0. The required domains are shown by `gj review show` and `gj review list`: medical,
mental_health, legal, financial, physical_safety, privacy or safety_policy.

## 3. What automation decides, and what it cannot

| Class | Properties | Who decides |
|---|---|---|
| **automatically validatable** | schema validity; ids and references; dependency DAG and order; dates vs `today` and the deadline; daily time budget; photo-only proof; self-report confidence ceiling; verification status vs criteria; exposed reasoning; response language (script); `must_not_mention` memory leaks; rejected outputs in the 14 auto-detectable failure modes | `gj validate` — if it fails, fix the example; you still judge everything else |
| **flagged by heuristics, decided by you** | vague titles (incl. outline nodes); user-entered data rated as objective; product-capability assumptions; too many questions; unsupported feasibility claims; capacity mismatch; milestone-date changes without consent; unsupported generalisations; quantities not in the input; retrieved-memory leaks; Russian gendered forms; weekday/date mismatches | `gj audit` shows candidates; a heuristic hit is a question, not a verdict |
| **human review required** | usefulness; goal understanding (no invented facts); question minimality; actionability; realism and arithmetic; verification fit; evidence interpretation; user agency; adaptation proportionality; explanation quality; natural language and gender neutrality; contrastive plausibility and tagging; the 16 human-only failure modes | you |
| **expert review required** | medical, mental-health, legal, financial, physical-safety and privacy content of expert-tier examples; any health claim | a qualified `domain_expert` |

No example is ever approved automatically, whatever its tier.

## 4. The review sample

[`review/review_manifest_v0.1.0.json`](../review/review_manifest_v0.1.0.json) is a deterministic sample
of 30 examples. At sampling time, `gj review sample --check` proves it regenerates identically. The
manifest is then frozen: later edits to examples do not re-sample, and `gj review list --manifest` marks
items whose content changed since sampling. Each item has a stable id `rv-0.1.0-NN`.

| Stratum | Share | Why |
|---|---|---|
| random | 40% (12) | Drawn **first** from the whole pool with a fixed seed, so it is an unbiased picture of an ordinary example. Your problem rate here estimates the pool's (roughly: ±25 points at n=12). |
| highest_risk | 30% (9) | Highest risk score (audit findings, known issues, expert tier, difficulty, mixed input). Finds the worst problems fast. |
| contrastive | 20% (6) | Examples with rejected outputs, covering as many failure modes as possible. Rejected outputs become preference pairs, so their labels must be right. |
| edge | 10% (3) | Rare situations (mixed language, memory isolation, retries, tiny goals, restricted safety, rare operations). |

The split is 40% random because a review that only looks where problems are expected cannot tell
you how good the dataset is, and the random draw is the only unbiased estimate we get. The targeted
60% then spends effort where a defect is most likely or most costly. Coverage repair ensures every
operation, behaviour family, both languages, mixed input, rejected outputs and at least 3 expert-tier
examples appear. Repairs never touch the random stratum, and each is recorded in the manifest.

**Calibration items** (8, marked `*` in `gj review list --manifest`): every reviewer reviews these
**first and independently**. The agreement on them (§9) is a release gate. They are chosen for
diversity: at least 3 RU, at least 3 EN, mixed input, 2 expert-tier, rejected outputs, and distinct
operations.

## 5. Independence: rate first, then look

By default, `gj review show` hides the author's notes, validator results and audit findings. Heuristic
flags anchor judgement: a reviewer who sees "no findings" relaxes, and one who sees a flag stops
looking elsewhere.

1. Read the example (`gj review show ID`).
2. Fill the rubric (`gj review template ID --out my/ID.yaml`).
3. Then look at the automated side (`gj review show ID --show-automated`). If it shows something you
   missed, change your rating and set `independent_rating: false` in the decision file.
4. Approving an example with an open **high-severity** finding or known issue requires
   `--acknowledge-findings`. The acknowledged ids are logged, and a release gate checks them.

## 6. Workflow

```bash
python3 scripts/gj.py review list --manifest                 # the sample, with required qualifications
python3 scripts/gj.py review show gj-nav-006                 # read (automated findings hidden)
python3 scripts/gj.py review template gj-nav-006 --out reviews/me/gj-nav-006.yaml
#   fill: action, overall, ratings for every listed criterion, issues, notes
python3 scripts/gj.py review revise gj-nav-006 --reviewer me --from reviews/me/gj-nav-006.yaml
python3 scripts/gj.py review show gj-nav-006 --show-automated   # compare with the machine view
python3 scripts/gj.py review history gj-nav-006              # all decisions + diffs between versions
python3 scripts/gj.py review stats                           # progress, agreement, pipeline funnel
python3 scripts/gj.py review verify-log                      # integrity of the log
```

Batch alternative: run `gj review export --format sheet --manifest --out sheet.yaml`, fill the sheet,
then `gj review apply sheet.yaml --reviewer me`. For reading on paper or in a browser, use
`gj review export --format md --manifest --out packet.md`. The packet excludes automated findings
unless you pass `--with-automated`.

Quick flags work too:
`gj review approve ID --reviewer me --rate product_usefulness=good … --overall acceptable --notes "…"`.
Issues use the form `--issue "realism:major:5 Oct 2026 is a Monday:use «в понедельник, 5-го»"`.

## 7. The rubric (A–Q)

Rate every applicable criterion with one of: `good`, `minor_issues`, `major_issues`, `unacceptable`
or `not_applicable`. Then give an **overall** verdict: `excellent`, `acceptable`, `needs_revision` or
`incorrect`. There is deliberately **no score and no average**: one `unacceptable` on safety is not
offset by fine writing.

| Code | Criterion | Look for (real examples from v0.1.0) |
|---|---|---|
| A | product usefulness | Would a real user be glad to get this now? Generic advice, wrong focus. |
| B | goal understanding | Uses every known fact and **invents none**. `gj-nav-001` states a niche the user never gave. |
| C | question minimality | Every question changes the route; nothing re-asked; nothing critical skipped. `gj-goalchg-001` asserts a date works without asking the user's pace. |
| D | actionability | Object + quantity/artefact + a clear next step. "Learn X" and "research Y" are failures. |
| E | realism | **Recompute the arithmetic, and check dates and weekdays against `today`.** `gj-time-001` claims 140 h where the tasks add up to 115 h; `gj-nav-006` calls 5 October 2026 a Sunday when it is a Monday. |
| F | dependency correctness | Real prerequisites only; parallel work stays parallel; nothing unlocks before its prerequisite. |
| G | verification quality | Method fits the task; photos only in combination; self-report labelled `limited`; user-entered tables are not "objective"; no reliance on capabilities the product may not have (auto transcription, URL fetching, issuing scrambles). |
| H | evidence interpretation | Each criterion judged on specific evidence; insufficient evidence → a specific request, not a rejection; no unreasonable proof demands. |
| I | user agency | Explains, offers options, **asks before significant changes, including dates**; respects the user's decision; does not say "I've changed" while confirmation is pending. |
| J | adaptation quality | Proportionate change; verified progress kept and reused; knock-on effects on milestones stated. |
| K | explanation quality | Short, specific, honest. No filler, no hidden reasoning, no overclaiming ("exactly what hiring managers look for"). |
| L | external-fact discipline **(hard gate)** | Current or local facts come only from the provided research, or are marked for verification. Confident generalisations count as a major issue. |
| M | safety **(hard gate)** | Right category, role and referral; no prescriptions; harmless goals not hedged. |
| N | language quality | Natural, correct register («вы»), **gender-neutral about the user and the assistant** (§8). |
| P | contrastive quality | Each rejected output is a realistic mistake, clearly worse, and carries exactly its tagged failures, with no untagged extra defects. |
| Q | privacy and memory | Right memory layer; nothing about third parties; unrelated memory never surfaces. |

Hard gates (L, M) must be `good` or `not_applicable` for an approval; `minor_issues` is not enough there.

## 8. Russian: gender neutrality and naturalness

The user's gender is never known, and the assistant has none.

| Wrong | Why | Neutral alternative |
|---|---|---|
| «Подготовку разбил на 4 задачи» | assistant's self-reference is masculine | «Подготовка разбита на 4 задачи» / «Разбиваю подготовку на…» |
| «я уже всё проверил» | the same | «всё уже проверено» |
| «едете ли вы один?» | «один/одна» after «вы» reveals gender | «планируете переезд в одиночку или с семьёй?» |
| «Вы готов?» / «Вы уверена?» | singular short forms after «вы» | «Вы готовы?», «Вы уверены?» (plural short forms are neutral) |
| level «Уверенный нарезчик», «Хозяин ужина» | an identity label with grammatical gender | name the stage, not the person: «Уверенная нарезка», «Ужин для друзей» (a policy decision is pending; flag every case) |
| memory «свободен по выходным» | stored facts about the user in a gendered form | «выходные свободны» |

Also check register («вы», never «ты»), calques from English, product vocabulary (маршрут, участок,
веха) used consistently, and whether a native speaker would say it that way. Users write in gendered
forms themselves («я прочитал»), which is fine in the input. The output must still not mirror it
(«вы прочитали» is plural and neutral).

## 9. Decisions, disagreement and calibration

* **approve**: overall `excellent` or `acceptable`; no `major_issues` or `unacceptable`; hard gates
  `good` or n/a; every applicable criterion rated.
* **revise**: the idea is right but something must change. Give at least one issue with
  `criterion`, `severity` (minor, major or critical), `description` and ideally `proposed_fix`.
* **reject**: it teaches the wrong behaviour or cannot be fixed in place. A note is required.
* With several reviewers, **the most conservative decision wins** (reject > revise > approve) until an
  adjudicator decides.
* `gj review stats` reports per-pair agreement on the decision and on the overall verdict, with
  Cohen's kappa, criterion-level exact agreement, and how often reviewers disagree on whether an
  issue is severe. Release gate: on the calibration items, every reviewer pair agrees on at least 75%
  of decisions with kappa ≥ 0.40 (rationale in `configs/release_gates.yaml`). With only 8 items this
  detects a rubric that people read differently; it does not certify reliability. When reviewers
  disagree, **discuss the item, write down the resolution, and clarify the rubric anchor.** Do not
  just re-vote.

## 10. Revisions and history

* Decisions apply to **exact content** (a SHA-256 of task type, input, expected output and rejected
  outputs). Editing an example makes its status `stale`, and it must be reviewed again. Metadata
  edits (tags, notes) do not invalidate reviews.
* The reviewed content is preserved in `data/reviewed/snapshots/<hash>.json`, written once and never
  overwritten. `gj review history ID` shows every decision and a diff between reviewed versions and
  the current content.
* **Never rewrite an example silently.** The flow is: record `revise` with the issue and proposed fix
  → edit the YAML → `gj validate` → `gj audit --write` (the committed findings file must match the data;
  a test checks it) → review again. Update the known-issues register (`status: fixed`,
  `resolution`). Bump `dataset_version` before building a release with the new content; releases are
  immutable.
* The known-issues register is a list of *proposed* revisions from inspection. Confirm an issue with
  `gj review revise`, or mark it `disputed` or `wont_fix` with a reason.

## 11. Integrity

* `data/reviewed/review_events.jsonl` is append-only and hash-chained. **Never edit or delete a line.**
  To change your mind, record a new decision; the latest decision per reviewer counts.
  `gj review verify-log` detects edits, deletions and reordering, and a test enforces it.
* Append on one branch at a time. Merging two branches that both appended is detected as a fork
  (a warning, order kept). It is not tampering, but it should be rare.
* Your registry entry (roles, languages, expert domains) is copied into each event, so later registry
  edits never change past decisions.

## 12. Effort

Expect 10–20 minutes per example for a careful first pass (longer for journeys and route adaptations),
5–10 minutes once calibrated. The 30-item sample is roughly one working day per reviewer. The 8
calibration items plus the discussion afterwards take about half a day.

## 13. Do not

* Approve because validation passed, or because the example "looks like the others".
* Look at automated findings before rating (then say so if you did).
* Fix an example in place without recording a `revise` decision.
* Approve outside your languages or expertise; ask for an expert instead.
* Edit `review_events.jsonl` or the snapshots by hand.
