"""`gj review sample-status`: the review sample in force, carried to the current dataset version.

The 30-item sample (review/review_manifest_v<sample_version>.json) is kept as drawn: its item ids, strata and
the 8 calibration items do not change. For every item this report records, against the current pool:
  * whether the content changed since it was sampled (content hash), and the revision ids that explain it
    (data/revisions/v<version>.yaml);
  * the known issues that name the example (review/known_issues_v<version>.yaml) with their status;
  * the human review status and detail from the append-only decision log (review_store.resolve).

Nothing here sets a review status: `human_review_status` is read from human decisions only, and a
decision recorded for older content never carries over to changed content (detail `content_changed`).
"""
import json
from collections import Counter

from gjcore import schemas
from gjcore.config import versions
from gjcore.io import dump_json, load_json
from gjcore.paths import rel, repo_path
from gjcore.records import content_hash

from . import audit
from . import review_store as RS
from .pool import load_pool, load_review_events
from .review import load_manifest, sample_version
from .revisions import revision_info


def status_path(version=None):
    return repo_path(RS.review_config()["paths"]["sample_status"].format(version=version or versions()["dataset_version"]))


def build(version=None):
    version = version or versions()["dataset_version"]
    sv = sample_version(version)
    manifest = load_manifest(version)
    if not manifest:
        raise FileNotFoundError(f"no review sample for v{version} (sample version {sv})")
    pool = {r["id"]: r for r, _, _ in load_pool()}
    events = load_review_events()
    rinfo = revision_info(version)
    known = audit.load_known_issues(version)
    calib = set(manifest["calibration"]["items"])
    items = []
    for it in manifest["items"]:
        eid = it["example_id"]
        rec = pool.get(eid)
        cur = content_hash(rec) if rec else ""
        info = RS.resolve(rec, events) if rec else {"status": "pending", "detail": "not_reviewed"}
        kis = [{"id": k["id"], "status": k.get("status", "open"), "severity": k["severity"], "problem": k["problem"]}
               for k in known if eid in k.get("records", [])]
        changed = bool(rec) and cur != it["content_hash"]
        note = []
        if changed:
            note.append("content revised since sampling — rate the current content; an earlier decision would not carry over")
        if it["review_item_id"] in calib:
            note.append("calibration item: every reviewer rates it independently, before other items")
        items.append({
            "review_item_id": it["review_item_id"], "example_id": eid, "calibration": it["review_item_id"] in calib,
            "stratum": it["stratum"], "sampled_content_hash": it["content_hash"], "current_content_hash": cur,
            "changed_since_sampling": changed, "revision_ids": (rinfo.get(eid) or {}).get("revision_ids", []),
            "known_issues": kis, "human_review_status": info["status"], "human_review_detail": info["detail"],
            **({"note": "; ".join(note)} if note else {}),
        })
    ki_status = Counter(k["status"] for i in items for k in i["known_issues"])
    summary = {
        "items": len(items),
        "changed_since_sampling": sum(i["changed_since_sampling"] for i in items),
        "unchanged": sum(not i["changed_since_sampling"] for i in items),
        "calibration_items": len(calib),
        "calibration_items_changed": sum(i["changed_since_sampling"] for i in items if i["calibration"]),
        "items_with_known_issues": sum(1 for i in items if i["known_issues"]),
        "known_issue_links_by_status": dict(sorted(ki_status.items())),
        "human_review_status": dict(sorted(Counter(i["human_review_status"] for i in items).items())),
        "human_review_detail": dict(sorted(Counter(i["human_review_detail"] for i in items).items())),
        "approved_by_automation": 0,
    }
    return {
        "status_version": "1.0", "dataset_version": version,
        "sample_manifest": rel(repo_path(RS.review_config()["paths"]["manifest"].format(version=sv))),
        "sample_id": manifest["sample_id"], "calibration_items": sorted(calib), "summary": summary, "items": items,
    }


def run(version=None, write=False, check=False, as_json=False):
    doc = build(version)
    errs = schemas.validate("review_sample_status", doc)
    if errs:
        print("✗ sample status does not match schemas/review_sample_status.json:", errs[:5])
        return 1
    path = status_path(doc["dataset_version"])
    if as_json:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    else:
        s = doc["summary"]
        print(f"Review sample {doc['sample_id']} ({doc['sample_manifest']}) at v{doc['dataset_version']}: {s['items']} items, "
              f"{s['changed_since_sampling']} changed since sampling ({s['calibration_items_changed']} of {s['calibration_items']} "
              f"calibration items); human review {s['human_review_status']} {s['human_review_detail']}.")
        for i in doc["items"]:
            mark = "*" if i["calibration"] else " "
            kis = ", ".join(f"{k['id']}:{k['status']}" for k in i["known_issues"]) or "-"
            print(f" {mark}{i['review_item_id']} {i['example_id']:16} {'changed' if i['changed_since_sampling'] else 'same   '} "
                  f"{','.join(i['revision_ids']) or '-':28} KI {kis:40} {i['human_review_status']}/{i['human_review_detail']}")
    if check:
        same = path.exists() and load_json(path) == doc
        print(f"{'✓' if same else '✗'} {rel(path)} {'is current' if same else 'differs — run `gj review sample-status --write`'}")
        return 0 if same else 1
    if write:
        dump_json(doc, path)
        print(f"Wrote {rel(path)}")
    return 0
