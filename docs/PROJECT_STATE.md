# Project state

*Last updated: 2026-09-30 · during Milestone 1.7 (Human Review Round 1), after the move to
solo-owner-first review governance (D-026, pipeline 0.4.0) and the first solo-owner reviews
(rv-0.1.0-01, rv-0.1.0-03, rv-0.1.0-04, rv-0.1.0-05, rv-0.1.0-06, rv-0.1.0-07, rv-0.1.0-08, rv-0.1.0-10, rv-0.1.0-11, rv-0.1.0-13, rv-0.1.0-14, rv-0.1.0-15, rv-0.1.0-16, rv-0.1.0-17, rv-0.1.0-18, rv-0.1.0-19, rv-0.1.0-21, rv-0.1.0-22, rv-0.1.0-23, rv-0.1.0-24, rv-0.1.0-25, rv-0.1.0-26, rv-0.1.0-27, rv-0.1.0-28), which complete the decisions
on the 30-item review sample. Update this file before declaring any
milestone complete (`/milestone-complete`).*

**Governance change (D-026).** The project has moved from **multi-reviewer-first governance** to
**solo-owner-first governance with optional expert escalation**. The reasons:

* the project has one product owner;
* the pairwise gates (`reviewer_diversity`, `calibration_agreement`) could be met only with a second
  independent person the project does not have, or with a fabricated identity, which the review
  rules forbid.

Solo mode keeps every check one careful human can honestly perform:

* the rubric A–Q with hard gates L and M;
* content-hash binding and the append-only log;
* invalidation on revision;
* ratings independent of automated findings;
* the expert tier.

Solo mode is also explicit about what one person cannot provide: the two pairwise gates are shown as
**N/A**, never as passed, and expert-tier items without a qualified expert stay `awaiting_expert`
and are not training-eligible. `multi_reviewer` mode keeps the earlier semantics.

This file is the durable, factual snapshot of the repository. The repository is the source of
truth; chat history is not.

## Repository

| | |
|---|---|
| Repository | `infable1/goaljourney` — dataset, validation and evaluation pipeline for the GoalJourney Navigator model |
| Working branch | Default branch `claude/fervent-keller-j517cd` (there is no `main`). The M1.7 review round after `ae21c7d` is on `claude/sleepy-dijkstra-nzrf3t`, which also merged the rv-0.1.0-29 record from `claude/compassionate-noether-1o9iyx`; it is not merged into the default branch. No open pull request (infable1/goaljourney#1 and infable1/goaljourney#2 were closed unmerged) |
| History | `995f513` M1 → `476d322` M1.5 → `c3b7cfb`…`13d837e` M1.6 → orchestration setup → M1.7 review round `fdf6d4c`…`e0dbc53` → solo-owner governance (D-026, pipeline 0.4.0) `6d6bcb5` → first solo-owner reviews `9457084`, the rv-0.1.0-01 independence correction `2438dd4` the rv-0.1.0-04 review `5b3f7c4` and the rv-0.1.0-05 review `71c92eb` and the rv-0.1.0-06 review `8deff75` and the rv-0.1.0-07 review `40a3d51` with its notes correction `7284b5a` the rv-0.1.0-08 review `2997666` and the rv-0.1.0-10 review `301009a` the rv-0.1.0-11 review `c7eef17` the rv-0.1.0-13 review `b297d91` and the rv-0.1.0-14 review `8aa4416` the rv-0.1.0-15 review `6e92860` the rv-0.1.0-16 review `d876db9` the rv-0.1.0-17 review `49fe41f` the rv-0.1.0-18 review `e27bb32` the rv-0.1.0-19 review `8ee6efd` the rv-0.1.0-21 review `57c78c0` with its text correction `8eafa75` the rv-0.1.0-22 review `10a493b` the rv-0.1.0-23 review `b7d1c5c` the rv-0.1.0-24 review `26e98e5` with its independence correction `212cf67` the rv-0.1.0-25 review `1e2e9b2` the rv-0.1.0-26 review `3af4cae` the rv-0.1.0-27 review `73c22db` and the rv-0.1.0-28 review `2f2511f`, which completes the sample (latest commits: `git log --oneline -5`) |
| Language / stack | Python ≥ 3.10; jsonschema, referencing, PyYAML, pytest; CLI `scripts/gj.py`; `make check` |
| Mobile app / product code | not in this repository |

## Versions (`configs/versions.yaml` is authoritative)

| Artefact | Version | Notes |
|---|---|---|
| dataset | 0.1.1 | release `draft_unreviewed`: train 81, validation 12, test 63 eval cases. v0.1.0 is immutable and kept |
| schema | 0.1.2 | 0.1.2 adds the revision-ledger `review` block; v0.1.0 and v0.1.1 archived in `schemas/archive/`. Records stay at `schema_version` 0.1.1 and validate against the archived set |
| pipeline | 0.4.1 | `gj revisions review` (human decisions on ledger entries, bound to the content hash); 0.4.0: review governance modes (`solo_owner` default), gate scopes, training-eligibility accounting in release manifests; 0.3.0: v0.1.1 validators, revision ledger, review log v0.3, eval builders |
| evaluation | 0.2.0 | 63 cases / 106 model calls (43 atomic, 14 composite, 6 longitudinal). v0.1.0 (30 cases) frozen |
| navigator prompt / generation prompts | 0.1.1 / 0.1.1 | `prompts/navigator/v0.1.1/`, `prompts/generation/v0.1.1/` |
| base model | unset | chosen later, recorded in `configs/versions.yaml` |

## Milestones

* Done: M1 (dataset foundation), M1.5 (human review system, audits, leakage, gates) and M1.6
  (dataset calibration v0.1.1).
* Active: M1.7 (Human Review Round 1), in progress; see [`ACTIVE_MILESTONE.md`](ACTIVE_MILESTONE.md).
  Plan: [`ROADMAP.md`](ROADMAP.md). Review state (from `gj review stats`, `gj gates`):
  * **Governance mode:** `solo_owner` (`configs/review.yaml`). `reviewer_diversity` and
    `calibration_agreement` are N/A. Adjudication and pairwise calibration are not part of the solo
    workflow.
  * **Reviewers:** 2 registered humans, `po-reviewer` and `po-reviewer-two`, both still `active`.
    Both are `dataset_reviewer`, read ru and en, and hold no expert domains. No `adjudicator` and no
    `domain_expert` is registered. `gj review stats` notes the 2 active reviewers in solo mode.
    Whether `po-reviewer-two` keeps reviewing (or is set `active: false`; past events keep their
    snapshot) is the owner's decision.
  * **Decisions:** 45 review events (`po-reviewer` 37, `po-reviewer-two` 8).
    * The first 17 are stamped rubric 0.2.0: 16 on the 8 calibration items, plus 1
      (`rev-da39af4d1363`, approve of `gj-daily-002`) on an example outside the review sample.
    * The last 28 are stamped rubric 0.2.1. They are the solo-owner reviews by `po-reviewer`:
      * rv-0.1.0-01 / `gj-feas-005`: `rev-044d69c4953d` (approve / acceptable, minor issues),
        followed by the corrective `rev-a1a061cc1487`;
      * rv-0.1.0-03 / `gj-prog-003`: `rev-599dbd07516e` (approve / acceptable, minor issue);
      * rv-0.1.0-04 / `gj-route-006`: `rev-612c1a60c45a` (`5b3f7c4`), `revise`, overall
        `needs_revision`, `user_agency: major_issues`, `language_quality: minor_issues`,
        `independent_rating: true`. The example is `needs_revision`, so it is not
        training-eligible;
      * rv-0.1.0-05 / `gj-route-003`: `rev-3f360f0323f8` (`71c92eb`), `approve`, overall
        `excellent`, no issues, `contrastive_quality: good`, `privacy_and_memory:
        not_applicable`, `independent_rating: false`. The owner changed those two ratings after
        the AI second-look discussion, so the flag records provenance; it is not an issue;
      * rv-0.1.0-06 / `gj-time-001` (a calibration item): `rev-1584bfb68001` (`8deff75`),
        `approve`, overall `excellent`, no issues, `contrastive_quality: good`,
        `privacy_and_memory: not_applicable`, `independent_rating: false` (the owner changed
        `privacy_and_memory` after the AI second-look discussion). The example was already
        `approved` on its current content hash (`4e129fbf…`, the v0.1.1 revision) by
        `po-reviewer` and `po-reviewer-two`, both `acceptable` under rubric 0.2.0, so this event
        did not change any pool or sample count. It is now `po-reviewer`'s latest decision on
        that content, and the earlier 0.2.0 events are unchanged;
      * rv-0.1.0-07 / `gj-mem-004` (a calibration item): `rev-2172b02c5ad4` (`40a3d51`), `approve`,
        overall `acceptable`, minor `language_quality` issue, `contrastive_quality:
        not_applicable`, `independent_rating: false` (the owner changed `external_fact_discipline`
        and `contrastive_quality` after the AI second-look discussion). Its `notes` field held a
        stray instruction, so `rev-896e41f5431a` (`7284b5a`) was appended with the intended notes
        and every other field identical; the earlier line is unchanged. The example was already
        `approved` on its current content hash (`3073971d…`) by `po-reviewer` (`excellent`) and
        `po-reviewer-two` (`acceptable`) under rubric 0.2.0, so these events changed no pool or
        sample count. `po-reviewer`'s latest decision on it is now `acceptable`;
      * rv-0.1.0-08 / `gj-goalchg-004`: `rev-f758a292a772` (`2997666`), `approve`, overall
        `excellent`, no issues, `contrastive_quality: not_applicable`, `privacy_and_memory:
        not_applicable`, `independent_rating: false` (the owner changed those two ratings from
        `good` after the AI second-look discussion). It was `pending` and is now `approved`;
      * rv-0.1.0-10 / `gj-clar-008`: `rev-b9fc375fa353` (`301009a`), `approve`, overall
        `excellent`, no issues, `verification_quality`, `evidence_interpretation`,
        `adaptation_quality`, `contrastive_quality` and `privacy_and_memory` all
        `not_applicable`, the other 11 `good`, `independent_rating: false` (the owner changed
        those five from `good` after the AI second-look discussion). It was `pending` and is now
        `approved`;
      * rv-0.1.0-11 / `gj-web-004` (a `web_research_decision`): `rev-f9651cdb0493` (`c7eef17`),
        `approve`, overall `excellent`, no issues. `product_usefulness`, `goal_understanding`,
        `explanation_quality`, `external_fact_discipline`, `safety`, `language_quality` and
        `contrastive_quality` are `good`; `question_minimality`, `actionability`, `realism`,
        `dependency_correctness`, `verification_quality`, `evidence_interpretation`,
        `user_agency`, `adaptation_quality` and `privacy_and_memory` are `not_applicable`.
        `independent_rating: false` (the owner changed seven ratings after the AI second-look
        discussion). Content hash `e3db3ea1…` matched the sampled hash and had no earlier review.
        It was `pending` and is now `approved`;
      * rv-0.1.0-13 / `gj-task-004` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-005`): `rev-ee991d345309` (`b297d91`), `approve`, overall `excellent`,
        `issues: []`. `question_minimality`, `evidence_interpretation`, `user_agency`,
        `adaptation_quality` and `privacy_and_memory` are `not_applicable`; the other 11 are
        `good`. `independent_rating: false` (the owner changed those five from `good` after the AI
        second-look discussion). The reviewed version is the revised content hash `7254399c…`, not
        the sampled `36c5dd1b…`; it had no earlier review and is now `approved`. Its known issues
        `KI-004` and `KI-015` remain `fixed_pending_review` in the sample status;
      * rv-0.1.0-14 / `gj-jour-001` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-017`): `rev-9af791ca3ec1` (`8aa4416`), `revise`, overall `needs_revision`.
        Issues: `realism` minor, `explanation_quality` minor, `external_fact_discipline` major.
        `question_minimality`, `adaptation_quality` and `privacy_and_memory` are `not_applicable`.
        `independent_rating: false` (the owner changed the applicability of those three after the
        AI second-look discussion and confirmed the E/K/L ratings). The reviewed version is the
        revised content hash `b4492d1f…`, not the sampled `77906c26…`; it had no earlier review
        and is now `needs_revision`. `KI-008` remains `open` and `KI-015`
        `fixed_pending_review` in the sample status;
      * rv-0.1.0-15 / `gj-vprot-004` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-016`): `rev-a72d9fb206f1` (`6e92860`), `approve`, overall `excellent`,
        `issues: []`. `question_minimality`, `dependency_correctness`, `adaptation_quality`,
        `contrastive_quality` and `privacy_and_memory` are `not_applicable`; the other 11 are
        `good`. `independent_rating: false` (the owner changed the applicability of those criteria
        after the AI second-look discussion). The reviewed version is the revised content hash
        `555bdf0e…`, not the sampled `b8123766…`; it had no earlier review and is now `approved`.
        Its known issues `KI-014` and `KI-015` remain `fixed_pending_review` in the sample
        status;
      * rv-0.1.0-16 / `gj-task-002` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-021`): `rev-905177337998` (`d876db9`), `revise`, overall `needs_revision`.
        Issues: `realism` minor, `verification_quality` minor. `question_minimality`,
        `user_agency`, `adaptation_quality`, `contrastive_quality` and `privacy_and_memory` are
        `not_applicable`; the other 9 are `good`. `independent_rating: false`. The reviewed
        version is the revised content hash `23c95b15…`, not the sampled `96f0bfce…`; it had no
        earlier review and is now `needs_revision`. `KI-014` and `KI-015` remain
        `fixed_pending_review` in the sample status;
      * rv-0.1.0-17 / `gj-clar-007` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-006`): `rev-f859c085d0a3` (`49fe41f`), `approve`, overall `excellent`,
        `issues: []`. `verification_quality`, `evidence_interpretation`, `adaptation_quality` and
        `privacy_and_memory` are `not_applicable`; the other 12 are `good`.
        `independent_rating: false` (the owner changed the applicability of those criteria after
        the AI second-look discussion). The reviewed version is the revised content hash
        `949f477f…`, not the sampled `a375ae92…`; it had no earlier review and is now `approved`.
        Its known issue `KI-005` remains `fixed_pending_review` in the sample status;
      * rv-0.1.0-18 / `gj-nav-006` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-001`): `rev-411ee8471106` (`e27bb32`), `approve`, overall `excellent`,
        `issues: []`. `question_minimality`, `verification_quality`, `evidence_interpretation` and
        `privacy_and_memory` are `not_applicable`; the other 12, including `adaptation_quality`,
        are `good`. `independent_rating: false` (the owner changed the applicability of those
        criteria after the AI second-look discussion). The reviewed version is the revised content
        hash `626869a7…`, not the sampled `5c93d672…`; it had no earlier review and is now
        `approved`. Its known issue `KI-001` remains `fixed_pending_review` in the sample status;
      * rv-0.1.0-19 / `gj-time-003` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-007`; no expert domain): `rev-d498bb6d343b` (`8ee6efd`), `revise`, overall
        `needs_revision`. Issues: `adaptation_quality` major (n4 and n6 leave the mandatory path
        while m1 still requires all 6 sections) and `external_fact_discipline` major (unsupported
        claim about exam point weights; a hard gate). The other 14 criteria are `good`.
        `independent_rating: false` (the owner changed J and L from `good` to `major_issues` and
        the decision from approve/excellent to revise/needs_revision after the AI second-look
        discussion). The reviewed version is the revised content hash `e5e92c52…`, not the
        sampled `b5cc77ae…`; it had no earlier review and is now `needs_revision`. `KI-007` and
        `KI-032` remain `fixed_pending_review` in the sample status;
      * rv-0.1.0-21 / `gj-time-004` (a `highest_risk` sample item that changed since sampling via
        `REV-0.1.1-003`; no expert domain): `rev-7463e20f59e6` (`57c78c0`), `revise`, overall
        `needs_revision`. Issue: `realism` major (the workload arithmetic does not support the
        stated timing slack). `question_minimality`, `verification_quality`,
        `evidence_interpretation`, `contrastive_quality` and `privacy_and_memory` are
        `not_applicable`; the other 10 are `good`. `independent_rating: false`. The reviewed
        version is the revised content hash `d8536ef0…`, not the sampled `83f2a3a8…`; it had no
        earlier review and is now `needs_revision`. The issue text contained an arithmetic error
        (12 + 20 hours written as 27), so `rev-ae41d3818db8` (`8eafa75`) was appended with the
        corrected issue description, proposed fix and notes and every other field identical; the
        original event is unchanged and the decision, ratings and status did not change. `KI-003`
        remains `fixed_pending_review` in the sample status;
      * rv-0.1.0-22 / `gj-jour-004` (a `contrastive` sample item that changed since sampling via
        `REV-0.1.1-028`; no expert domain): `rev-3881c74630f9` (`10a493b`), `revise`, overall
        `needs_revision`. Issue: `goal_understanding` major (the goal adds a required success
        criterion, a 3-course dinner for guests, that the user never asked for; it may only be an
        optional extension). `question_minimality`, `evidence_interpretation`, `user_agency`,
        `adaptation_quality` and `privacy_and_memory` are `not_applicable`; the other 10 are
        `good`. `independent_rating: false` (the owner changed B from `good` to `major_issues`, the
        applicability of C, H, I, J and Q, and the decision from approve/excellent to
        revise/needs_revision after the AI second-look discussion). The reviewed version is the
        revised content hash `dd7a3b8f…`, not the sampled `87549836…`; it had no earlier review and
        is now `needs_revision`. `KI-013` remains `fixed_pending_review` in the sample status;
      * rv-0.1.0-23 / `gj-feas-006` (a `contrastive` sample item, unchanged since sampling; no
        ledger revision, no known issue, no expert domain): `rev-fa531d93252b` (`b7d1c5c`),
        `revise`, overall `needs_revision`. Issue: `external_fact_discipline` major (a hard gate;
        an unverified general claim about what associate-level cloud architecture exams require
        and how long preparation usually takes, with no named certification and no verification
        marker, although the feasibility conclusion partly relies on it). `dependency_correctness`,
        `verification_quality`, `evidence_interpretation`, `adaptation_quality` and
        `privacy_and_memory` are `not_applicable`; the other 10 are `good`.
        `independent_rating: false` (the owner changed L from `good` to `major_issues`, the
        applicability of F, G, H, J and Q, and the decision from approve/excellent to
        revise/needs_revision after the AI second-look discussion). The reviewed version is the
        sampled content hash `67e429ff…`; it had no earlier review and is now `needs_revision`;
      * rv-0.1.0-24 / `gj-vres-004` (a `contrastive` sample item that changed since sampling via
        `REV-0.1.1-031`; no known issue, no expert domain): the original review event
        `rev-aa592a3163df` (`26e98e5`) is `approve`, overall `excellent`, no issues, recorded with
        `independent_rating: true`. `question_minimality`, `dependency_correctness`,
        `adaptation_quality` and `privacy_and_memory` are `not_applicable`; the other 12 are
        `good`. That flag was wrong: the owner changed the applicability of C, F, J and Q from
        `good` to `not_applicable` after the AI second-look discussion. The append-only corrective
        event `rev-07d13934c996` (`212cf67`) repeats the same decision, content hash, 16 ratings
        and empty issue list with `independent_rating: false` and Russian notes explaining the
        correction; the original event is unchanged and keeps `true`. The effective latest
        decision is therefore `approve` / `excellent` with `independent_rating: false`; the status
        did not change (`pending` before the first event, `approved` after both). The reviewed
        version is the revised content hash `356dc499…`, not the sampled `2cbbbe61…`;
      * rv-0.1.0-25 / `gj-vprot-005` (a `contrastive` sample item, unchanged since sampling; no
        ledger revision, no known issue, no expert domain): `rev-8c9847364149` (`1e2e9b2`),
        `approve`, overall `excellent`, no issues. `question_minimality`,
        `dependency_correctness`, `evidence_interpretation`, `user_agency`, `adaptation_quality`
        and `privacy_and_memory` are `not_applicable`; the other 10 are `good`.
        `independent_rating: false` (the owner changed the applicability of C, F, H, I, J and Q
        from `good` to `not_applicable` after the AI second-look discussion). The reviewed version
        is the sampled content hash `67b754a0…`; it had no earlier review and is now `approved`;
      * rv-0.1.0-26 / `gj-clar-006` (a `contrastive` sample item, unchanged since sampling; no
        ledger revision, no known issue, no expert domain): `rev-5cd828a81332` (`3af4cae`),
        `approve`, overall `excellent`, no issues. `verification_quality`,
        `evidence_interpretation`, `adaptation_quality` and `privacy_and_memory` are
        `not_applicable`; the other 12 are `good`. `independent_rating: false` (the owner changed
        the applicability of G, H, J and Q from `good` to `not_applicable` after the AI second-look
        discussion). The reviewed version is the sampled content hash `3a263322…`; it had no
        earlier review and is now `approved`;
      * rv-0.1.0-27 / `gj-vretry-002` (a `contrastive` sample item, unchanged since sampling; no
        ledger revision, no known issue, no expert domain): `rev-aeb597251ce5` (`73c22db`),
        `approve`, overall `excellent`, no issues. `question_minimality`,
        `dependency_correctness`, `adaptation_quality` and `privacy_and_memory` are
        `not_applicable`; the other 12 are `good`. `independent_rating: false` (the owner changed
        the applicability of C, F, J and Q from `good` to `not_applicable` after the AI second-look
        discussion). The reviewed version is the sampled content hash `9690cc62…`; it had no
        earlier review and is now `approved`;
      * rv-0.1.0-28 / `gj-safe-002` (an `edge` sample item, unchanged since sampling; no ledger
        revision; expert tier, `financial`; known issue `KI-022`, low, `open`): `rev-fef976fb4399`
        (`2f2511f`), `revise`, overall `needs_revision`. Issue: `external_fact_discipline` major (a
        hard gate; the response calls repaying about 300,000 of credit-card debt within a year
        "quite achievable" without the income, essential expenses, interest rates, minimum
        payments or available monthly amount that would support that). `question_minimality`,
        `actionability`, `realism`, `dependency_correctness`, `verification_quality`,
        `evidence_interpretation`, `adaptation_quality` and `privacy_and_memory` are
        `not_applicable`; the other 7 are `good`. `independent_rating: false` (the owner changed L
        from `good` to `major_issues`, the applicability of C, D, E, F, G, H, J and Q, and the
        decision from approve/excellent to revise/needs_revision after the AI second-look
        discussion). The reviewed version is the sampled content hash `5d0d0c50…`; it had no
        earlier review and is now `needs_revision` (a revise takes effect without expert sign-off;
        approving a revised version will still need `financial` sign-off). The owner's notes treat
        `KI-022` as a separate schema-level issue in how the optional professional referral is
        represented, not a change to the safety rating; it remains `open`.

        With rv-0.1.0-28 every one of the 30 sample items has a human decision on its current
        content hash: 20 `approved` and 10 `needs_revision`, none `pending` or `awaiting_expert`.
  * **Independence correction.** `rev-044d69c4953d` was recorded with `independent_rating: true`,
    but the owner had changed `language_quality` from major to minor issues after the AI-copilot
    discussion. The corrective event appends the same final decision with
    `independent_rating: false`; the original line is unchanged. rv-0.1.0-03 keeps
    `independent_rating: true`, because no rating changed there. Across all events:
    `independent_rating` is absent on 16, `true` on 5 (the original rv-0.1.0-24 event, superseded by its correction), `false` on 24 (the four corrective events, the fourth being `rev-07d13934c996` for rv-0.1.0-24, and rv-0.1.0-05, rv-0.1.0-06, rv-0.1.0-07, rv-0.1.0-08, rv-0.1.0-10, rv-0.1.0-11, rv-0.1.0-13, rv-0.1.0-14, rv-0.1.0-15, rv-0.1.0-16, rv-0.1.0-17, rv-0.1.0-18, rv-0.1.0-19, rv-0.1.0-21, rv-0.1.0-22, rv-0.1.0-23, rv-0.1.0-25, rv-0.1.0-26, rv-0.1.0-27 and rv-0.1.0-28).
  * **Counts (`gj review stats`):**
    * pool (93): human-reviewed 31, training-eligible 21, needs_revision 10, not reviewed 62;
    * review sample (30): decided 30, approved 20, needs_revision 10, pending 0
      (`review/review_sample_status_v0.1.1.json`).
  * **Historical calibration (informational in solo mode):** all 8 items rated by both reviewers
    (`po-reviewer-two` from a blind packet). Decision agreement is 7/8 (0.875, κ 0.60) and
    overall-verdict agreement 3/8 (0.375, κ 0.05; it was 2/8 while rv-0.1.0-06 was `po-reviewer`'s
    only 0.2.1 verdict on a calibration item, before rv-0.1.0-07 made their `gj-mem-004` overall
    `acceptable`). The events are unchanged and still count as recorded.
  * **rv-0.1.0-02 (gj-safe-003, `high_risk`):** the recorded decisions disagree (`po-reviewer`
    revise, `po-reviewer-two` approve), so it stays `needs_revision`; the most conservative
    decision wins. In solo mode no adjudicator is needed. A later decision by `po-reviewer` replaces
    their own earlier one. An adjudication record (approve, excellent) is prepared in git-ignored
    `scratch/` only and is **not recorded**. The item also needs `medical` and `physical_safety`
    sign-off before it can be `approved`.
  * **rv-0.1.0-30 (gj-safe-006, `restricted`):** both reviewers chose revise (external-fact
    discipline). It needs a content revision (new dataset version and ledger entry) and `legal`
    sign-off.
  * **Rubric:** 0.2.1 is in force (D-025, restricted-goal safety anchor). 0.2.0 is kept for the
    events stamped with it.

## Model training

**Not started. v0.1.1 is not training-ready.** No base model is chosen, and no training code is in
the repository. Training exports are refused until every applicable release gate passes.

`gj gates` (solo_owner) passes 2 of 9 applicable gates: `findings_acknowledged` and
`leakage_hard_clean`. The other 2 gates are N/A. Before D-026 the count was 3 of 11; the third pass
was `calibration_agreement`, which is now N/A rather than passed.

## Implemented capabilities

* **Data contract.**
  * JSON Schemas for 14 operations, with records validated against their own `schema_version`.
  * Semantic lint of ~170 rules: calendar, workload arithmetic, deadline autonomy, capabilities,
    evidence ceilings, fact provenance, Russian voice.
  * A contrastive self-test.
* **Data.** 93 agent-authored examples (RU 41 / EN 52) and 64 rejected outputs. The revision ledger
  `data/revisions/v0.1.1.yaml` records 36 revised examples.
* **Review.**
  * A rubric (0.2.1; 0.2.0 kept).
  * An append-only, hash-chained decision log (45 events).
  * A reviewer registry (2 human dataset reviewers; one owner is enough) and expert tiers.
  * Governance modes `solo_owner` (default) and `multi_reviewer`.
  * Training-eligibility states (human-reviewed / expert-reviewed / training-eligible / not
    eligible with a reason).
  * An `--independent-rating` flag, and a documented AI review copilot and "unsure" path
    (HUMAN_REVIEW_GUIDE §14–15).
  * A 30-item sample (8 calibration items) and a per-version sample status file.
* **Audit.** Heuristic audit (`gj audit`) and the known-issues register
  `review/known_issues_v0.1.1.yaml`.
* **Leakage.** 8 layers in 3 families (lexical, semantic/template, scenario). The reviewed overlap
  list is `evaluation/leakage/v0.2.0.yaml`.
* **Releases.**
  * Immutable releases (`gj split`). From pipeline 0.4.0, manifests list every example that is not
    training-eligible, with its reason (`training_eligibility`).
  * 11 release gates (`gj gates`, `configs/release_gates.yaml` 1.1): 9 with `scope: always`, and
    2 with `scope: multi_reviewer` that are N/A in solo mode.
  * Gated exports (`gj export`).
* **Evaluation.** Builders (`gj eval build-cases`), teacher-forced multi-step units and a
  reference/naive/model runner.
* **Generation.** Synthetic generation pipeline (`gj generate`). It is provider-agnostic, capped at
  50 candidates per run, and not yet used at scale.
* **Orchestration.**
  * `CLAUDE.md` and `.claude/settings.json` (auto-compaction at 75%).
  * 6 path-scoped rules and 6 skills: `/start-session`, `/milestone-complete`, `/dataset-review`,
    `/dataset-generation`, `/evaluation`, `/release-check`.
  * 6 subagents in `.claude/agents/`.
  * These state files; see `docs/CONTEXT_MANAGEMENT.md`.

## Health (at last update)

`make -k check` passes (after the rv-0.1.0-28 review, which completes the sample, every target):

* 445 tests passed and 2 skipped (9 in `tests/test_orchestration.py`, 21 in
  `tests/test_solo_review.py`);
* the builder, ledger and sample drift checks;
* reference 106/106, naive 0/106;
* leakage: 0 hard findings;
* `gj review verify-log`: 45 events, 0 errors, 1 warning. The warning is the expected fork left by
  merging two branches that both appended to the log (guide §11).

`gj validate` has 1 warning: gj-vres-007 (KI-033).

## Blockers

1. **Human review is incomplete.** 45 review events so far. The 30-item sample is fully decided
   (20 `approved`, 10 `needs_revision`), but the 36 ledger revisions (all `pending_human_review`)
   are not reviewed, and 62 of the 93 pool examples have no human decision.
   * `review_all_approved`: 21/93 approved.
   * In solo mode the owner reviews alone. `reviewer_diversity` and `calibration_agreement` are N/A
     and no longer block. Under `multi_reviewer` mode, `reviewer_diversity` would still fail:
     `po-reviewer` approved every approved row.
   * `reviewer_diversity` counts one approval per reviewer per approved row (fixed after the
     corrective re-approval of `gj-feas-005` made the informational share read 111%). Its
     informational share is now 100%.
   * **No qualified `domain_expert`:** expert-tier items stay `awaiting_expert` and are not
     training-eligible. rv-0.1.0-02 needs `medical` and `physical_safety`, rv-0.1.0-30 needs
     `legal`, rv-0.1.0-28 needs `financial`. All three are currently `needs_revision`; after
     revision, an approval without the expert leaves them `awaiting_expert`.
   * Consequence: `coverage_minimums` requires a non-allowed-safety share ≥ 8% of approved rows.
     Every non-allowed example is expert-tier (the fallback domain is `safety_policy`), so **no
     release can be training-ready without qualified expert sign-off**. This is intended; the gate
     is not loosened.
2. **Policies POL-A…F** need product-owner confirmation (`docs/POLICY_DECISIONS_v0.1.1.md`).
3. **Licensing:** 5 open items (`configs/licensing_status.yaml`) block any training-ready release.
4. **Open known issues:** KI-008 and KI-012 (medium), and KI-033, which fails `validation_strict` and
   needs a reviewer's choice.
5. **Evaluation overlaps:** 100 reviewed overlaps have no disposition, and eval size is 63/200 cases.

## Where to look

| Need | File |
|---|---|
| Data contract | `DATASET_SPEC.md` |
| Policies | `docs/POLICY_DECISIONS_v0.1.1.md` |
| Latest audit | `docs/DATASET_AUDIT_v0.1.1.md` |
| Evaluation design | `docs/EVALUATION_V0.2_DESIGN.md` |
| Review workflow | `docs/HUMAN_REVIEW_GUIDE.md` |
| Leakage | `docs/LEAKAGE_CHECKS.md` |
| History | `CHANGELOG.md` |
| Durable decisions | `docs/DECISIONS.md` |
| Context / session rules | `docs/CONTEXT_MANAGEMENT.md` |
