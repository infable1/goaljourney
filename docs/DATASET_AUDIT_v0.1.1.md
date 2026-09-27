# Dataset audit — GoalJourney v0.1.1

*Milestone 1.6 "Dataset Calibration" · 2026-09-27 · dataset v0.1.1 (93 training examples), schema v0.1.1,
evaluation v0.2.0 (63 cases, 106 model calls)*

> **Who wrote this audit.** The AI agent that authored v0.1.0 made the v0.1.1 revisions, wrote the
> new validators and evaluation cases, and wrote this audit. It is not a human review. No example
> was approved, rejected or marked reviewed. Every revision is recorded as *pending human review*.
> Automated validation passing is not a review.

Reproduce every number:

```bash
make check
gj revisions check
gj audit
gj leakage --distribution
gj review sample-status
gj gates
gj eval run --predictor reference|naive
```

## 1. Summary

* **v0.1.0 is untouched.** Its release files, manifest, review manifest, known issues, audit report,
  evaluation cases, leakage metadata and schemas are byte-identical to Milestone 1.5.
  v0.1.1 is a new, immutable, derived release: `data/{train,validation,test}/goaljourney-v0.1.1.jsonl`,
  status `draft_unreviewed`.
* **Every change is traceable.** `data/revisions/v0.1.1.yaml` has one entry per changed example: 36
  entries, 13 `defect_fix` and 23 `policy_alignment`. Each entry records:
  * the defect, the correction and the rationale;
  * the known issues and policies involved;
  * content hashes before and after, the changed JSON paths and full snapshots of both versions.

  `gj revisions check` fails on any unrecorded or stale difference, and `gj split` refuses to build
  without a clean ledger. Metadata changes are counted separately: schema_version, scenario_group and
  topic_group on all 93 examples; annotations on 2.
* **Four policies decided** in [`POLICY_DECISIONS_v0.1.1.md`](POLICY_DECISIONS_v0.1.1.md):
  * capabilities (POL-A);
  * confidence semantics (POL-B);
  * deadline autonomy (POL-C);
  * Russian voice (POL-D).

  Plus fact provenance (POL-E) and the product principle (POL-F).
* **The six defects named in the brief are corrected** (§3). All 6 high-severity known issues are
  `fixed_pending_review`, and the heuristic audit finds no high-severity issue left in any expected
  output (§6).
* **Deterministic validators now catch the defect classes that slipped through v0.1.0:**
  * calendar weekdays;
  * workload arithmetic, including arithmetic stated in prose;
  * deadline autonomy and feasibility;
  * capability promises;
  * evidence ceilings;
  * fact provenance;
  * Russian gendered forms.

  Each is version-gated, so v0.1.0 records are still judged by v0.1.0 rules (§4).
* **Evaluation v0.2.0** replaces the v0.1.0 set, which stays frozen. It has 63 cases from independent
  seeds: 43 atomic, 14 composite and 6 longitudinal, 106 model calls in all. It includes the 5-turn
  Python chain, adversarial cases in 26 of the 63 cases, and a leakage report split into lexical,
  semantic/template and scenario families. The design and results are in
  [`EVALUATION_V0.2_DESIGN.md`](EVALUATION_V0.2_DESIGN.md).
* **Verdict: not training-ready.** 1 of 11 release gates passes (§10). No gate was loosened.

## 2. What changed, by kind

| Kind | Entries | Examples |
|---|---:|---|
| defect_fix | 13 | the six brief defects (`gj-nav-006`, `gj-time-001`, `gj-time-004`, `gj-nav-001`, `gj-task-004`, `gj-clar-007`) plus `gj-time-003`, `gj-route-004`, `gj-route-005`, `gj-route-002`, `gj-nav-003`, `gj-nav-008`, `gj-mem-003` |
| policy_alignment | 23 | protocols brought to POL-B ceilings (12), capability rewrites (`gj-vprot-001`, `gj-vprot-003`, `gj-vres-002`), untagged defects in rejected outputs now tagged (`gj-clar-001`, `gj-jour-004`, `gj-jour-005`, `gj-vprot-007`, `gj-vres-004`, `gj-vres-006`), Russian memory wording in inputs (`gj-mem-002`, `gj-lang-001`), … |

Which policy changed which example is listed per policy in the policy document, reconciled with the
ledger (POL-A 5, POL-B 16, POL-C 9, POL-D 7, POL-E 11 entries; 3 entries tied to no policy).

Nothing was silently edited. `gj revisions diff <example>` prints every changed path with the old and
new value from the snapshots.

## 3. The six defects from the brief

| Revision | Example | Defect | Correction |
|---|---|---|---|
| REV-0.1.1-001 | gj-nav-006 | «воскресенье 5-го», but 5 Oct 2026 is a Monday; the milestone move to 14 Oct was only in the summary; reschedules did not say which level moves | «понедельник, 5 октября»; each reschedule declares `target_type` and `new_date`; the milestone move is its own proposed change; the summary is a proposal |
| REV-0.1.1-002 | gj-time-001 | «about 140 hours … around 11 months» counted an already verified project (actual: 115 h, ≈38 weeks); an unnecessary milestone move; the alternative assumed a job search | Numbers recomputed from the node estimates (115 h → 48 h, 16 weeks, ≈6 weeks of buffer); `workload` block; the needless move removed; the alternative argues from the user's March 1 date |
| REV-0.1.1-003 | gj-time-004 | «three extra weeks of buffer» after a vacation that only closes a gap; `new_weekly_hours_planned` 15 for a temporary pace; a due date changed only inside `modified_nodes` | Temporary pace as `workload.pace_phases`; the milestone stays at 10 Dec (now reachable, ≈12 days to spare); the due date is declared in `modified_deadlines` (auto, applied) |
| REV-0.1.1-004 | gj-nav-001 | The answer stated a niche («бюджетные путешествия с детьми») that is nowhere in the input, and overclaimed a time saving | The niche is added to the input as goal memory `gm1` (the recorded result of a verified node) and cited in `facts_used` as user_provided; the overclaim is removed |
| REV-0.1.1-005 | gj-task-004 | Masculine self-reference «разбил»; user-entered tables rated medium/high | «Подготовка разбита на 4 задачи»; each protocol's ceiling follows its evidence class (POL-B) |
| REV-0.1.1-006 | gj-clar-007 | Masculine address «едете ли вы один»; an unsourced market generalisation; an untagged missed question in the rejected output | «планируете переезд в одиночку или с семьёй?»; the claim is hedged; facts_used; the rejected output is tagged `missed_critical_question` |

Each entry also records a rationale. All are `reviewer_status: pending_human_review`.

## 4. Validator changes

New modules in `generation/validators/`:

| Module | What it checks | Codes |
|---|---|---|
| `calendar.py` | weekday named with a date vs the calendar; relative dates ("this Friday", «в следующий вторник») resolved from `today` | `DATE_WEEKDAY_MISMATCH` |
| `workload.py` + `quantities.py` | remaining work vs capacity with temporary pace phases and horizons; every hour/week/month/day quantity in the message and the decision summary must follow from the plan | `ARITH_REMAINING_BEFORE/AFTER`, `ARITH_UNESTIMATED`, `ARITH_WEEKS_NEEDED/AVAILABLE`, `ARITH_FITS`, `ARITH_HORIZON_DATE`, `ARITH_PACE`, `ARITH_TEXT_UNDERIVABLE`, `RA_WORKLOAD_MISSING`, `RA_UNFIT_NO_DECISION`, `MILESTONE_DATE_INFEASIBLE`, `J_MILESTONE_OVERBOOKED`, `T_OVER_CAPACITY` |
| `policy.py` | capabilities (POL-A) and evidence classes (POL-B) from `configs/product_capabilities.yaml` and `configs/evidence_policy.yaml` | `VP_METHOD_UNAVAILABLE`, `EVIDENCE_SOURCE_UNAVAILABLE`, `CAPABILITY_PROMISE`, `VP_CEILING_ABOVE_EVIDENCE`, `VR_CONFIDENCE_ABOVE_EVIDENCE`, `VR_BASIS_MISMATCH` |
| `provenance.py` | `facts_used` point at real context (conversation turn, memory item, research result…); inferred facts are never upgraded; numbers in memory items come from the conversation | `FACT_BAD_REF`, `FACT_NOT_GROUNDED`, `FACT_PROVENANCE_UPGRADED`, `FACT_VERIFIED_WITHOUT_SOURCE`, `MEM_SOURCE_NOT_GROUNDED` |
| `russian.py` | the assistant's gendered self-reference, gendered address to the user, gendered wording in stored memory | `RU_GENDERED_SELF_REFERENCE`, `RU_GENDERED_USER_ADDRESS`, `RU_GENDERED_MEMORY` |

**Deadline autonomy (POL-C)** in `semantic.py`: `RA_DEADLINE_AUTONOMY_MISSING/WRONG`,
`RA_DEADLINE_STATE_INCONSISTENT`, `RA_MILESTONE_NO_SUMMARY`, `RA_UNDECLARED_DEADLINE_CHANGE`,
`NAV_RESCHEDULE_UNDECLARED`, `NAV_GOAL_DEADLINE_NO_CONFIRM` and `GC_DEADLINE_NO_CONFIRM`.
`J_GOAL_DEADLINE_CHANGED` becomes an error.

**Verification.** Contradictions between evidence and claims must be recorded and cannot be
`verified` (`VR_CONTRADICTION_VERIFIED`, `VR_CONTRADICTION_BAD_REF`).

**Input lint.** Inputs are linted too: protocols given in the input, weekdays in earlier assistant
turns, and gendered memory in the input.

**Record validation.** Records are validated against the rules of their own `schema_version`. At
v0.1.1, a rejected output whose lint errors fall outside its tagged failure modes gets a warning, so
untagged extra defects surface.

**Refinement during Milestone 1.6.** At v0.1.1 a performance export (such as a drill history) counts
as fitting evidence for `skill_acquisition`, and a public page or verification link for
`administrative` (`VP_NATURE_MISMATCH`). These are warnings only, and the lint output for the training
data is unchanged.

**The audit heuristics are now policy-aware:**

* `user_entered_as_objective` uses the POL-B classes;
* `capability_assumption` uses the POL-A registry;
* `deadline_change_without_consent` respects autonomy;
* `change_without_consent` accepts removals that carry out a decision already confirmed in
  `decision_log`.

Re-running the v0.1.1 heuristics over the frozen v0.1.0 release gives 127 findings instead of the
committed 122:

| Rule | v0.1.0 heuristics | v0.1.1 heuristics |
|---|---:|---:|
| `user_entered_as_objective` | 16 | 19 |
| `capability_assumption` | 6 | 9 |
| `deadline_change_without_consent` | 4 | 3 |

The v0.1.0 report stays as committed.

**Known limits:**

* The text-arithmetic rule reads «N weeks left» as remaining work.
* A sentence-initial institution («Библиотека перенесла…») is read as the assistant's
  self-reference.
* Number words cover common forms only.

These are false positives. The authors rephrase around them; they never hide real errors.

## 5. Schema changes (v0.1.0 archived in `schemas/archive/v0.1.0/`)

* `common.json#/$defs/fact` + `facts_used` on clarification, feasibility, journey, daily plan,
  navigator, route adaptation and goal change (POL-E). Conversational text is **not** required to
  carry provenance; only the facts an answer relies on are listed.
* `route_adaptation`:
  * `modified_deadlines[].autonomy` and `.state` (POL-C);
  * `workload` (weekly hours, pace phases, remaining minutes before/after, horizon, weeks needed and
    available, fits);
  * `invalidated_progress`.
* `navigator_response.proposed_changes[].target_type` and `.new_date`.
* `verification_protocol.methods[].evidence_class` and `.references_required`;
  `verification_result.contradictions`; `evidence.responds_to`.
* `example_record.topic_group` and `.revision`.
* `eval_case`: `case_type`, `steps[]` with `step_pattern`, `scenario_group`, `strata`, `adversarial`,
  `reference_status`, and the new metrics.
* New schemas:
  * `behavioural_scenarios.json` — the scenario registry;
  * `revision_ledger.json`;
  * `review_sample_status.json`.
* `review_event.new_status_detail`, and known-issue triage fields.
* **Canonical review statuses:** `pending | approved | needs_revision | rejected`, with a
  `detail` of `not_reviewed | content_changed | awaiting_expert | decided`. The log stays append-only
  (review log v0.3.0).

## 6. Automated results for v0.1.1

| Check | Result |
|---|---|
| `gj validate` | 93/93 valid; **1 warning** (`gj-vres-007` input protocol, KI-033, open); 64 rejected outputs, every lint-detectable failure mode detected; eval v0.1.0 30/30 and v0.2.0 63/63 valid |
| `gj revisions check` | every difference from v0.1.0 recorded; snapshots and base release intact |
| Tests | 416 passed |
| Evaluation self-check (v0.2.0) | reference 106/106 units, 63/63 cases; naive baseline 0/106 units |
| Heuristic audit | 128 findings (v0.1.0: 122). Expected outputs: **0 high** (v0.1.0: 4), 3 medium (v0.1.0: 26), 22 low, 39 info. Examples with a non-info finding: 19 (v0.1.0: 34) |
| Leakage | 0 hard findings in any family; max lexical similarity 0.338; 100 reviewed overlaps awaiting dispositions |
| Review log | empty; nobody has reviewed anything yet |

The three remaining medium findings on expected outputs:

* `gj-jour-001` `capacity_mismatch` — pacing 10 h/week × 22 weeks vs ≈47 h of tasks. This is open
  known issue KI-008; it needs a content decision (is the rest of the time job searching?), so it was
  left for review.
* `gj-jour-004` `ru_gendered_identity_label` ×2 — level titles that are role nouns. POL-D rule 3
  accepts natural role nouns as badge names (REV-0.1.1-028), so the heuristic keeps flagging them
  for a reviewer to confirm.

Among the low findings, `gj-goalchg-001` («the December 1 date still works» without the user's pace)
is open known issue KI-012 (medium).

The known-issues register `review/known_issues_v0.1.1.yaml` holds 34 issues:

* 22 `fixed_pending_review`: every high-severity issue (6) and 7 of the 9 medium ones;
* 11 `open`: 2 medium, 9 low;
* 1 `wont_fix`: KI-034, which belongs to the frozen evaluation v0.1.0 and cannot change.

## 7. Review sample (kept, not re-drawn)

The 30-item sample `review/review_manifest_v0.1.0.json` is kept: same item ids, strata and 8
calibration items (rv-0.1.0-02, -06, -07, -09, -12, -20, -29, -30). `gj review sample --check`
regenerates it exactly from the frozen v0.1.0 inputs. `review/review_sample_status_v0.1.1.json`
carries it to v0.1.1:

* **12 of 30 items changed** since sampling, each with its revision id. Two of them are calibration
  items: rv-0.1.0-06 `gj-time-001` and rv-0.1.0-20 `gj-jour-003`.
* **18 unchanged.**
* Known issues are linked to the items with their current status.
* Human review status: **30 pending / not_reviewed**. `approved_by_automation: 0`.

A decision recorded against older content would not carry over to changed content (detail
`content_changed`). The status file is regenerated and checked in `make check`.

## 8. Release v0.1.1

| | v0.1.0 | v0.1.1 |
|---|---|---|
| train / validation | 81 / 12 | 81 / 12 |
| test (evaluation) | 30 cases | 63 cases (106 model calls) |
| release status | draft_unreviewed | draft_unreviewed |
| revision record | — | `revisions` block + `revision_ids` / `previous_content_hash` on the 36 revised rows |

The validation split is **not comparable** with v0.1.0. Scenario groups were relabelled from topics
to behavioural scenarios (one per example), and the seeded group split re-ranks them, so 10 of the 12
validation examples changed. `topic_group` keeps the old label for traceability.

## 9. Evaluation v0.2.0 and leakage

Summary; details are in [`EVALUATION_V0.2_DESIGN.md`](EVALUATION_V0.2_DESIGN.md).

* **Cases.** 63 cases from 63 independent seeds, one eval-side behavioural scenario each, with a
  step pattern for every composite and longitudinal step: 43 atomic, 14 composite (2 steps) and 6
  longitudinal (5–9 steps). Every documented stratum has at least 4 cases, and all 9 adversarial types
  are covered.
* **Leakage families.** The report separates lexical (0 hard), semantic/template (0 hard, 13 automated
  candidates, all reviewed) and scenario (0 hard) overlap.
* **Manual review.** The review against all 92 training scenarios rewrote 3 cases that repeated a
  training decision pattern and 5 whose topic repeated a training example or seed. It records 100
  remaining overlaps: 11 strong (all set-up or intermediate steps), 78 medium, 4 topic_only, 7 none.
* **What the automated layers miss.** They found 13 of the 116 reviewed pairs. The report therefore
  says what each family *cannot* establish, and it never states "no leakage".

## 10. Release gates (not loosened)

| Gate | v0.1.1 | Why |
|---|---|---|
| validation_strict | FAIL | 1 warning: gj-vres-007 input protocol (KI-033 needs a reviewer's choice between two fixes) |
| review_all_approved | FAIL | 0/93 approved |
| findings_acknowledged | FAIL | no approved rows |
| known_issues_closed | FAIL | open medium issues KI-008, KI-012 |
| reviewer_diversity | FAIL | no approving reviewers |
| calibration_agreement | FAIL | 0/8 calibration items double-reviewed |
| leakage_hard_clean | **PASS** | 0 hard findings |
| leakage_dispositions | FAIL | 100 reviewed overlaps without a human disposition |
| coverage_minimums | FAIL | 0 approved train rows (target ≥ 1,000) |
| eval_readiness | FAIL | 63/200 cases; 11 operations below 10 model calls |
| licensing_resolved | FAIL | 5 open licensing items |

## 11. Remaining issues

* **Human review has not started.** Nothing in v0.1.1 is approved. That includes all 36 revisions and
  all 106 draft evaluation references.
* **Open known issues:**
  * 11 open issues, 2 medium: KI-008 (pacing vs tasks in `gj-jour-001`) and KI-012 (unsupported
    feasibility claim in `gj-goalchg-001`).
  * 9 low issues, mostly confident generalisations (KI-019) and question minimality.
  * KI-033, the `gj-vres-007` input protocol.
* **Scale.** 93 examples (the pilot) and 63 evaluation cases. Both are far below the gates.
* **Untrained failure modes.** Four failure modes introduced in v0.1.1 have no rejected output in
  the training data yet: `calendar_error`, `arithmetic_error`, `ignored_contradiction` and
  `gendered_language`. The validators detect them, but preference data for them has to be written
  (the preference gate needs ≥ 5 per mode).
* **Author independence.** One agent wrote the data, the fixes, the validators, the evaluation and
  this audit. The validators were written with the data in view, so passing them is partly circular.
* **Validator limits.**
  * Arithmetic and calendar checks cover hours, weeks, months, days and weekdays, but not money or
    distances.
  * Provenance checks only the facts listed in `facts_used`.
  * Gendered-form detection is heuristic.
* **Policy confirmation.** The policies were decided by dataset engineering and need the product
  owner's confirmation (POLICY_DECISIONS status note).

## 12. Recommended next step

Start human review. It unblocks every other gate.

1. Record reviewers in `review/reviewers.yaml` (humans only).
2. Have at least two RU and two EN reviewers independently rate the 8 calibration items. Items
   rv-0.1.0-06 and rv-0.1.0-20 have changed, so rate their current content.
3. Check agreement: `gj gates` requires κ ≥ 0.40.
4. Review the 36 ledger revisions and set their `reviewer_status`.
5. Decide the open known issues (KI-008, KI-012, KI-033).
6. Give dispositions to the 100 evaluation overlaps.
7. Review the v0.2.0 references, longitudinal cases first.

Only after that should Milestone 2 scale generation, using the v0.1.1 validators as the automatic
floor.
