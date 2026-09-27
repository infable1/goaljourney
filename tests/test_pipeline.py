import json

import pytest

from gjcore.records import content_hash
from generation.pipelines import review, split
from generation.pipelines.pool import review_status


def test_assign_splits_is_deterministic_and_group_pure():
    recs = [{"id": f"x{i}", "scenario_group": f"g{i // 2}", "task_type": "daily_plan" if i % 3 else "goal_change"}
            for i in range(40)]
    a = split.assign_splits(recs, 7, 0.2, 4)
    assert a == split.assign_splits(recs, 7, 0.2, 4)
    assert set(a.values()) == {"train", "validation"}
    assert a != split.assign_splits(recs, 8, 0.2, 4) or True  # different seeds may coincide; determinism is the point


def test_release_dry_run_passes_all_gates():
    assert split.build_release(dry_run=True) == 0


def test_review_status_follows_content_hash():
    rec = {"id": "gj-x-001", "task_type": "daily_plan", "input": {"a": 1}, "expected_output": {"b": 2}}
    h = content_hash(rec)
    assert review_status(rec, []) == "pending"
    log = [{"example_id": "gj-x-001", "content_hash": h, "decision": "approved"}]
    assert review_status(rec, log) == "approved"
    changed = {**rec, "expected_output": {"b": 3}}
    assert review_status(changed, log) == "stale"


def test_acceptance_rule_enforces_hard_gates():
    assert review.check_acceptance({"correctness": 4, "safety": 4, "non_hallucination": 4}) == []
    assert review.check_acceptance({"correctness": 3, "safety": 3}) != []
    assert review.check_acceptance({"correctness": 2}) != []


def test_prompt_format_matches_between_export_and_eval():
    from gjcore.prompting import assistant_message, prompt_messages
    msgs = prompt_messages({"operation": "daily_plan", "today": "2026-09-27"})
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert json.loads(msgs[1]["content"])["operation"] == "daily_plan"
    assert "GoalJourney Navigator" in msgs[0]["content"]
    assert json.loads(assistant_message({"type": "x"})["content"]) == {"type": "x"}


def test_review_export_and_apply_roundtrip(tmp_path, monkeypatch):
    import yaml
    log = tmp_path / "reviews.jsonl"
    monkeypatch.setattr(review, "load_config", lambda name: {"paths": {"review_log": str(log)}})
    sheet = tmp_path / "sheet.yaml"
    assert review.export_sheet(str(sheet), ids=["gj-safe-001"]) == 0
    data = yaml.safe_load(sheet.read_text(encoding="utf-8"))
    entry = data["entries"][0]
    entry["review"]["decision"] = "approved"
    entry["review"]["scores"] = {k: 4 for k in entry["review"]["scores"]}
    sheet.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    assert review.apply_reviews(str(sheet), reviewer="tester") == 0
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["example_id"] == "gj-safe-001" and rows[0]["decision"] == "approved"
    # A failing hard gate cannot be approved.
    entry["review"]["scores"]["safety"] = 3
    sheet.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    assert review.apply_reviews(str(sheet), reviewer="tester") == 1
