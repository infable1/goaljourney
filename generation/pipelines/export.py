"""`gj export`: turn a release into training/evaluation formats.

sft         {"messages": [system, user, assistant], "metadata": {...}}   (train + validation)
preference  {"prompt": [system, user], "chosen": [assistant], "rejected": [assistant], "metadata": {...}}
eval        {"id", "messages": [system, user], "task_type", "dimensions", "checks", "language"}

The chat template of the base model is applied later by the training framework; nothing here is
specific to one model or provider.
"""
from gjcore.config import load_config, versions
from gjcore.io import read_jsonl, write_jsonl
from gjcore.paths import rel, repo_path
from gjcore.prompting import assistant_message, prompt_messages

from .split import release_paths


def _meta(rec, version, split):
    v = versions()
    return {"id": rec["id"], "split": split, "task_type": rec["task_type"], "behavior": rec["behavior"],
            "language": rec["language"], "domain": rec["domain"], "safety_category": rec["safety_category"],
            "review_status": rec.get("review_status"), "dataset_version": version,
            "navigator_prompt_version": v["navigator_prompt_version"], "schema_version": v["schema_version"]}


def export(fmt, version=None, out_dir=None):
    version = version or versions()["dataset_version"]
    paths = release_paths(version)
    missing = [p for k, p in paths.items() if k != "manifest" and not p.exists()]
    if missing:
        print(f"✗ release v{version} not built ({rel(missing[0])} missing) — run `gj split` first.")
        return 1
    out = repo_path(out_dir or load_config("export")["exports_dir"]) / f"v{version}"
    written = []
    if fmt == "sft":
        for split in ("train", "validation"):
            rows = [{"messages": prompt_messages(r["input"]) + [assistant_message(r["expected_output"])],
                     "metadata": _meta(r, version, split)} for r in read_jsonl(paths[split])]
            write_jsonl(rows, out / f"sft_{split}.jsonl")
            written.append((out / f"sft_{split}.jsonl", len(rows)))
    elif fmt == "preference":
        for split in ("train", "validation"):
            rows = []
            for r in read_jsonl(paths[split]):
                for c in r.get("contrastive") or []:
                    rows.append({"prompt": prompt_messages(r["input"]),
                                 "chosen": [assistant_message(r["expected_output"])],
                                 "rejected": [assistant_message(c["output"])],
                                 "metadata": {**_meta(r, version, split), "contrastive_id": c["id"],
                                              "failure_modes": c["failure_modes"]}})
            write_jsonl(rows, out / f"preference_{split}.jsonl")
            written.append((out / f"preference_{split}.jsonl", len(rows)))
    elif fmt == "eval":
        rows = [{"id": c["id"], "messages": prompt_messages(c["input"]), "task_type": c["task_type"],
                 "dimensions": c["dimensions"], "language": c["language"], "checks": c["checks"],
                 "eval_version": c["eval_version"]} for c in read_jsonl(paths["test"])]
        write_jsonl(rows, out / "eval.jsonl")
        written.append((out / "eval.jsonl", len(rows)))
    else:
        print(f"✗ unknown format {fmt!r}")
        return 1
    for p, n in written:
        print(f"Wrote {n:4d} records -> {rel(p)}")
    return 0
