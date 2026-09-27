"""`gj review sample`: deterministic review sample -> review/review_manifest_v<ver>.json

Strata (configs/review.yaml → sampling), drawn in this order:
  random        uniform seeded draw from the WHOLE pool — an unbiased estimate of the pool's defect rate
  highest_risk  highest risk score (audit findings + known issues + expert tier + difficulty + mixed input)
  contrastive   greedy cover of distinct failure modes among examples with rejected outputs
  edge          greedy cover of rare situations (mixed language, memory isolation, retries, tiny goals …)
Every coverage category must appear at least once; gaps are repaired by swapping targeted-stratum items
(never `random`) and each swap is recorded. A calibration subset (reviewed by every reviewer first)
is chosen for diversity. The same pool + findings + config always give byte-identical output.
"""
import hashlib
import json
from collections import Counter

from gjcore import schemas
from gjcore.config import versions
from gjcore.io import canonical_json, dump_json, load_json, sha256_text
from gjcore.paths import rel, repo_path
from gjcore.records import content_hash

from . import audit
from . import review_store as RS
from .pool import load_pool

STRATUM_RATIONALE = {
    "random": "Seeded uniform draw from the whole pool, taken first so it stays unbiased: it estimates how often a "
              "reviewer finds problems in an arbitrary example (with n=12 only roughly — ±25 points).",
    "highest_risk": "Highest risk score (automated audit findings, known issues, expert tier, hard difficulty, mixed input). "
                    "Finds the worst problems fast; details are hidden from the manifest to keep ratings independent.",
    "contrastive": "Examples with rejected outputs, chosen to cover as many distinct failure modes as possible — rejected "
                   "outputs become preference pairs, so their labels and plausibility must be right.",
    "edge": "Rare situations (mixed language, memory isolation, retries, tiny goals, restricted safety, rare operations) "
            "that get the least author attention and are easy to get subtly wrong.",
}

RARE_OPERATIONS = {"memory_extraction", "progress_update", "goal_change"}


def _rank(seed, key):
    return hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()


def coverage_tags(r) -> set:
    tt, b = r["task_type"], set(r.get("behavior") or [])
    out, inp = r.get("expected_output") or {}, r.get("input") or {}
    tags = {
        "goal_clarification": tt == "goal_clarification",
        "feasibility": tt == "feasibility_assessment",
        "journey": tt == "journey_generation",
        "task_generation": tt == "task_generation",
        "verification_protocol": tt == "verification_protocol_design",
        "verification_decision": tt == "verification_result" and not inp.get("verification_history"),
        "verification_retry": "verification_retry" in b,
        "route_adaptation": tt == "route_adaptation" and "time_adaptation" not in b,
        "navigator": tt == "navigator_response",
        "daily_prioritization": tt == "daily_plan",
        "time_adaptation": "time_adaptation" in b,
        "goal_change": tt == "goal_change",
        "web_research": tt == "web_research_decision",
        "decision_summary": "decision_summary" in b or bool(out.get("decision_summary")),
        "memory": "memory" in b or tt == "memory_extraction",
        "progress": tt == "progress_update",
        "safety": "safety" in b or tt == "safety_classification",
        "russian": r.get("language") == "ru",
        "english": r.get("language") == "en",
        "mixed_language": r.get("input_language") == "mixed",
        "contrastive": bool(r.get("contrastive")),
    }
    return {k for k, v in tags.items() if v}


def edge_features(r) -> set:
    out, inp = r.get("expected_output") or {}, r.get("input") or {}
    tb = inp.get("time_budget") or {}
    feats = {
        "mixed_language": r.get("input_language") == "mixed",
        "memory_isolation": bool(inp.get("retrieved_memory")),
        "retry": bool(inp.get("verification_history")),
        "tiny_goal": r.get("goal_size") == "tiny",
        "restricted_or_high_risk": r.get("safety_category") in ("restricted", "high_risk"),
        "rare_operation": r["task_type"] in RARE_OPERATIONS,
        "tiny_time_budget": (tb.get("available_minutes_today") or 999) <= 15,
        "fixed_deadline": (inp.get("goal") or {}).get("deadline_flexibility") == "fixed",
        "hearsay": bool(out.get("unsupported_claims")),
        "user_pushback": out.get("intent") in ("decline_task", "remove_milestone", "reschedule", "request_alternative"),
        "off_topic": out.get("in_scope") is False,
        "no_questions_needed": r["task_type"] == "goal_clarification" and out.get("ready_to_plan") is True,
    }
    return {k for k, v in feats.items() if v}


def _counts(size, strata):
    raw = [(s["name"], s["share"] * size) for s in strata]
    base = {n: int(x) for n, x in raw}
    rest = size - sum(base.values())
    for n, x in sorted(raw, key=lambda t: (-(t[1] - int(t[1])), t[0]))[:rest]:
        base[n] += 1
    return base


def build_manifest(version=None, records=None, findings=None, known=None, cfg=None):
    version = version or versions()["dataset_version"]
    rcfg = cfg or RS.review_config()
    scfg, weights = rcfg["sampling"], rcfg["risk_weights"]
    seed, size = scfg["seed"], scfg["size"]
    if records is None:
        pool = load_pool()
        records = [r for r, _, _ in pool]
        sources = {r["id"]: rel(p) for r, p, _ in pool}
    else:
        sources = {r["id"]: r.get("_source", "") for r in records}
    records = sorted(records, key=lambda r: r["id"])
    by_id = {r["id"]: r for r in records}
    findings = audit.run_audit(records) if findings is None else findings
    known = audit.load_known_issues(version) if known is None else known
    audit_score, _ = audit.risk_by_record(findings, known, weights)
    tiers = {r["id"]: RS.review_tier(r, rcfg) for r in records}
    risk = {}
    for r in records:
        s = audit_score.get(r["id"], 0)
        s += weights["expert_tier"] if tiers[r["id"]] == "expert_review_required" else 0
        s += weights["hard_difficulty"] if r.get("difficulty") == "hard" else 0
        s += weights["mixed_input_language"] if r.get("input_language") == "mixed" else 0
        risk[r["id"]] = s
    cov = {r["id"]: coverage_tags(r) | ({"expert_tier"} if tiers[r["id"]] == "expert_review_required" else set())
           for r in records}
    edges = {r["id"]: edge_features(r) for r in records}
    modes = {r["id"]: {m for c in r.get("contrastive") or [] for m in c["failure_modes"]} for r in records}
    counts = _counts(size, scfg["strata"])
    cap = scfg["max_per_task_type_in_targeted_strata"]
    required = list(scfg["coverage_categories"])

    chosen = []  # [(id, stratum, reason)]

    def covered():
        return set().union(*(cov[i] for i, _, _ in chosen)) if chosen else set()

    def remaining():
        taken = {i for i, _, _ in chosen}
        return [r["id"] for r in records if r["id"] not in taken]

    # 1. random — uniform over the whole pool
    order = sorted(remaining(), key=lambda i: _rank(seed, "random:" + i))
    for k, i in enumerate(order[:counts.get("random", 0)], 1):
        chosen.append((i, "random", f"seeded uniform draw #{k} of {len(records)}"))

    def pick_greedy(stratum, n, eligible, gain, reason):
        per_tt = Counter()
        for _ in range(n):
            cands = [i for i in remaining() if eligible(i) and per_tt[by_id[i]["task_type"]] < cap]
            if not cands:
                break
            cur = covered()
            best = max(cands, key=lambda i: (gain(i), len(cov[i] & set(required) - cur), _rank(seed, f"{stratum}:{i}")))
            chosen.append((best, stratum, reason(best)))
            per_tt[by_id[best]["task_type"]] += 1

    # 2. highest risk
    pick_greedy("highest_risk", counts.get("highest_risk", 0), lambda i: risk[i] > 0, lambda i: risk[i],
                lambda i: f"risk score {risk[i]} (signals hidden until after rating: gj review show {i} --show-automated)")

    # 3. contrastive — cover distinct failure modes
    def modes_covered():
        return set().union(*(modes[i] for i, _, _ in chosen)) if chosen else set()
    pick_greedy("contrastive", counts.get("contrastive", 0), lambda i: bool(modes[i]),
                lambda i: len(modes[i] - modes_covered()),
                lambda i: f"covers failure modes {sorted(modes[i])}")

    # 4. edge — cover distinct rare features
    def edges_covered():
        return set().union(*(edges[i] for i, _, _ in chosen)) if chosen else set()
    pick_greedy("edge", counts.get("edge", 0), lambda i: bool(edges[i]), lambda i: len(edges[i] - edges_covered()),
                lambda i: f"edge features {sorted(edges[i])}")

    # 5. coverage repair (targeted strata only): every category reaches its minimum count
    mins = {c: (scfg.get("coverage_minimums") or {}).get(c, 1) for c in required}

    def count(cat):
        return sum(1 for i, _, _ in chosen if cat in cov[i])

    repairs = []
    for cat in required:
        while count(cat) < mins[cat]:
            cands = [i for i in remaining() if cat in cov[i]]
            if not cands:
                break
            deficit = {c for c in required if count(c) < mins[c]}
            add = max(cands, key=lambda i: (len(cov[i] & deficit), _rank(seed, f"repair:{cat}:{i}")))
            done = False
            for idx in range(len(chosen) - 1, -1, -1):
                cid, stratum, _ = chosen[idx]
                if stratum == "random" or cat in cov[cid]:
                    continue
                if all(count(c) - 1 + (c in cov[add]) >= mins[c] for c in cov[cid] & set(required)):
                    chosen[idx] = (add, stratum, f"coverage repair: adds '{cat}' (replaced {cid})")
                    repairs.append({"category": cat, "added": add, "removed": cid, "stratum": stratum})
                    done = True
                    break
            if not done:
                break
    uncovered = sorted(c for c in required if count(c) < mins[c])

    # stable order: strata order, then selection order
    order_idx = {s["name"]: k for k, s in enumerate(scfg["strata"])}
    chosen_sorted = sorted(enumerate(chosen), key=lambda t: (order_idx[t[1][1]], t[0]))
    items = []
    for n, (_, (i, stratum, reason)) in enumerate(chosen_sorted, 1):
        r = by_id[i]
        items.append({
            "review_item_id": f"rv-{version}-{n:02d}", "example_id": i, "content_hash": content_hash(r),
            "source_file": sources.get(i, ""), "task_type": r["task_type"], "behavior": r.get("behavior") or [],
            "language": r["language"], "input_language": r["input_language"], "safety_category": r["safety_category"],
            "tier": tiers[i], "required_languages": RS.required_languages(r),
            "required_expert_domains": RS.required_expert_domains(r, rcfg), "stratum": stratum,
            "selection_reason": reason, "risk_score": risk[i], "coverage": sorted(cov[i] & set(required)),
            "calibration": False,
        })

    # 6. calibration subset — diversity across languages, tiers, contrastive, task types
    targets = {"ru": 3, "en": 3, "mixed": 1, "expert": 2, "contrastive": 2}

    def feats(it):
        f = {it["language"]}
        if it["input_language"] == "mixed":
            f.add("mixed")
        if it["tier"] == "expert_review_required":
            f.add("expert")
        if "contrastive" in it["coverage"]:
            f.add("contrastive")
        return f

    calib, have, tts = [], Counter(), set()
    for _ in range(min(scfg["calibration_size"], len(items))):
        rest = [it for it in items if it["review_item_id"] not in calib]
        best = max(rest, key=lambda it: (sum(1 for f in feats(it) if have[f] < targets.get(f, 0)),
                                         it["task_type"] not in tts, _rank(seed, "calibration:" + it["example_id"])))
        calib.append(best["review_item_id"])
        have.update(feats(best))
        tts.add(best["task_type"])
        best["calibration"] = True
    calib.sort()

    coverage = {cat: [it["review_item_id"] for it in items if cat in it["coverage"]] for cat in required}
    fingerprint = sha256_text("\n".join(f"{r['id']}:{content_hash(r)}" for r in records))
    manifest = {
        "manifest_version": "1.0",
        "sample_id": f"rs-v{version}-a",
        "dataset_version": version,
        "generated_by": "gj review sample --write",
        "seed": seed,
        "pool": {"size": len(records), "fingerprint": fingerprint},
        "sample_size": len(items),
        "strata": [{"name": s["name"], "share": s["share"], "count": sum(1 for it in items if it["stratum"] == s["name"]),
                    "rationale": STRATUM_RATIONALE[s["name"]]} for s in scfg["strata"]],
        "selection_order": [s["name"] for s in scfg["strata"]] + ["coverage_repair", "calibration"],
        "coverage": coverage,
        "uncovered": uncovered,
        "coverage_repairs": repairs,
        "calibration": {"size": len(calib), "items": calib,
                        "rationale": "Every reviewer reviews these first, independently; agreement on them (Cohen's kappa) "
                                     "is a release gate. Chosen for diversity: >=3 RU, >=3 EN, mixed input, >=2 expert-tier, "
                                     ">=2 with rejected outputs, distinct operations."},
        "inputs": {
            "audit_findings_sha256": sha256_text(canonical_json(sorted(
                [f["finding_id"], f["severity"]] for f in findings if f["scope"] in ("expected_output", "contrastive", "input")))),
            "known_issues_sha256": sha256_text(canonical_json(sorted([k["id"], k["severity"], k["status"]] for k in known))),
            "risk_weights": weights, "sampling_config": scfg,
        },
        "items": items,
    }
    return manifest


def manifest_path(version=None):
    return repo_path(RS.review_config()["paths"]["manifest"].format(version=version or versions()["dataset_version"]))


def run(write=False, check=False, as_json=False):
    manifest = build_manifest()
    errs = schemas.validate("review_manifest", manifest)
    if errs:
        print("✗ manifest does not match schemas/review_manifest.json:", errs[:5])
        return 1
    path = manifest_path(manifest["dataset_version"])
    if as_json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        _print(manifest)
    if check:
        if not path.exists():
            print(f"✗ {rel(path)} does not exist")
            return 1
        same = load_json(path) == manifest
        print(f"{'✓' if same else '✗'} {rel(path)} {'matches' if same else 'differs from'} a fresh regeneration")
        return 0 if same else 1
    if write:
        if path.exists():
            if load_json(path) == manifest:
                print(f"{rel(path)} unchanged.")
                return 0
            print(f"✗ {rel(path)} already exists with different content. The review sample is frozen once reviews "
                  f"reference its item ids; keep it, or create a new sample deliberately (new dataset version).")
            return 1
        dump_json(manifest, path)
        print(f"Wrote {rel(path)}")
    return 0


def _print(m):
    print(f"Review sample {m['sample_id']}: {m['sample_size']} of {m['pool']['size']} examples (seed {m['seed']})")
    for s in m["strata"]:
        print(f"  {s['name']:13} {s['count']:2} ({s['share']:.0%})")
    print("\n  item            example            stratum       tier    lang  task_type")
    for it in m["items"]:
        mark = "*" if it["calibration"] else " "
        print(f"  {it['review_item_id']}{mark} {it['example_id']:18} {it['stratum']:13} "
              f"{'expert' if it['tier'].startswith('expert') else 'human':7} {it['language']}{'+mx' if it['input_language'] == 'mixed' else '   '} "
              f"{it['task_type']}")
    thin = {k: len(v) for k, v in m["coverage"].items() if len(v) < 2}
    print(f"\nCoverage: all {len(m['coverage']) - len(m['uncovered'])}/{len(m['coverage'])} categories covered"
          + (f"; uncovered {m['uncovered']}" if m["uncovered"] else "") + (f"; covered once: {sorted(thin)}" if thin else ""))
    for rp in m["coverage_repairs"]:
        print(f"  repair: +{rp['added']} for '{rp['category']}' (replaced {rp['removed']} in {rp['stratum']})")
    print(f"Calibration (* above): {', '.join(m['calibration']['items'])}")
