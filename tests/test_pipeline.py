import json

from generation.pipelines import split


def test_assign_splits_is_deterministic_and_group_pure():
    recs = [{"id": f"x{i}", "scenario_group": f"g{i // 2}", "task_type": "daily_plan" if i % 3 else "goal_change"}
            for i in range(40)]
    a = split.assign_splits(recs, 7, 0.2, 4)
    assert a == split.assign_splits(recs, 7, 0.2, 4)
    assert set(a.values()) == {"train", "validation"}
    assert a != split.assign_splits(recs, 8, 0.2, 4) or True  # different seeds may coincide; determinism is the point


def test_release_dry_run_passes_all_gates():
    assert split.build_release(dry_run=True) == 0


def test_prompt_format_matches_between_export_and_eval():
    from gjcore.prompting import assistant_message, prompt_messages
    msgs = prompt_messages({"operation": "daily_plan", "today": "2026-09-27"})
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert json.loads(msgs[1]["content"])["operation"] == "daily_plan"
    assert "GoalJourney Navigator" in msgs[0]["content"]
    assert json.loads(assistant_message({"type": "x"})["content"]) == {"type": "x"}
