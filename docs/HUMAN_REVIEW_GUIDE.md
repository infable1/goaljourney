# Human review guide — GoalJourney dataset

Every review question comes down to one test:

> **Would we be comfortable teaching a model this behaviour?**

A 4B model learns from each example as a demonstration. It cannot tell a slightly wrong date, a
gendered form of address or an invented fact from the parts we meant it to learn. Review each example
as if it were the only one the model will ever see for that situation.

The examples were written by an AI agent. They pass every automated check, and they still contain
errors (see [`DATASET_AUDIT_v0.1.0.md`](DATASET_AUDIT_v0.1.0.md) and, for the v0.1.1 revisions,
[`DATASET_AUDIT_v0.1.1.md`](DATASET_AUDIT_v0.1.1.md)). **Passing validation is not evidence of
quality.** Your judgement is the quality gate. The policies you review against — capabilities,
confidence semantics, deadline autonomy, Russian voice, fact provenance — are in
[`POLICY_DECISIONS_v0.1.1.md`](POLICY_DECISIONS_v0.1.1.md).

## Review governance: solo owner first (D-026)

The dataset is reviewed by **one accountable human owner**, helped by an **AI review copilot**, with a
**qualified external expert** only where an expert-tier example needs one
(`configs/review.yaml` → `governance.mode: solo_owner`).

> The project needs rigorous human judgement, not bureaucratic multiplication of humans.
> AI can be a reviewer coach, but the human remains the accountable decision-maker.
> Expert qualification is a real-world requirement, not something the software or AI can simulate.

```text
                 ┌──────────────────────┐
                 │   AI review copilot   │   explains, challenges, recalculates, compares readings (§14)
                 └──────────┬───────────┘   never decides, never approves, is never an expert
                            ▼
┌──────────────┐     ┌───────────────┐
│ Dataset item │ ──▶ │  Human owner  │ ──▶ approve / revise / reject   (latest decision on the content is final)
└──────────────┘     └───────┬───────┘
                   ordinary  │  expert-tier
                     item ◀──┴──▶ item: a qualified human domain expert signs off (the owner only if qualified);
                  human final     without one it stays `pending / awaiting_expert` and never enters training (§16)
```

* No second reviewer, reviewer-diversity check, adjudicator or pairwise calibration is required. The
  release gates `reviewer_diversity` and `calibration_agreement` are reported **N/A** in this mode, never
  as passed.
* Nothing about quality changes: the rubric A–Q, the hard gates L and M, exact content-hash binding,
  immutable snapshots, the append-only history, re-review after any edit, independence from automated
  findings and expert sign-off all apply exactly as before.
* Decisions recorded by several reviewers earlier (the 2026-09-28/29 calibration round) keep their
  meaning: on that content version every reviewer's latest decision still counts.
* A second reviewer can be added later; see §17.

## 1. Before you start

1. Add yourself to [`review/reviewers.yaml`](../review/reviewers.yaml): a stable pseudonymous `id`,
   `roles`, the `languages` you can judge natively or near-natively, `expert_domains` only if you are
   professionally qualified, and `human: true`. In solo_owner mode one entry — the owner — is enough.
   Automated agents, including the AI copilot, are never registered and cannot record decisions.
2. Read the rubric ([`evaluation/rubrics/dataset_review_rubric_v0.2.1.yaml`](../evaluation/rubrics/dataset_review_rubric_v0.2.1.yaml))
   and this guide.
3. Skim [`DATASET_SPEC.md`](../DATASET_SPEC.md) §5–§12 (operations, journey grammar, verification,
   research, safety, memory, language). The rubric assumes those rules.

## 2. Roles and qualifications

| Role | Can do | Notes |
|---|---|---|
| `dataset_reviewer` | approve, revise or reject examples in the languages they list | the owner, in solo_owner mode. Russian and mixed-input examples need a reviewer who reads Russian; mixed input needs both languages |
| `domain_expert` | the same, and signs off expert-tier examples in their `expert_domains` | a professionally qualified human only — the owner if genuinely qualified, otherwise an external expert; never an AI, never self-study. Expert-tier examples stay `pending` (detail `awaiting_expert`) until approvals cover every required domain |
| `adjudicator` | resolves disagreements; their latest decision on a content version is final | multi_reviewer mode only (§17); not used in solo_owner mode. Use sparingly, and write the reasoning in `notes` |

**Expert tier** means a non-`allowed` safety category or an explicit risk tag, which covers 10
examples in v0.1.0. The required domains are shown by `gj review show` and `gj review list`: medical,
mental_health, legal, financial, physical_safety, privacy or safety_policy.

## 3. What automation decides, and what it cannot

| Class | Properties | Who decides |
|---|---|---|
| **automatically validatable** | schema validity; ids and references; dependency DAG and order; dates vs `today` and the deadline; daily time budget; photo-only proof; self-report confidence ceiling; verification status vs criteria; exposed reasoning; response language (script); `must_not_mention` memory leaks; rejected outputs in the auto-detectable failure modes. **Since v0.1.1:** weekday vs date; hour/week arithmetic in the plan *and in the message text*; deadline autonomy (task auto / milestone with summary / goal only proposed); capabilities (no video, no reminders, no API calls); confidence ceilings by evidence class; recorded contradictions; `facts_used` provenance; Russian gendered self-reference, address and memory | `gj validate` — if it fails, fix the example; you still judge everything else |
| **flagged by heuristics, decided by you** | vague titles (incl. outline nodes); user-entered data rated as objective; product-capability assumptions; too many questions; unsupported feasibility claims; capacity mismatch; milestone-date changes without consent; unsupported generalisations; quantities not in the input; retrieved-memory leaks; Russian gendered forms; weekday/date mismatches | `gj audit` shows candidates; a heuristic hit is a question, not a verdict |
| **human review required** | usefulness; goal understanding (no invented facts); question minimality; actionability; realism and arithmetic; verification fit; evidence interpretation; user agency; adaptation proportionality; explanation quality; natural language and gender neutrality; contrastive plausibility and tagging; the 16 human-only failure modes | you |
| **expert review required** | medical, mental-health, legal, financial, physical-safety and privacy content of expert-tier examples; any health claim | a qualified `domain_expert` |

No example is ever approved automatically, whatever its tier.

## 4. The review sample

[`review/review_manifest_v0.1.0.json`](../review/review_manifest_v0.1.0.json) is a deterministic sample
of 30 examples. `gj review sample --check` proves it regenerates identically from its frozen inputs.
The manifest is frozen: later edits to examples do not re-sample. Each item has a stable id
`rv-0.1.0-NN`.

Dataset v0.1.1 keeps this sample (`configs/review.yaml` `sampling.sample_version`).
[`review/review_sample_status_v0.1.1.json`](../review/review_sample_status_v0.1.1.json)
(`gj review sample-status`) shows, per item:

* whether the content changed since sampling, and which revision (`REV-0.1.1-NNN`) changed it;
* the known issues that name the example;
* the current human status.

12 of the 30 items changed in v0.1.1, including 2 calibration items. Rate the **current** content.
The ledger entry (`gj revisions diff ID`) shows what changed and why; read it only after your
independent rating.

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

**Calibration items** (8, marked `*` in `gj review list --manifest`), chosen for diversity: at least 3
RU, at least 3 EN, mixed input, 2 expert-tier, rejected outputs, and distinct operations. In solo_owner
mode they are ordinary sample items that are worth reviewing first. In multi_reviewer mode every
reviewer reviews them first and independently, and their agreement is a release gate (§17). The
historical double reviews of these items are kept.

## 5. Independence: rate first, then look

By default, `gj review show` hides the author's notes, validator results and audit findings. Heuristic
flags anchor judgement: a reviewer who sees "no findings" relaxes, and one who sees a flag stops
looking elsewhere.

1. Read the example (`gj review show ID`).
2. Fill the rubric (`gj review template ID --out my/ID.yaml`).
3. Then look at the automated side (`gj review show ID --show-automated`) and, if you want, ask the AI
   copilot for a critique (§14). If either makes you change a rating, record it with
   `independent_rating: false` in the decision file (or `--independent-rating no` with quick flags).
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
python3 scripts/gj.py review stats                           # mode, human-reviewed / training-eligible, funnel
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
| M | safety **(hard gate)** | Right category, role and referral; no prescriptions; harmless goals not hedged. For a `restricted` goal the refusal stops planning or advancing the prohibited activity; a lawful alternative (or a next step for it) may still be offered and is not unsafe continuation unless it materially facilitates the prohibited activity. `proceed_with_journey: false` concerns the original restricted goal (rubric 0.2.1). |
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
* **One reviewer (solo_owner mode):** your latest decision on a content version is final. To change
  your mind, record a new decision and say why in `notes` (§11). There is nobody to adjudicate and no
  self-agreement to measure. If unsure, use §15.
* **Several reviewers** (historical decisions, or multi_reviewer mode): every reviewer's latest decision
  counts and **the most conservative decision wins** (reject > revise > approve) until an adjudicator
  decides. Agreement, calibration and disagreement handling are in §17.

## 10. Revisions and history

* Decisions apply to **exact content** (a SHA-256 of task type, input, expected output and rejected
  outputs). Editing an example returns it to `pending` (detail `content_changed`), and it must be
  reviewed again. Metadata edits (tags, notes) do not invalidate reviews.
* **Statuses** (canonical, derived from the log):

  | Status | Detail |
  |---|---|
  | `pending` | `not_reviewed`, `content_changed` or `awaiting_expert` |
  | `approved` | `decided` |
  | `needs_revision` | `decided` |
  | `rejected` | `decided` |

  Only `approved` content can reach a training file.
* The reviewed content is preserved in `data/reviewed/snapshots/<hash>.json`, written once and never
  overwritten. `gj review history ID` shows every decision and a diff between reviewed versions and
  the current content.
* **Never rewrite an example silently.** The flow is:
  1. record `revise` with the issue and proposed fix;
  2. edit the YAML;
  3. add a ledger entry to `data/revisions/v<ver>.yaml` (defect, correction, rationale, known issues,
     policies), then run `gj revisions sync` and `gj revisions check`;
  4. `gj validate`;
  5. `gj audit --write` and `gj review sample-status --write` (committed files must match; tests check
     it);
  6. review again.

  Update the known-issues register (`status: fixed_pending_review`, `resolution`). A ledger entry's
  `reviewer_status` is a human decision; it stays `pending_human_review` until you record one. Bump
  `dataset_version` before building a release with the new content; releases are immutable, and
  `gj split` refuses a version whose ledger is incomplete.
* **Reviewing a ledger entry** (`gj revisions diff EXAMPLE` shows the defect, correction and
  field-level diff). Decide whether the correction fixes the stated defect without new problems, then
  record it (D-027):

  ```
  gj revisions review REV-0.1.1-001 --reviewer <you> --status confirmed|disputed \
      --independent-rating yes|no --notes "<decision and reason>"
  ```

  The decision is bound to the entry's content hash. Use `--independent-rating no` if you changed it
  after automated findings or AI critique (§5, §14). A second decision on the same entry needs
  `--replace`. `disputed` does not fix anything: the fix goes through a new `dataset_version` and
  ledger entry. A ledger decision does not change the example's own review status; rate the example
  with `gj review` for that.
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
5–10 minutes with practice. The 30-item sample is roughly one working day.

## 13. Do not

* Approve because validation passed, or because the example "looks like the others".
* Look at automated findings before rating (then say so if you did).
* Fix an example in place without recording a `revise` decision.
* Approve outside your languages or expertise; ask for an expert instead.
* Edit `review_events.jsonl` or the snapshots by hand.
* Let the AI copilot choose, record or phrase your decision as if it were yours; count its output as expert
  sign-off; or approve an uncertain item because the copilot's answer sounds plausible (§14, §15).
* Register a second identity for yourself, or an expert domain you are not professionally qualified in, to
  make a gate or a status move.

## 14. AI review copilot

The copilot (an AI assistant such as Claude Code, working in this repository) helps you judge; it never
judges for you.

| The copilot may | The copilot may not |
|---|---|
| explain any rubric criterion and why it may or may not apply | record, apply or "confirm" a decision, or impersonate a reviewer |
| point out contradictions, unsupported factual claims and provenance gaps | count as a human approval or as a domain expert |
| recalculate arithmetic, check dates and weekdays against `today`, inspect dependency order | create or imply professional qualification |
| point out possible safety, privacy, memory or Russian-voice problems | change your rating or decision, silently or otherwise |
| compare two plausible readings of the rubric and explain minor vs major | turn an uncertain answer into an approval because it sounds plausible |
| suggest questions to reconsider, and explain what approve / revise / reject would lead to | register reviewers or expert domains on its own initiative |
| dry-check a filled decision file against the decision rules (nothing is recorded) | see your ratings before you have recorded them, if you want an independent first pass |

The software enforces the hard part: only a registered `human: true` reviewer can record a decision,
only approvals by human `domain_expert`s cover expert domains, and a dry check writes nothing
(`tests/test_solo_review.py`).

**Order of work** (keeps your first rating independent, §5):

1. Read the item.
2. Rate it and write down your initial decision (the decision file, or notes).
3. Only then look at automated findings and ask the copilot for a critique.
4. Reconsider.
5. If you change a rating because of that assistance, record it with `independent_rating: false`
   (`--independent-rating no`), and say in `notes` what changed and why.
6. Record your final decision yourself, or explicitly ask the agent to record exactly the ratings,
   decision and notes you gave it, under your own reviewer id. The agent never fills gaps.

**Asking for clarification.** Useful prompts: "Explain criterion E for this item and where the arithmetic
is", "Is anything in this answer a current external fact without a source?", "Give me the strongest case
for major and for minor on K, with evidence from the item", "Which rubric anchor decides this?".

## 15. When you are unsure

There is no "uncertain" verdict. Uncertainty is resolved by reasoning, and the reasoning is recorded.

```text
You:      "I am unsure whether this is a major issue or acceptable."
Copilot:  points to the rubric anchor; names the competing interpretations; quotes the evidence in the
          item; says what would make each interpretation correct — and does not choose.
You:      choose the rating and decision, and write the reasoning in notes, e.g.
          "Unsure between minor and major on L; chose major because the claim is jurisdiction-specific
           and unsourced. Copilot consulted after my initial rating (independent_rating: false)."
```

If you still cannot decide, `revise` with an issue that states the doubt is the safe choice: the item
stays out of training until its content or your judgement settles. For expert-tier content the doubt
is not yours to settle: leave it to a qualified expert (§16).

## 16. Expert-tier items and training eligibility

Expert-tier examples (§2) need sign-off from a qualified human `domain_expert` for every required
domain, in every governance mode.

* **You are genuinely qualified** in the required domain: hold the `domain_expert` role with that
  domain in `review/reviewers.yaml`, under the same qualification standard as always. Your approval then
  covers it.
* **You are not qualified:** review the item normally — your decision still counts as the human review —
  but do not add the domain to your entry. The item stays `pending / awaiting_expert`, lists the missing
  domains, and is **not training-eligible** until a qualified expert approves it. It does not block your
  review of anything else. Self-study and AI assistance are not a qualification.

Review states, per exact content version (`review_store.training_eligibility`, `gj review stats`):

| State | Meaning |
|---|---|
| human-reviewed | a human decision exists on the current content |
| expert-reviewed | no expert domain is required, or qualified human experts cover every required domain |
| training-eligible | the current content is `approved`: human approval, expert coverage, no open objection |
| not training-eligible | with a reason: `not_reviewed`, `content_changed`, `awaiting_expert` (with the missing domains), `needs_revision` or `rejected` |
| training-ready release | every training row is eligible and every applicable release gate passes (`gj gates`) |

Every release manifest (`gj split`) records `review_mode` and a `training_eligibility` section that
lists **every** pool example that is not training-eligible, with its reason, missing expert domains and
whether it is in the release as a draft row. `require_approved` releases leave such rows out;
`allow_pending` drafts may carry them, clearly marked. `gj export` writes only `approved` rows to
training formats, and only for a release whose applicable gates all pass. Nothing is dropped silently.

## 17. Multi-reviewer mode (compatibility)

Set `governance.mode: multi_reviewer` when there really are several independent reviewers. Then:

* **Calibration becomes meaningful.** Every reviewer rates the 8 calibration items first and
  independently. The `calibration_agreement` gate requires every reviewer pair with at least 8 shared
  items (same content versions) to agree on at least 75% of decisions with kappa ≥ 0.40. With 8 items
  this detects a rubric that people read differently; it does not certify reliability.
* **Reviewer diversity becomes meaningful.** The `reviewer_diversity` gate requires at least two
  approving reviewers, with no one above 80% of the approved rows.
* **Adjudication is available.** An `adjudicator`'s latest decision on a content version overrides
  everyone. Roles are copied into each event, so any event recorded under an entry that includes
  `adjudicator` is decisive; grant the role for adjudication, not for routine review.
* **Disagreements:** discuss the item, write down the resolution, and clarify the rubric anchor. Do
  not just re-vote. `gj review stats` reports per-pair agreement on decisions and overall verdicts
  (Cohen's kappa, criterion-level agreement, severity disagreement).

Switching modes never rewrites the review log; it changes which gates apply.
