# Leakage checks — what they can and cannot establish

`gj leakage` runs eight layers between the training pool, the evaluation cases and the scenario
seeds. From evaluation v0.2.0, each step of a multi-step case is checked as its own unit
(`<case_id>/<step_id>`), and the report groups the layers into three families:

* **lexical**: L1–L4, wording;
* **semantic/template**: L5, L8, plus the human-reviewed overlap list — the same decision structure
  behind different words;
* **scenario**: L6, L7 — the same scenario or seed on both sides.

Each family's report line states what the family cannot establish. `gj split` aborts a release on any **hard** finding, and the release gates additionally
require a human disposition for every reviewed overlap (`configs/release_gates.yaml`).

**No combination of these checks can show that there is no leakage.** They can show that some
specific kind of leakage *exists*. A clean report means "none of these eight narrow tests fired",
nothing more. Every statement in the repository about leakage is phrased that way.

## Layers

| Layer | What it compares | Blocks? | Can detect | Cannot detect |
|---|---|---|---|---|
| L1 `exact_input` | canonical JSON of the whole input (ignoring `today`), pool↔pool and pool↔eval | hard | copy-pasted situations | anything edited, even by one character |
| L2 `exact_output` | canonical JSON of expected outputs inside the pool | warning | copy-pasted answers | reworded answers |
| L3 `char_near_dup` | 5-character shingle Jaccard on the situation text (goal, user messages, evidence, events, task title) | hard ≥ 0.55 (pool↔eval); warning ≥ 0.70 (within pool) | shared wording | paraphrases (hand-made paraphrases of eval inputs score 0.17–0.34), translations |
| L4 `lexical_para` | TF-IDF cosine over stemmed content words (5-char prefix stemming, RU+EN stop words) | hard ≥ 0.50; warning ≥ 0.30 | same-language paraphrases that keep the content words (0.55–0.84 on the test paraphrases) | translations, re-told situations with different vocabulary, same behaviour in a new domain |
| L5 `template` | same *behavioural signature* (operation, events, trigger, status/classification/intent/category, deadline flexibility, time up/down, retry, retrieved memory) **and** shared numbers (Jaccard ≥ 0.5) or lexical ≥ 0.15 | warning, needs a disposition | the same decision structure with the same numbers or vocabulary | cross-lingual twins, re-numbered twins, templates whose signature fields differ |
| L6 `scenario_group` | scenario groups: train↔validation (from the release manifest), pool↔eval (evaluation metadata), and registry sides (a training row on an eval-side scenario or vice versa) | hard | a scenario that straddles splits or sides | two different groups that describe the same scenario |
| L7 `seed` | seed ids used by generated examples vs eval `seed_origin`; seed text vs eval inputs (TF-IDF) | hard (ids); warning ≥ 0.30 (text) | seed reuse; seeds that mirror an eval case before generation starts | seeds that were never recorded; eval cases derived informally from a seed |
| L8 `decision_pattern` | behavioural-scenario registry patterns `operation\|trigger\|condition\|decision`: each eval unit (the case's scenario, or a step's `step_pattern`) vs every training scenario | hard if identical; warning if same operation and condition/decision term Jaccard ≥ 0.5 | reused or similarly labelled decision patterns | the same decision described with different labels (labels are written by the author) |

## How the thresholds were chosen (v0.1.0)

From `gj leakage --distribution` on the 93 examples, 30 evaluation cases and 30 seeds:

| Distribution | n | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| lexical, pool vs eval | 2,790 | 0.000 | 0.062 | 0.133 | 0.374 |
| lexical, within pool (distinct scenarios) | 4,278 | 0.000 | 0.062 | 0.120 | 0.376 |
| lexical, seed vs eval | 900 | 0.000 | 0.056 | 0.118 | 0.372 |
| character shingles, pool vs eval | 2,790 | 0.000 | 0.038 | 0.073 | 0.221 |

Three hand-made same-language paraphrases of evaluation inputs scored 0.55, 0.56 and 0.84 on L4 but
only 0.17–0.34 on L3. The L4 hard threshold (0.50) therefore sits between the largest similarity
seen between *different* authored scenarios (0.376) and the smallest seen for a paraphrase (0.554).
The warning threshold (0.30) is ~2× the p99 of unrelated pairs and surfaces the three most similar
pairs for a manual look. These numbers come from one small, single-author corpus; recompute them
(`--distribution`) at every scale-up step, especially once generated candidates arrive.

The L3 threshold (0.55) is unchanged from v0.1.0 and remains useful only for copy-paste-level reuse.

## What v0.1.0 actually shows

* L1–L4, L6, L7 (ids): **no hard finding**. Highest similarities: lexical 0.374, character 0.221.
* L4 warnings: 3 pairs (`gj-vprot-005`~`ev-vr-02`, `gj-vretry-003`~`ev-vr-01`, `gj-feas-006`~`ev-ra-02`).
* L7 warning: seed `sc-pd-001` ("Read 24 books this year") mirrors `ev-wr-02` ("Read 12 books by the
  end of next year"). Every candidate generated from that seed would mirror the evaluation case —
  change the seed or the case before scale-up.
* **Manual review found 27 evaluation↔training behavioural overlaps (11 strong, 13 medium, 1 topic-only,
  2 coincidental)**, recorded in [`evaluation/leakage/v0.1.0.yaml`](../evaluation/leakage/v0.1.0.yaml).
  The automated template layer flagged 5 candidates. Two matched pairs found by hand, one was a
  genuine overlap the manual pass had missed (`ev-q-01`~`gj-clar-002`), and two were coincidental
  (shared numbers only). It missed 32 of the 34 train/eval pairs found by hand. 8 of the overlaps are
  cross-lingual (e.g. `ev-v-02` RU vs `gj-vprot-005` EN), and no text-similarity layer can see those.
  The strongest example is `ev-ra-01` vs `gj-time-003`: near-parallel user messages ("≈3 h/week,
  fixed date that cannot move").

The conclusion is not "no leakage". It is: **no copy-level or paraphrase-level leakage was
detected, and the evaluation set substantially re-tests the training set's behavioural templates.**
Until the dispositions are decided and the expansion plan is followed, v0.1.0 evaluation results
measure recall of practised templates more than generalisation.

## What evaluation v0.2.0 shows

From `gj leakage --distribution` on 93 examples, 63 cases (106 units) and 30 training seeds:

* **Lexical: 0 hard.** Max pool↔eval lexical similarity is 0.338, and character similarity 0.139.
  One warning: `gj-daily-003`~`e2-gc-02` (0.34), two conversational-language goals.
* **Semantic/template: 0 hard.** There are 13 automated candidates (11 template, 2 decision pattern),
  and every one is in the reviewed list.
* **Scenario: 0 hard, 0 warnings.** Every case has its own eval-side scenario; seed ids and seed text
  are clear.
* **The manual review** read every case and step against all 92 training scenarios.
  * Before release, it rewrote three atomic cases that repeated a training decision pattern. It also
    moved five cases whose topic repeated a training example or a training seed to new topics.
  * It records 100 remaining overlaps in
    [`evaluation/leakage/v0.2.0.yaml`](../evaluation/leakage/v0.2.0.yaml): 11 strong (all set-up or
    intermediate steps of multi-step cases), 78 medium, 4 topic-only and 7 coincidental. 46 of the
    100 are cross-lingual.
  * The automated layers found **13 of the 116** reviewed (unit, training example) pairs.

The conclusion is the same kind as for v0.1.0, and not "no leakage". No copy- or paraphrase-level
leakage was detected. Most evaluation units test trained behaviours under a different decisive
condition. The strong overlaps are listed, and all 100 still need a human disposition.

## Evaluation metadata

`evaluation/leakage/v<eval_version>.yaml` sits outside the case files, so adding provenance does not
change released test data. For v0.2.0, its `cases:` block is generated by `gj eval build-cases`; the
overlap lists below it are maintained by hand and preserved on regeneration. It holds, per case, `scenario_group`, `behavior_template`, `seed_origin`
and `author`. It also holds the reviewed `template_overlaps` and `seed_overlaps`, each with a
`proposed_disposition` (the agent's suggestion) and a `disposition` that stays `open` until a person
decides:

| disposition | meaning |
|---|---|
| `open` | nobody has decided yet (blocks `training_ready`) |
| `accept_in_distribution` | keep; report the case in the in-template metric slice |
| `rewrite_eval_case` / `rewrite_training_example` | decided; rewrite pending (blocks until done) |
| `resolved` | the rewrite was done and the overlap no longer holds |

## Adding stronger checks later

At scale (thousands of candidates), add in this order:

1. **MinHash/LSH** for L3/L4, to keep pairwise comparison tractable.
2. **Multilingual sentence embeddings** (for example, a local open-weight encoder) for a
   cross-lingual paraphrase layer. Calibrate it the same way: unrelated-pair distribution plus
   constructed paraphrases and translations.
3. **Structural fingerprints**: node-graph shape, event sequence and numeric pattern, to strengthen L5.
4. A **held-out authoring process** for evaluation cases (different authors, seeds and teacher
   model; see `docs/EVALUATION_EXPANSION_PLAN.md`). No detector substitutes for independent authorship.
