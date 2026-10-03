"""`gj export`: turn a release into training/evaluation formats.

sft         {"messages": [system, user, assistant], "metadata": {...}}   (train + validation)
preference  {"prompt": [system, user], "chosen": [assistant], "rejected": [assistant], "metadata": {...}}
eval        {"id", "case_id", "step_id", "case_type", "messages": [system, user], "task_type", "dimensions",
             "checks", "language"} — one row per model call (each step of a multi-step case is a row)

Training formats (sft, preference) are gated:
  * --review-policy require_approved (default): only rows whose exact content is `approved` NOW
    (review decisions are resolved live against the content hash stored in the release) — so rows needing
    revision, rejected, not reviewed or changed since their decision never reach a training file, in any review mode;
  * the release gates (configs/release_gates.yaml) must pass — otherwise the export is refused, unless
    --allow-draft is given, which writes to exports/v<ver>-draft/ with training_eligible: false on every
    record and a DRAFT_NOT_FOR_TRAINING marker (pipeline smoke tests only);
  * --review-policy allow_pending always implies a draft export.
The eval format is not gated: it contains no training targets.

The system prompt is the navigator prompt version recorded in the release manifest, so re-exporting
an older release reproduces the prompt it was built for.

The chat template of the base model is applied later by the training framework; nothing here is
specific to one model or provider.
"""
from gjcore.config import load_config, versions
from gjcore.io import load_json, read_jsonl, write_jsonl
from gjcore.paths import rel, repo_path
from gjcore.prompting import assistant_message, navigator_prompt_path, prompt_messages

from .split import release_paths

_RELEASE_ONLY = ("review_status", "content_hash")


def _release_versions(paths):
    """Versions the release was built with (manifest), falling back to the current ones."""
    if paths["manifest"].exists():
        return load_json(paths["manifest"]).get("versions") or versions()
    return versions()


def _meta(rec, version, split, status, eligible, prompt_version):
    return {"id": rec["id"], "split": split, "task_type": rec["task_type"], "behavior": rec["behavior"],
            "language": rec["language"], "domain": rec["domain"], "safety_category": rec["safety_category"],
            "review_status": status, "training_eligible": eligible, "content_hash": rec.get("content_hash"),
            "dataset_version": version, "navigator_prompt_version": prompt_version,
            "schema_version": rec.get("schema_version")}


def export(fmt, version=None, out_dir=None, review_policy="require_approved", allow_draft=False):
    version = version or versions()["dataset_version"]
    paths = release_paths(version)
    missing = [p for k, p in paths.items() if k != "manifest" and not p.exists()]
    if missing:
        print(f"✗ release v{version} not built ({rel(missing[0])} missing) — run `gj split` first.")
        return 1
    base = repo_path(out_dir or load_config("export")["exports_dir"])
    written = []
    prompt_version = _release_versions(paths)["navigator_prompt_version"]
    prompt = navigator_prompt_path(prompt_version)
    if fmt == "eval":
        from evaluation.metrics.scoring import expand_units
        out = base / f"v{version}"
        rows = []
        for c in read_jsonl(paths["test"]):
            for u in expand_units(c):
                rows.append({"id": u["unit_id"], "case_id": u["case_id"], "step_id": u["step_id"],
                             "case_type": u["case_type"], "messages": prompt_messages(u["input"], prompt),
                             "task_type": u["task_type"], "dimensions": u["dimensions"], "language": u["language"],
                             "checks": u["checks"], "eval_version": c["eval_version"],
                             "schema_version": c.get("schema_version", "0.1.0"), "navigator_prompt_version": prompt_version})
        write_jsonl(rows, out / "eval.jsonl")
        print(f"Wrote {len(rows):4d} records -> {rel(out / 'eval.jsonl')}")
        return 0
    if fmt not in ("sft", "preference"):
        print(f"✗ unknown format {fmt!r}")
        return 1

    from . import review_store as RS
    from .gates import evaluate, failing as failing_gates, training_ready
    if review_policy == "allow_pending" and not allow_draft:
        print("✗ --review-policy allow_pending exports unreviewed rows; it requires --allow-draft (output is marked not-for-training).")
        return 1
    results = evaluate(version, purpose=fmt)
    ready = training_ready(results)
    failing = failing_gates(results)
    if not ready and not allow_draft:
        print(f"✗ release v{version} is not training_ready — failing gates: {', '.join(failing)}.")
        print("  Run `gj gates` for details. For a pipeline smoke test use --allow-draft (writes exports/v<ver>-draft/, "
              "training_eligible: false).")
        return 1
    draft = allow_draft and (not ready or review_policy != "require_approved")
    out = base / (f"v{version}-draft" if draft else f"v{version}")
    events = RS.ReviewStore.default().events()
    kept, skipped = 0, 0
    for split in ("train", "validation"):
        rows = []
        for r in read_jsonl(paths[split]):
            rec = {k: v for k, v in r.items() if k not in _RELEASE_ONLY}
            status = RS.resolve(rec, events)["status"]
            if review_policy == "require_approved" and status != "approved":
                skipped += 1
                continue
            kept += 1
            eligible = (not draft) and status == "approved"
            meta = _meta({**rec, "content_hash": r.get("content_hash")}, version, split, status, eligible, prompt_version)
            if fmt == "sft":
                rows.append({"messages": prompt_messages(rec["input"], prompt) + [assistant_message(rec["expected_output"])],
                             "metadata": meta})
            else:
                for c in rec.get("contrastive") or []:
                    rows.append({"prompt": prompt_messages(rec["input"], prompt),
                                 "chosen": [assistant_message(rec["expected_output"])],
                                 "rejected": [assistant_message(c["output"])],
                                 "metadata": {**meta, "contrastive_id": c["id"], "failure_modes": c["failure_modes"]}})
        write_jsonl(rows, out / f"{fmt}_{split}.jsonl")
        written.append((out / f"{fmt}_{split}.jsonl", len(rows)))
    if draft:
        (out / "DRAFT_NOT_FOR_TRAINING").write_text(
            f"Draft export of release v{version} (review policy {review_policy}). Failing gates: {', '.join(failing) or 'none'}.\n"
            "Every record has metadata.training_eligible = false. Use only to test training/eval tooling.\n", encoding="utf-8")
    for p, n in written:
        print(f"Wrote {n:4d} records -> {rel(p)}")
    print(f"Rows kept {kept}, skipped (not approved) {skipped}; "
          + ("DRAFT — not for training." if draft else "training_ready release; records are training_eligible."))
    return 0
