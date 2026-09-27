"""`gj leakage`: layered train/eval/seed leakage report (layers in generation/validators/leakage.py).

What the layers can and cannot establish is documented in docs/LEAKAGE_CHECKS.md. The report never
claims "no leakage": it lists what each layer checked, what it found, and which reviewed overlaps
still lack a human disposition.
"""
import json

from gjcore import schemas
from gjcore.config import load_config, versions
from gjcore.io import load_json, load_yaml
from gjcore.paths import rel, repo_path
from gjcore.records import load_eval_cases
from generation.validators import leakage as L

from .pool import load_pool

LAYER_LIMITS = {
    "exact_input": "catches byte-identical situations only",
    "exact_output": "catches copy-pasted answers only",
    "char_near_dup": "catches shared wording; misses paraphrases and translations",
    "lexical_para": "catches same-language paraphrases sharing content words; misses translations and re-told situations",
    "template": "flags same decision structure with overlapping numbers/words; misses cross-lingual and re-numbered templates",
    "scenario_group": "only as good as the scenario-group labels",
    "seed": "catches seed-id reuse and similar seed text; cannot see seeds that were never recorded",
    "decision_pattern": "compares hand-written registry labels: catches reused or similarly worded decision patterns; "
                        "misses the same decision described with different labels",
}
FAMILY_LIMITS = {
    "lexical": "wording only — a translated or re-told situation passes every lexical layer",
    "semantic_template": "automated proxies (behaviour signature, decision-pattern labels) plus the human-reviewed "
                         "overlap list; there is no embedding or cross-lingual semantic model, so absence of findings "
                         "here is not evidence of independence",
    "scenario": "scenario-group and seed ids are labels assigned by the author; they are only as good as that labelling",
}


def load_eval_metadata(version=None):
    version = version or versions()["evaluation_version"]
    d = repo_path(load_config("dataset")["leakage"]["eval_metadata_dir"]) / f"v{version}.yaml"
    if not d.exists():
        return {"eval_version": version, "cases": {}, "template_overlaps": [], "seed_overlaps": []}, [f"{rel(d)} missing"]
    meta = load_yaml(d) or {}
    return meta, [f"{rel(d)}: {e}" for e in schemas.validate("eval_leakage_metadata", meta)]


def load_seeds():
    out = []
    for p in sorted(repo_path("generation/scenarios").glob("*.yaml")):
        out += (load_yaml(p) or {}).get("scenarios") or []
    return out


def load_registry():
    p = repo_path("data/scenarios/behavioural_scenarios.yaml")
    return (load_yaml(p) or {}).get("scenarios") or [] if p.exists() else []


def _units(cases):
    from evaluation.metrics.scoring import expand_units
    return [u for c in cases for u in expand_units(c)]


def _release_splits(version=None):
    from .split import release_paths
    mp = release_paths(version or versions()["dataset_version"])["manifest"]
    if not mp.exists():
        return None
    return {e["scenario_group"]: e["split"] for e in load_json(mp).get("examples", [])}


def build(version=None):
    cfg = load_config("dataset")["leakage"]
    pool = [r for r, _, _ in load_pool()]
    cases = [c for c, _ in load_eval_cases(repo_path(load_config("evaluation")["cases_dir"]))]
    units = _units(cases)
    meta, problems = load_eval_metadata()
    seeds = load_seeds()
    rep = L.run_checks(pool, units, cfg, eval_meta=meta.get("cases") or {}, seeds=seeds, splits=_release_splits(version),
                       registry=load_registry())
    reviewed = {}
    for o in meta.get("template_overlaps") or []:
        for t in o["train"]:
            reviewed[(o["eval"], t)] = o
    auto_pairs = set()
    for f in rep.findings:
        if f.layer in ("template", "decision_pattern") and f.severity == "warning":
            # a reviewed entry may name the step (`e2-comp-04/s1`) or the whole case (`e2-comp-04`)
            key = (f.b, f.a) if (f.b, f.a) in reviewed else (f.b.split("/")[0], f.a)
            auto_pairs.add(key)
            o = reviewed.get(key)
            f.detail += f"; reviewed: {o['strength']}, disposition {o['disposition']}" if o else "; NOT in the reviewed overlap list"
    seed_reviewed = {(s["seed"], s["eval"]): s for s in meta.get("seed_overlaps") or []}
    for f in rep.findings:
        if f.layer == "seed" and f.severity == "warning":
            s = seed_reviewed.get((f.a, f.b))
            f.detail += f"; reviewed, disposition {s['disposition']}" if s else "; NOT in the reviewed seed-overlap list"
    overlaps = meta.get("template_overlaps") or []
    families = {}
    for fam in ("lexical", "semantic_template", "scenario"):
        fs = [f for f in rep.findings if L.LAYER_FAMILY.get(f.layer) == fam]
        families[fam] = {"layers": [k for k, v in L.LAYER_FAMILY.items() if v == fam], "hard": sum(1 for f in fs if f.severity == "hard"),
                         "warnings": sum(1 for f in fs if f.severity == "warning"), "limit": FAMILY_LIMITS[fam]}
    families["semantic_template"]["reviewed_overlaps"] = len(overlaps)
    summary = {
        "families": families,
        "eval_units": len(units),
        "reviewed_template_overlaps": len(overlaps),
        "reviewed_by_strength": {k: sum(1 for o in overlaps if o["strength"] == k) for k in ("strong", "medium", "topic_only", "none")},
        "cross_lingual_overlaps": sum(1 for o in overlaps if o.get("cross_lingual")),
        "open_dispositions": sum(1 for o in overlaps if o["disposition"] == "open")
                             + sum(1 for s in meta.get("seed_overlaps") or [] if s["disposition"] == "open"),
        "auto_template_candidates": len(auto_pairs),
        "auto_candidates_confirmed_by_review": len(auto_pairs & set(reviewed)),
        "reviewed_overlaps_missed_by_auto": len(set(reviewed) - auto_pairs),
        "unreviewed_auto_candidates": sorted(f"{b}~{a}" for b, a in auto_pairs - set(reviewed)),
        "eval_cases_without_metadata": sorted(c["id"] for c in cases if c["id"] not in (meta.get("cases") or {})),
    }
    return rep, summary, problems


def run(as_json=False, distribution=False, out=None):
    rep, summary, problems = build()
    payload = {**rep.to_dict(), "review_summary": summary, "metadata_problems": problems}
    if distribution:
        pool = [r for r, _, _ in load_pool()]
        cases = _units([c for c, _ in load_eval_cases(repo_path(load_config("evaluation")["cases_dir"]))])
        payload["distribution"] = L.distribution(pool, cases, load_seeds(), load_config("dataset")["leakage"]["shingle_size"])
    if out:
        p = repo_path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print(rep, summary, problems, payload.get("distribution"))
    return 1 if rep.hard or problems else 0


def _print(rep, summary, problems, dist=None):
    c = rep.counts
    print(f"Leakage checks: pool {c['pool']}, eval units {c['eval_cases']} ({summary.get('eval_units', c['eval_cases'])} model "
          f"calls), seeds {c['seeds']} -> {c['hard']} hard finding(s), {c['warnings']} warning(s)")
    print("These layers can show that leakage EXISTS; none of them can show that it does not (docs/LEAKAGE_CHECKS.md).\n")
    for fam, info in (summary.get("families") or {}).items():
        print(f"== {fam}: {info['hard']} hard, {info['warnings']} warning(s) — layers {', '.join(info['layers'])}")
        print(f"   limit: {info['limit']}")
    print()
    for layer, limit in LAYER_LIMITS.items():
        fs = [f for f in rep.findings if f.layer == layer]
        hard = sum(1 for f in fs if f.severity == "hard")
        print(f"[{layer}] {len(fs)} finding(s) ({hard} hard) — {limit}")
        for f in fs[:12]:
            score = f" {f.score}" if f.score is not None else ""
            print(f"    {f.severity:7} {f.a} ~ {f.b}{score}: {f.detail}")
        if len(fs) > 12:
            print(f"    … {len(fs) - 12} more (--json)")
    print(f"\nMax similarities: {rep.max_scores}")
    for n in rep.notes:
        print(f"note: {n}")
    s = summary
    print(f"\nReviewed template overlaps (evaluation/leakage/): {s['reviewed_template_overlaps']} "
          f"{s['reviewed_by_strength']}, {s['cross_lingual_overlaps']} cross-lingual, {s['open_dispositions']} without a human disposition")
    print(f"Automated template layer: {s['auto_template_candidates']} candidate(s), {s['auto_candidates_confirmed_by_review']} match the "
          f"reviewed list, {s['reviewed_overlaps_missed_by_auto']} reviewed overlap(s) it did not find")
    if s["unreviewed_auto_candidates"]:
        print(f"Unreviewed automated candidates: {', '.join(s['unreviewed_auto_candidates'])}")
    if s["eval_cases_without_metadata"]:
        print(f"Eval cases without metadata: {s['eval_cases_without_metadata']}")
    if dist:
        print("\nSimilarity distributions (for threshold rationale):")
        for k, v in dist.items():
            print(f"  {k:24} n={v['n']:5} p50={v['p50']} p95={v['p95']} p99={v['p99']} max={v['max']}")
    for p in problems:
        print(f"✗ {p}")
