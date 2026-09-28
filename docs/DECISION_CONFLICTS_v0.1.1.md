# Decision conflicts and ambiguities — v0.1.1

*Prepared 2026-09-28 as part of the Product Owner Decision Review Pack. Compares
`docs/DECISIONS.md` (D-001…D-020) against `docs/POLICY_DECISIONS_v0.1.1.md`, `DATASET_SPEC.md`,
`docs/ARCHITECTURE.md` and `README.md`. This file records findings only; nothing here resolves a
conflict or changes a status.*

Two real issues were found. Everything else cross-checked cleanly: `DECISIONS.md` is a faithful
short summary of the source documents for D-001, D-002, D-003, D-005 through D-009, D-011 through
D-020.

---

## C-1. D-004 oversimplifies POL-B's confidence ceilings for user-entered data and images

**Where:** `docs/DECISIONS.md` D-004 vs. `docs/POLICY_DECISIONS_v0.1.1.md` POL-B and
`DATASET_SPEC.md` §7.

**The conflict.** D-004 states, without qualification:

> Confidence follows the evidence class: self-report, user-entered data and image descriptions
> give at most *limited*.

But POL-B's own table gives two explicit exceptions:

> `user_entered_data` … Ceiling alone: **limited** … Can reach medium when: every row carries a
> checkable reference (`references_required: true`) **and** the protocol spot-checks references
> (URL fetch).
>
> `image_description` … Ceiling alone: **limited**, never sufficient alone … Can reach medium
> when: combined with another required non-image method (a physical result shown **and**
> explained).

`DATASET_SPEC.md` §7 restates the same exceptions ("user-entered data with checkable references
plus a URL spot-check → *medium*; an image together with a non-image required method → *medium*"),
so the policy and spec agree with each other — only `DECISIONS.md`'s summary is out of step.

**Why it matters.** A reviewer or engineer who reads only `DECISIONS.md` (the durable,
supposedly-authoritative summary) would conclude that user-entered data and image descriptions can
*never* exceed *limited*, and could raise a spurious defect against `medium`-rated examples that
are in fact policy-compliant under POL-B's exception. Since these are exactly the examples POL-B's
own changelog says it altered ("16 ledger entries" that raised or lowered confidence based on this
distinction), the ambiguity sits directly on live review material.

**Not resolved here.** Whether D-004 should be corrected to match POL-B (the likely fix, since
POL-B is the more detailed and more recently confirmed source), or whether POL-B's exceptions
should instead be narrowed to match D-004's stricter wording, is a product-owner call — it changes
what confidence ceiling a real example is allowed to claim.

## C-2. D-010 states Russian output is gender-neutral as settled, but the level/badge-title question is explicitly still open

**Where:** `docs/DECISIONS.md` D-010 vs. `docs/POLICY_DECISIONS_v0.1.1.md` POL-D and
`docs/HUMAN_REVIEW_GUIDE.md` §8.

**The conflict.** D-010 reads as a closed decision:

> **Russian voice is gender-neutral.** The navigator uses no gendered self-reference and never
> addresses the user with a gendered form. Stored memory is written without gendered forms.

This covers self-reference, address and memory — all three of which POL-D and the validators
(`RU_GENDERED_SELF_REFERENCE`, `RU_GENDERED_USER_ADDRESS`, `RU_GENDERED_MEMORY`) treat as settled
and lint automatically. But POL-D's own §3 (level and achievement titles) and
`docs/HUMAN_REVIEW_GUIDE.md` §8 are explicit that the *title* case is **not** settled:

> level «Уверенный нарезчик», «Хозяин ужина» — an identity label with grammatical gender — name
> the stage, not the person … **(a policy decision is pending; flag every case)**

The known-issues register makes the same point for v0.1.0 and it is still open in v0.1.1
(`review/known_issues_v0.1.1.yaml`, `ru_gendered_identity_label`, "A policy for gendered identity
labels in Russian does not exist yet"). POL-D itself only says titles "are not linted as errors;
the audit lists them at info level" — i.e. explicitly *not yet a hard rule* like the other three
Russian-voice cases.

**Why it matters.** D-010, read on its own, gives no hint that a fourth Russian-voice sub-case
(identity labels in level/achievement titles) is unresolved. A reviewer relying on `DECISIONS.md`
alone could treat "Уверенный нарезчик"-style titles as already-decided violations (or as
already-decided acceptable), when the project's own audit and known-issues register carry them as
open findings awaiting a product decision.

**Not resolved here.** Whether badge/level titles should be gender-neutral by the same rule as
self-reference/address/memory, or whether they get a separate, more permissive rule (as POL-D §3
currently allows: "may use the natural dictionary form of a role noun when the role is the natural
title"), is the actual open question for the product owner — see
`docs/PRODUCT_OWNER_DECISION_CHECKLIST.md` D-010.

---

## Checked and found consistent (no write-up needed)

* D-001/D-002 vs. DATASET_SPEC §5–6 and POL-C — consistent, including the three-tier autonomy
  model and its validator codes.
* D-003 vs. DATASET_SPEC §7 (`VP_PHOTO_ONLY`) — consistent.
* D-005 vs. POL-A's capability table and DATASET_SPEC §7 — consistent, including the
  available/planned/unsupported split.
* D-008 vs. DATASET_SPEC §9's safety-category table — consistent.
* D-009 vs. POL-E's fact-provenance table — consistent.
* D-012 vs. `docs/ARCHITECTURE.md` §6 — consistent; only the status *label* differs
  ("accepted" in ARCHITECTURE.md's heading vs. "adopted" in DECISIONS.md), which is terminology,
  not a substantive conflict, since `docs/DECISIONS.md` itself defines "adopted" as the
  not-yet-owner-confirmed status and ARCHITECTURE.md predates that convention.
* D-013 through D-020 vs. DATASET_SPEC §14–19 and README.md — consistent.
* No contradictions were found against `README.md`'s status summary or command reference.
