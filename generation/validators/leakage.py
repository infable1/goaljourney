"""Layered leakage and duplication checks between the training pool, evaluation cases and seeds.

Each layer answers one narrow question. None of them — alone or together — proves the absence of
leakage; see docs/LEAKAGE_CHECKS.md for what each layer can and cannot establish.

Layers
  L1 exact_input      identical input contexts (canonical JSON, `today` ignored)          -> hard
  L2 exact_output     identical expected outputs inside the pool                          -> warning
  L3 char_near_dup    character-shingle Jaccard on the situation text (existing guard)     -> hard
  L4 lexical_para     TF-IDF cosine over stemmed content words (paraphrase proxy)         -> hard / warning
  L5 template         same behavioural signature + overlapping numbers or vocabulary      -> warning (needs a human disposition)
  L6 scenario_group   scenario groups disjoint between train/validation and evaluation    -> hard
  L7 seed             training seeds vs evaluation cases (seed ids and seed text)         -> hard (ids) / warning (text)
  L8 decision_pattern registry decision patterns (operation|trigger|condition|decision): an evaluation unit whose
                      pattern equals a training pattern -> hard; same operation and similar condition/decision
                      vocabulary -> warning (needs a human disposition)

Families (how the report groups the layers; eval v0.2.0):
  lexical            L1-L4  wording: identical, near-identical or paraphrased text
  semantic_template  L5, L8 the same decision structure behind different words (behaviour signature, decision
                            pattern); plus the human-reviewed overlap list in evaluation/leakage/
  scenario           L6, L7 the same underlying scenario or seed on both sides

Evaluation cases with `steps` (composite / longitudinal) are checked per unit: each step is compared
with the pool on its own input, id `<case_id>/<step_id>`.
"""
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field

from gjcore.io import canonical_json, sha256_text

from . import similarity

# ---------------------------------------------------------------------------------------------
# Text normalisation for the lexical layer

_STOP = set("""
a an the and or but if of to in on at for with from by as is are was were be been being it its this that these those
i me my we our you your he she they them their his her him not no do does did can could will would should may might
have has had just so than then there here what which who whom how when where why about into over under up down out
all any some more most very also only even much many one two three about per via let get got like want need make
и в во на с со к ко по о об от до за из у же ли не ни но а что как так это этот эта эти то та те тот для при без
над под или да нет уже ещё еще бы был была было были быть есть я мы вы ты он она они мне меня мой моя мои наш ваш
ваша ваши вам вас их его ее её им ним них себя свой своя свои который которая которые чтобы если когда где там тут
очень только тоже также всё все всего можно нужно надо хочу хочет хотим хотите
""".split())

_WORD = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)
_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _stem(word: str) -> str:
    """Crude language-agnostic stemming: a 5-character prefix merges most inflections
    (выпустить/выпуск, learning/learned) at the cost of some collisions."""
    return word[:5] if len(word) > 5 else word


def content_tokens(text: str):
    toks = []
    for w in _WORD.findall((text or "").lower()):
        if w in _STOP or w.isdigit() or len(w) < 3:
            continue
        toks.append(_stem(w))
    return toks


def numbers(text: str) -> frozenset:
    """Numbers as they appear in the situation (thousand separators removed)."""
    t = re.sub(r"(?<=\d)[\s ](?=\d{3}\b)", "", text or "")
    return frozenset(n.replace(",", ".") for n in _NUM.findall(t))


class TfIdf:
    def __init__(self, docs):
        self.df = Counter()
        tokenised = [content_tokens(d) for d in docs]
        for toks in tokenised:
            self.df.update(set(toks))
        self.n = max(len(docs), 1)

    def vector(self, text):
        tf = Counter(content_tokens(text))
        vec = {t: (1 + math.log(c)) * math.log((1 + self.n) / (1 + self.df.get(t, 0)) + 1) for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}


def cosine(a: dict, b: dict) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())


# ---------------------------------------------------------------------------------------------
# Behavioural signature: what the example is *about*, independent of its wording.

def behaviour_signature(task_type: str, inp: dict, out: dict | None) -> tuple:
    out = out or {}
    goal = inp.get("goal") or {}
    tb = inp.get("time_budget") or {}
    parts = [task_type]
    parts.append("events:" + ",".join(sorted(e.get("type", "") for e in inp.get("events") or [])))
    trig = (out.get("trigger") or {}).get("type")
    for key, val in (("trigger", trig), ("status", out.get("status")), ("classification", out.get("classification")),
                     ("intent", out.get("intent")), ("category", out.get("category")),
                     ("change_level", out.get("change_level")), ("needs_research", out.get("needs_research")),
                     ("ready_to_plan", out.get("ready_to_plan"))):
        if val is not None:
            parts.append(f"{key}:{val}")
    if goal.get("deadline_flexibility"):
        parts.append("deadline:" + goal["deadline_flexibility"])
    if tb.get("previous_hours_per_week") and tb.get("hours_per_week"):
        parts.append("hours:" + ("down" if tb["hours_per_week"] < tb["previous_hours_per_week"] else "up"))
    if inp.get("verification_history"):
        parts.append("retry")
    if inp.get("retrieved_memory"):
        parts.append("retrieved_memory")
    return tuple(parts)


# ---------------------------------------------------------------------------------------------
# Decision patterns (behavioural scenario registry)

LAYER_FAMILY = {"exact_input": "lexical", "exact_output": "lexical", "char_near_dup": "lexical",
                "lexical_para": "lexical", "template": "semantic_template", "decision_pattern": "semantic_template",
                "scenario_group": "scenario", "seed": "scenario"}
_PATTERN_STOP = {"and", "or", "with", "no", "not", "of", "to", "the", "a", "in", "on", "for", "by", "then", "than",
                 "only", "first", "all", "one"}


def scenario_pattern(s: dict) -> str:
    return "|".join(s.get(k, "") for k in ("operation", "trigger", "condition", "decision"))


def pattern_tokens(pattern: str) -> frozenset:
    """Content tokens of a pattern's condition and decision ('fixed_deadline+uncuttable_work' -> {fixed, deadline, ...})."""
    parts = pattern.split("|")
    words = re.split(r"[_+\-]", "_".join(parts[2:4])) if len(parts) >= 4 else []
    return frozenset(w for w in words if w and w not in _PATTERN_STOP)


def unit_patterns(units, registry):
    """[(unit_id, pattern)] for evaluation units: a step's `step_pattern`, otherwise the pattern of the case's
    scenario in the registry. Units without either are skipped (reported by the caller as unchecked)."""
    by_id = {s["id"]: s for s in registry or []}
    out = []
    for u in units:
        pat = u.get("step_pattern")
        if not pat and not u.get("step_id"):
            sc = by_id.get(u.get("scenario_group"))
            pat = scenario_pattern(sc) if sc else None
        if pat:
            out.append((u["id"], pat))
    return out


def pattern_findings(train_patterns, eval_patterns, threshold):
    """L8: compare evaluation unit patterns with training scenario patterns. Returns (findings, best score per unit)."""
    findings, best = [], {}
    train = [(tid, pat, pat.split("|")[0], pattern_tokens(pat)) for tid, pat in train_patterns]
    for uid, upat in eval_patterns:
        op, toks = upat.split("|")[0], pattern_tokens(upat)
        top = (0.0, None)
        for tid, tpat, top_op, ttoks in train:
            if tpat == upat:
                findings.append(Finding("decision_pattern", "hard", tid, uid, 1.0, f"identical decision pattern {upat}"))
                continue
            if top_op != op or not toks or not ttoks:
                continue
            j = len(toks & ttoks) / len(toks | ttoks)
            if j > top[0]:
                top = (round(j, 3), tid)
            if j >= threshold:
                shared = ",".join(sorted(toks & ttoks))
                findings.append(Finding("decision_pattern", "warning", tid, uid, round(j, 3),
                                        f"same operation {op}; shared condition/decision terms: {shared}"))
        best[uid] = top
    return findings, best


def registry_findings(registry, pool, cases):
    """L6 (registry side): training rows must use side=train scenarios, evaluation cases side=eval ones."""
    by_id = {s["id"]: s for s in registry or []}
    out, notes = [], []
    for r in pool:
        s = by_id.get(r.get("scenario_group"))
        if s and s["side"] != "train":
            out.append(Finding("scenario_group", "hard", r["scenario_group"], r["id"], None,
                               "training example uses an evaluation-side scenario"))
    unregistered = []
    for c in cases:
        g = c.get("scenario_group")
        if not g:
            continue
        s = by_id.get(g)
        if s is None:
            unregistered.append(c["id"])
        elif s["side"] != "eval":
            out.append(Finding("scenario_group", "hard", g, c["id"], None, "evaluation case uses a training-side scenario"))
    if unregistered:
        notes.append(f"{len(unregistered)} evaluation case(s) reference scenarios outside the registry "
                     f"({', '.join(unregistered[:5])}{'…' if len(unregistered) > 5 else ''}): their decision pattern is unchecked.")
    return out, notes


# ---------------------------------------------------------------------------------------------

@dataclass
class Finding:
    layer: str
    severity: str          # hard | warning
    a: str
    b: str
    score: float | None = None
    detail: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class LeakageReport:
    thresholds: dict
    counts: dict = field(default_factory=dict)
    findings: list = field(default_factory=list)
    max_scores: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)

    @property
    def hard(self):
        return [f for f in self.findings if f.severity == "hard"]

    @property
    def warnings(self):
        return [f for f in self.findings if f.severity == "warning"]

    def to_dict(self):
        return {"thresholds": self.thresholds, "counts": self.counts, "max_scores": self.max_scores,
                "hard": [f.to_dict() for f in self.hard], "warnings": [f.to_dict() for f in self.warnings],
                "notes": self.notes}


def _input_key(inp: dict) -> str:
    return sha256_text(canonical_json({k: v for k, v in inp.items() if k != "today"}))


def seed_text(seed: dict) -> str:
    parts = [seed.get("goal_seed", ""), seed.get("persona", "")]
    parts += list(seed.get("known_context") or []) + list(seed.get("twists") or [])
    return " ".join(p for p in parts if p)


def run_checks(pool, cases, cfg, eval_meta=None, seeds=None, splits=None, registry=None):
    """pool: [record]; cases: [evaluation unit] (an atomic case, or one step of a multi-step case with
    `case_id`); cfg: leakage config dict; eval_meta: {case_id: {scenario_group, seed_origin, ...}} from the
    evaluation sidecar; seeds: [scenario seed]; splits: {scenario_group: 'train'|'validation'} (optional);
    registry: behavioural scenario registry entries (optional, enables L8 and the registry side check)."""
    eval_meta = eval_meta or {}
    th = {
        "char_shingle_size": cfg["shingle_size"],
        "char_near_duplicate": cfg["near_duplicate_threshold"],
        "char_repetition_warning": cfg["repetition_warning_threshold"],
        "lexical_hard": cfg["lexical_hard_threshold"],
        "lexical_warning": cfg["lexical_warning_threshold"],
        "template_lexical": cfg["template_lexical_threshold"],
        "template_numeric": cfg["template_numeric_threshold"],
        "seed_lexical_warning": cfg["seed_lexical_warning_threshold"],
        "decision_pattern_warning": cfg.get("decision_pattern_warning_threshold", 0.5),
    }
    rep = LeakageReport(thresholds=th)
    k = th["char_shingle_size"]

    pool_sig = [(r["id"], similarity.signature_text(r["input"])) for r in pool]
    case_sig = [(c["id"], similarity.signature_text(c["input"])) for c in cases]

    # L1 exact inputs
    seen = {}
    for r in pool:
        key = _input_key(r["input"])
        if key in seen:
            rep.findings.append(Finding("exact_input", "hard", seen[key], r["id"], 1.0, "identical input inside the pool"))
        seen[key] = seen.get(key, r["id"])
    for c in cases:
        key = _input_key(c["input"])
        if key in seen:
            rep.findings.append(Finding("exact_input", "hard", seen[key], c["id"], 1.0, "training input identical to an evaluation input"))

    # L2 exact outputs
    outs = {}
    for r in pool:
        key = sha256_text(canonical_json(r.get("expected_output")))
        if key in outs:
            rep.findings.append(Finding("exact_output", "warning", outs[key], r["id"], 1.0, "identical expected outputs"))
        outs.setdefault(key, r["id"])

    # L3 character near-duplicates
    cross = similarity.cross_near_duplicates(pool_sig, case_sig, 0.0, k)
    rep.max_scores["char_pool_vs_eval"] = max((s for _, _, s in cross), default=0.0)
    for a, b, s in cross:
        if s >= th["char_near_duplicate"]:
            rep.findings.append(Finding("char_near_dup", "hard", a, b, s, "training input near-duplicates an evaluation input"))
    within = similarity.pairwise_near_duplicates(pool_sig, 0.0, k)
    rep.max_scores["char_within_pool"] = max((s for _, _, s in within), default=0.0)
    for a, b, s in within:
        if s >= th["char_repetition_warning"]:
            rep.findings.append(Finding("char_near_dup", "warning", a, b, s, "template repetition inside the pool"))

    # L4 lexical paraphrase proxy (shared IDF over pool + cases + seeds)
    seed_items = [(s["id"], seed_text(s)) for s in seeds or []]
    tfidf = TfIdf([t for _, t in pool_sig] + [t for _, t in case_sig] + [t for _, t in seed_items])
    pv = {i: tfidf.vector(t) for i, t in pool_sig}
    cv = {i: tfidf.vector(t) for i, t in case_sig}
    best_lex = 0.0
    lex_pairs = {}
    for pid, pvec in pv.items():
        for cid, cvec in cv.items():
            s = round(cosine(pvec, cvec), 3)
            lex_pairs[(pid, cid)] = s
            best_lex = max(best_lex, s)
            if s >= th["lexical_hard"]:
                rep.findings.append(Finding("lexical_para", "hard", pid, cid, s, "content-word overlap typical of a paraphrase"))
            elif s >= th["lexical_warning"]:
                rep.findings.append(Finding("lexical_para", "warning", pid, cid, s, "notable content-word overlap; check by hand"))
    rep.max_scores["lexical_pool_vs_eval"] = best_lex

    # L5 behavioural template overlap
    psig = {r["id"]: behaviour_signature(r["task_type"], r["input"], r.get("expected_output")) for r in pool}
    csig = {c["id"]: behaviour_signature(c["task_type"], c["input"], c.get("reference_output")) for c in cases}
    pnum = {i: numbers(t) for i, t in pool_sig}
    cnum = {i: numbers(t) for i, t in case_sig}
    n_template = 0
    for pid, ps in psig.items():
        for cid, cs in csig.items():
            if ps != cs:
                continue
            num_j = similarity.jaccard(pnum[pid], cnum[cid]) if pnum[pid] and cnum[cid] else 0.0
            lex = lex_pairs.get((pid, cid), 0.0)
            if num_j >= th["template_numeric"] or lex >= th["template_lexical"]:
                n_template += 1
                rep.findings.append(Finding(
                    "template", "warning", pid, cid, round(max(num_j, lex), 3),
                    f"same behavioural signature {'/'.join(ps[1:]) or ps[0]}; numbers jaccard {num_j:.2f}, lexical {lex:.2f}"))
    rep.counts["template_candidates"] = n_template

    # L6 scenario groups
    pool_groups = {r["scenario_group"] for r in pool}
    for cid, meta in eval_meta.items():
        g = (meta or {}).get("scenario_group")
        if g and g in pool_groups:
            rep.findings.append(Finding("scenario_group", "hard", g, cid, None, "evaluation case shares a scenario group with training"))
    missing_meta = sorted({c.get("case_id", c["id"]) for c in cases
                           if not (eval_meta.get(c.get("case_id", c["id"])) or {}).get("scenario_group")})
    if missing_meta:
        rep.notes.append(f"{len(missing_meta)} evaluation case(s) have no scenario_group metadata: scenario-level "
                         f"leakage cannot be checked for them ({', '.join(missing_meta[:5])}{'…' if len(missing_meta) > 5 else ''}).")
    if splits:
        by_split = {}
        for g, s in splits.items():
            by_split.setdefault(s, set()).add(g)
        both = by_split.get("train", set()) & by_split.get("validation", set())
        for g in sorted(both):
            rep.findings.append(Finding("scenario_group", "hard", g, g, None, "scenario group in both train and validation"))

    # L7 seeds
    train_seed_ids = {((r.get("provenance") or {}).get("scenario_id")) for r in pool} - {None}
    for cid, meta in eval_meta.items():
        origin = (meta or {}).get("seed_origin")
        if origin and origin in train_seed_ids:
            rep.findings.append(Finding("seed", "hard", origin, cid, None, "evaluation case derived from a seed used for training data"))
    best_seed = 0.0
    for sid, stext in seed_items:
        svec = tfidf.vector(stext)
        for cid, cvec in cv.items():
            s = round(cosine(svec, cvec), 3)
            best_seed = max(best_seed, s)
            if s >= th["seed_lexical_warning"]:
                rep.findings.append(Finding("seed", "warning", sid, cid, s, "training seed resembles an evaluation case; every candidate generated from it would too"))
    rep.max_scores["lexical_seed_vs_eval"] = best_seed

    # L8 decision patterns + registry sides
    if registry:
        case_groups = {c.get("case_id", c["id"]): c.get("scenario_group") or (eval_meta.get(c.get("case_id", c["id"])) or {}).get("scenario_group")
                       for c in cases}
        found, notes = registry_findings(registry, pool, [{"id": cid, "scenario_group": g} for cid, g in case_groups.items()])
        rep.findings += found
        rep.notes += notes
        train_patterns = [(s["id"], scenario_pattern(s)) for s in registry if s["side"] == "train"]
        eval_patterns = unit_patterns(cases, registry)
        found, best = pattern_findings(train_patterns, eval_patterns, th["decision_pattern_warning"])
        # report training examples, not scenario ids, so the findings line up with the reviewed overlap list
        examples = {}
        for r in pool:
            examples.setdefault(r.get("scenario_group"), []).append(r["id"])
        for f in found:
            for ex in examples.get(f.a) or [f.a]:
                rep.findings.append(Finding(f.layer, f.severity, ex, f.b, f.score, f"{f.detail} (training scenario {f.a})"))
        rep.max_scores["decision_pattern_eval_vs_train"] = max((b[0] for b in best.values()), default=0.0)
        unchecked = sorted({c["id"] for c in cases} - {u for u, _ in eval_patterns})
        if unchecked:
            rep.notes.append(f"{len(unchecked)} evaluation unit(s) have no decision pattern: L8 did not check them "
                             f"({', '.join(unchecked[:5])}{'…' if len(unchecked) > 5 else ''}).")
        rep.counts["decision_pattern_units"] = len(eval_patterns)

    rep.counts.update({"pool": len(pool), "eval_cases": len(cases), "seeds": len(seed_items),
                       "hard": len(rep.hard), "warnings": len(rep.warnings)})
    return rep


def distribution(pool, cases, seeds=None, k=5):
    """Similarity distributions used to justify thresholds (reported by `gj leakage --distribution`)."""
    pool_sig = [(r["id"], similarity.signature_text(r["input"])) for r in pool]
    case_sig = [(c["id"], similarity.signature_text(c["input"])) for c in cases]
    seed_items = [(s["id"], seed_text(s)) for s in seeds or []]
    tfidf = TfIdf([t for _, t in pool_sig] + [t for _, t in case_sig] + [t for _, t in seed_items])
    pv = [tfidf.vector(t) for _, t in pool_sig]
    cv = [tfidf.vector(t) for _, t in case_sig]
    sv = [tfidf.vector(t) for _, t in seed_items]
    lex_cross = sorted(cosine(a, b) for a in pv for b in cv)
    lex_within = sorted(cosine(pv[i], pv[j]) for i in range(len(pv)) for j in range(i + 1, len(pv)))
    lex_seed = sorted(cosine(a, b) for a in sv for b in cv)
    char_cross = sorted(s for _, _, s in similarity.cross_near_duplicates(pool_sig, case_sig, 0.0, k))

    def q(xs, p):
        return round(xs[min(len(xs) - 1, int(p * len(xs)))], 3) if xs else 0.0

    return {name: {"n": len(xs), "p50": q(xs, .5), "p95": q(xs, .95), "p99": q(xs, .99), "max": round(xs[-1], 3) if xs else 0.0}
            for name, xs in (("lexical_pool_vs_eval", lex_cross), ("lexical_within_pool", lex_within),
                             ("lexical_seed_vs_eval", lex_seed), ("char_pool_vs_eval", char_cross))}
