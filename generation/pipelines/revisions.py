"""`gj revisions sync|check|diff`: the revision ledger of a dataset version (data/revisions/v<ver>.yaml).

A dataset version is built on an immutable base release (for v0.1.1: the v0.1.0 release files and
manifest). The ledger records every difference between the current pool and that base:

* one entry per revised example (defect, correction, rationale, known issues, policies, human
  reviewer status) — authored by hand;
* computed fields, filled by `sync`: the base and current content hashes, the changed JSON paths and
  content-addressed snapshots of both versions under data/revisions/snapshots/<hash>.json;
* metadata changes (fields outside the hashed content), with the number of examples affected;
* added and removed example ids.

`check` fails when anything differs from the base without a ledger entry (no silent edits), when a
computed field is stale (content edited after `sync`), when a snapshot is missing or does not match
its hash, or when the base release no longer matches the sha256 recorded in its manifest.

The ledger author is not a reviewer: `reviewer_status` stays `pending_human_review` until a registered
human reviewer's decision is recorded with `gj revisions review` (schema 0.1.2). That writes
`reviewer_status` (`confirmed` or `disputed`) and a `review` block — reviewer, timestamp, the content
hash the decision was made on, `independent_rating` and notes. `check` fails when the reviewed hash no
longer matches the entry, or the reviewer is not a registered human.
"""
from collections import Counter

import yaml

from gjcore import schemas
from gjcore.config import versions
from gjcore.io import canonical_json, dump_json, load_json, load_yaml, read_jsonl, sha256_text
from gjcore.paths import DATA_DIR, rel, repo_path
from gjcore.records import HASHED_FIELDS, content_hash

from .pool import load_pool

REVISIONS_DIR = DATA_DIR / "revisions"
SNAPSHOTS_DIR = REVISIONS_DIR / "snapshots"
_RELEASE_ONLY = {"review_status", "content_hash", "revision"}
_COMPUTED = ("previous_content_hash", "content_hash", "changed_paths", "snapshots")
_HEADER = """# Revision ledger — dataset v{version} (base: v{base}).
#
# Every example whose trainable content (task_type, input, expected_output, contrastive) differs from
# the base release has one entry here; metadata changes are counted below. Authored fields: id,
# example_id, kind, known_issues, policies, defect, correction, rationale, reviewer_status.
# Computed fields (previous_content_hash, content_hash, changed_paths, snapshots) are written by
# `gj revisions sync`; `gj revisions check` fails on any unrecorded or stale change.
# reviewer_status is a human decision: it stays pending_human_review until a registered reviewer's
# decision is recorded with `gj revisions review`, which also writes the entry's `review` block.
"""


class RevisionError(ValueError):
    pass


REVIEW_STATUSES = ("confirmed", "disputed")


def ledger_path(version=None):
    return REVISIONS_DIR / f"v{version or versions()['dataset_version']}.yaml"


def load_ledger(version=None):
    path = ledger_path(version)
    if not path.exists():
        return None
    return load_yaml(path)


def base_release(ledger):
    """{id: record} of the base release, and the list of integrity problems of its files."""
    manifest = load_json(repo_path(ledger["base_release_manifest"]))
    records, problems = {}, []
    for split in ("train", "validation"):
        info = manifest["files"][split]
        path = repo_path(info["path"])
        text = path.read_text(encoding="utf-8")
        if sha256_text(text) != info["sha256"]:
            problems.append(f"base release file {info['path']} no longer matches the sha256 in its manifest")
        for r in read_jsonl(path):
            records[r["id"]] = {k: v for k, v in r.items() if k not in _RELEASE_ONLY}
    return records, problems


def changed_paths(a, b, path="", limit=40):
    """JSON paths where a and b differ (lists compared by index)."""
    out = []

    def walk(x, y, p):
        if len(out) >= limit:
            return
        if isinstance(x, dict) and isinstance(y, dict):
            for k in sorted(set(x) | set(y)):
                walk(x.get(k), y.get(k), f"{p}/{k}" if p else k)
        elif isinstance(x, list) and isinstance(y, list):
            for i in range(max(len(x), len(y))):
                walk(x[i] if i < len(x) else None, y[i] if i < len(y) else None, f"{p}/{i}")
        elif x != y:
            out.append(p or "<root>")

    walk(a, b, path)
    return out


def snapshot_path(h):
    return SNAPSHOTS_DIR / f"{h}.json"


def _snapshot_body(record, version):
    return {"content_hash": content_hash(record), "example_id": record["id"], "dataset_version": version,
            **{k: record.get(k) for k in HASHED_FIELDS}}


def write_snapshot(record, version):
    body = _snapshot_body(record, version)
    path = snapshot_path(body["content_hash"])
    if path.exists():
        old = load_json(path)
        if {k: old.get(k) for k in HASHED_FIELDS} != {k: body.get(k) for k in HASHED_FIELDS}:
            raise RevisionError(f"snapshot {rel(path)} exists with different content — refusing to overwrite history")
        return path
    dump_json(body, path)
    return path


def metadata_diff(base, current):
    """{field: number of examples whose non-hashed field differs from the base}."""
    counts = Counter()
    for rid, rec in current.items():
        old = base.get(rid)
        if old is None:
            continue
        for k in (set(rec) | set(old)) - set(HASHED_FIELDS) - _RELEASE_ONLY - {"id"}:
            if rec.get(k) != old.get(k):
                counts[k] += 1
    return dict(sorted(counts.items()))


def _current():
    return {r["id"]: r for r, _, _ in load_pool()}


def sync(version=None):
    ledger = load_ledger(version)
    if ledger is None:
        raise RevisionError(f"no ledger at {rel(ledger_path(version))}")
    base, problems = base_release(ledger)
    if problems:
        raise RevisionError("; ".join(problems))
    cur = _current()
    for entry in ledger["revisions"]:
        rid = entry["example_id"]
        if rid not in cur or rid not in base:
            raise RevisionError(f"{entry['id']}: {rid} is not in both the base release and the current pool")
        old, new = base[rid], cur[rid]
        entry["previous_content_hash"] = content_hash(old)
        entry["content_hash"] = content_hash(new)
        entry["changed_paths"] = changed_paths({k: old.get(k) for k in HASHED_FIELDS}, {k: new.get(k) for k in HASHED_FIELDS})
        entry["snapshots"] = {"previous": rel(write_snapshot(old, ledger["base_version"])),
                              "current": rel(write_snapshot(new, ledger["dataset_version"]))}
    _write(ledger)
    return ledger


def _write(ledger):
    path = ledger_path(ledger["dataset_version"])
    body = yaml.safe_dump(ledger, allow_unicode=True, sort_keys=False, width=140)
    path.write_text(_HEADER.format(version=ledger["dataset_version"], base=ledger["base_version"]) + body, encoding="utf-8")


def check(version=None):
    """Return (errors, summary)."""
    ledger = load_ledger(version)
    if ledger is None:
        return [f"no ledger at {rel(ledger_path(version))}"], {}
    errors = [f"ledger schema: {e}" for e in schemas.validate("revision_ledger", ledger)]
    base, problems = base_release(ledger)
    errors += problems
    cur = _current()
    by_example = {}
    ids = Counter(e["id"] for e in ledger["revisions"])
    errors += [f"duplicate revision id {i}" for i, n in ids.items() if n > 1]
    for e in ledger["revisions"]:
        by_example.setdefault(e["example_id"], []).append(e)
    changed = sorted(rid for rid in cur if rid in base and content_hash(cur[rid]) != content_hash(base[rid]))
    for rid in changed:
        entries = by_example.get(rid)
        if not entries:
            errors.append(f"{rid}: content differs from v{ledger['base_version']} but has no ledger entry (silent edit)")
            continue
        for e in entries:
            if e.get("content_hash") != content_hash(cur[rid]):
                errors.append(f"{e['id']} ({rid}): content changed after the ledger was synced — run `gj revisions sync` and "
                              "review the entry")
            if e.get("previous_content_hash") != content_hash(base[rid]):
                errors.append(f"{e['id']} ({rid}): previous_content_hash does not match the base release")
            for key in ("previous", "current"):
                sp = (e.get("snapshots") or {}).get(key)
                h = e.get("previous_content_hash" if key == "previous" else "content_hash")
                if not sp or not repo_path(sp).exists():
                    errors.append(f"{e['id']}: {key} snapshot missing")
                    continue
                snap = load_json(repo_path(sp))
                if sha256_text(canonical_json({k: snap.get(k) for k in HASHED_FIELDS})) != h:
                    errors.append(f"{e['id']}: {key} snapshot does not match its hash")
    for rid, entries in by_example.items():
        if rid not in changed:
            errors.append(f"{', '.join(e['id'] for e in entries)}: {rid} is recorded as revised but equals the base release")
    added = sorted(set(cur) - set(base))
    removed = sorted(set(base) - set(cur))
    if added != sorted(ledger["examples_added"]):
        errors.append(f"examples_added {ledger['examples_added']} != actual {added}")
    if removed != sorted(ledger["examples_removed"]):
        errors.append(f"examples_removed {ledger['examples_removed']} != actual {removed}")
    meta = metadata_diff(base, cur)
    listed = {m["field"]: m["examples"] for m in ledger["metadata_changes"]}
    for field, n in meta.items():
        if listed.get(field) != n:
            errors.append(f"metadata field {field!r} changed on {n} example(s) but the ledger lists {listed.get(field)}")
    for field in set(listed) - set(meta):
        errors.append(f"metadata change {field!r} is listed but no example differs in it")
    ki_known = _known_issue_ids(ledger)
    for e in ledger["revisions"]:
        for ki in e["known_issues"]:
            if ki not in ki_known:
                errors.append(f"{e['id']}: unknown known issue {ki}")
    errors += _review_errors(ledger)
    summary = {"base_version": ledger["base_version"], "dataset_version": ledger["dataset_version"],
               "revised_examples": len(changed), "ledger_entries": len(ledger["revisions"]),
               "by_kind": dict(Counter(e["kind"] for e in ledger["revisions"])),
               "reviewer_status": dict(Counter(e["reviewer_status"] for e in ledger["revisions"])),
               "metadata_changes": meta, "added": added, "removed": removed}
    return errors, summary


def _review_errors(ledger):
    """Recorded ledger reviews must be bound to the entry's current content hash and name a registered human."""
    reviewed = [e for e in ledger["revisions"] if isinstance(e.get("review"), dict)]
    if not reviewed:
        return []
    from .review_store import load_registry
    registry, errors = load_registry(), []
    for e in reviewed:
        rv = e["review"]
        if rv.get("content_hash") != e.get("content_hash"):
            errors.append(f"{e['id']}: the review by {rv.get('reviewer_id')} was made on content {str(rv.get('content_hash'))[:12]}, "
                          f"but the entry is now at {str(e.get('content_hash'))[:12]} — record a new review")
        who = registry.get(rv.get("reviewer_id"))
        if who is None or not who["human"]:
            errors.append(f"{e['id']}: reviewer {rv.get('reviewer_id')!r} is not a registered human reviewer")
    return errors


def record_review(rev_id, reviewer_id, status, notes, independent_rating, version=None, replace=False, timestamp=None):
    """Record a registered human reviewer's decision on one ledger entry: set reviewer_status and the review block.

    The decision is bound to the entry's content_hash, which must match the current content (the ledger has to
    pass `check` first). An entry that already has a review is refused unless `replace` is set; git keeps the
    earlier block. Returns the updated entry."""
    from .review_store import load_registry, now_utc, required_languages, review_config
    if status not in REVIEW_STATUSES:
        raise RevisionError(f"status must be one of {list(REVIEW_STATUSES)}, got {status!r}")
    if not isinstance(independent_rating, bool):
        raise RevisionError("independent_rating must be given (yes or no)")
    if not (notes or "").strip():
        raise RevisionError("notes are required: state the decision and the reason")
    ledger = load_ledger(version)
    if ledger is None:
        raise RevisionError(f"no ledger at {rel(ledger_path(version))}")
    errors, _ = check(ledger["dataset_version"])
    if errors:
        raise RevisionError(f"the ledger does not pass `gj revisions check` ({len(errors)} problem(s)); first: {errors[0]}")
    entry = next((e for e in ledger["revisions"] if e["id"] == rev_id), None)
    if entry is None:
        raise RevisionError(f"no ledger entry {rev_id} in {rel(ledger_path(ledger['dataset_version']))}")
    if entry.get("review") and not replace:
        raise RevisionError(f"{rev_id} already has a review by {entry['review']['reviewer_id']} "
                            f"({entry['reviewer_status']}); pass --replace to record a new decision")
    reviewer = load_registry().get(reviewer_id)
    if reviewer is None:
        raise RevisionError(f"unknown reviewer {reviewer_id!r} — add yourself to review/reviewers.yaml first")
    if not reviewer["human"]:
        raise RevisionError(f"reviewer {reviewer_id!r} is not marked human: true — automated agents cannot record decisions")
    if not reviewer["active"]:
        raise RevisionError(f"reviewer {reviewer_id!r} is inactive")
    record = _current()[entry["example_id"]]
    langs = required_languages(record)
    if review_config()["approval"]["require_language_match"] and not set(langs) <= set(reviewer["languages"]):
        raise RevisionError(f"{entry['example_id']} needs a reviewer who reads {langs}; {reviewer_id} lists {reviewer['languages']}")
    review = {"reviewer_id": reviewer_id, "timestamp": timestamp or now_utc(), "content_hash": entry["content_hash"],
              "independent_rating": independent_rating, "notes": notes.strip()}
    updated = {}
    for k, v in entry.items():
        if k == "review":
            continue
        updated[k] = status if k == "reviewer_status" else v
        if k == "reviewer_status":
            updated["review"] = review
    entry.clear()
    entry.update(updated)
    problems = schemas.validate("revision_ledger", ledger)
    if problems:
        raise RevisionError("ledger schema: " + "; ".join(problems))
    _write(ledger)
    return entry


def _known_issue_ids(ledger):
    from .audit import load_known_issues
    ids = set()
    for v in (ledger["base_version"], ledger["dataset_version"]):
        ids |= {k["id"] for k in load_known_issues(v)}
    return ids


def revision_info(version=None):
    """{example_id: {dataset_version, previous_content_hash, revision_ids}} for release rows."""
    ledger = load_ledger(version)
    if not ledger:
        return {}
    out = {}
    for e in ledger["revisions"]:
        info = out.setdefault(e["example_id"], {"dataset_version": ledger["dataset_version"],
                                                "previous_content_hash": e.get("previous_content_hash"),
                                                "revision_ids": []})
        info["revision_ids"].append(e["id"])
    return out


def _short(v, n=160):
    s = v if isinstance(v, str) else canonical_json(v)
    return s if len(s) <= n else s[:n] + "…"


def _at(obj, path):
    for part in [p for p in path.split("/") if p]:
        if isinstance(obj, list):
            i = int(part)
            obj = obj[i] if i < len(obj) else None
        elif isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


def run(action, version=None, example=None, **kw):
    if action == "sync":
        ledger = sync(version)
        print(f"Synced {len(ledger['revisions'])} ledger entries -> {rel(ledger_path(ledger['dataset_version']))}")
        return 0
    if action == "check":
        errors, s = check(version)
        if s:
            print(f"Revisions v{s['dataset_version']} (base v{s['base_version']}): {s['revised_examples']} revised examples, "
                  f"{s['ledger_entries']} ledger entries {s['by_kind']}; reviewer status {s['reviewer_status']}; "
                  f"metadata {s['metadata_changes']}; added {len(s['added'])}, removed {len(s['removed'])}.")
        for e in errors:
            print(f"✗ {e}")
        if not errors:
            print("✓ every difference from the base release is recorded; snapshots and base release intact.")
        return 1 if errors else 0
    if action == "diff":
        ledger = load_ledger(version)
        entries = [e for e in ledger["revisions"] if e["example_id"] == example]
        if not entries:
            print(f"no ledger entry for {example}")
            return 1
        for e in entries:
            print(f"{e['id']} {e['example_id']} [{e['kind']}; {', '.join(e['known_issues'] + e['policies'])}] "
                  f"reviewer_status={e['reviewer_status']}")
            print(f"  defect:     {e['defect']}\n  correction: {e['correction']}\n  rationale:  {e['rationale']}")
            if e.get("review"):
                rv = e["review"]
                print(f"  review:     {rv['reviewer_id']} {rv['timestamp']} on {rv['content_hash'][:12]}, "
                      f"independent_rating={str(rv['independent_rating']).lower()}: {rv['notes']}")
            old = load_json(repo_path(e["snapshots"]["previous"]))
            new = load_json(repo_path(e["snapshots"]["current"]))
            for p in e["changed_paths"]:
                print(f"  ~ {p}\n      - {_short(_at(old, p))}\n      + {_short(_at(new, p))}")
        return 0
    if action == "review":
        e = record_review(kw["revision"], kw["reviewer"], kw["status"], kw["notes"], kw["independent_rating"],
                          version=version, replace=kw.get("replace", False))
        print(f"Recorded {e['id']} ({e['example_id']}): reviewer_status={e['reviewer_status']} by {e['review']['reviewer_id']} "
              f"on content {e['content_hash'][:12]}, independent_rating={str(e['review']['independent_rating']).lower()}")
        return 0
    raise ValueError(action)

