import json

import pytest

from gjcore.env import MissingCredentialsError
from gjcore.paths import repo_path
from gjcore.records import load_examples, load_records
from generation.generators import prompting
from generation.generators.generator import StageError, generate_candidate
from generation.generators.providers import OpenAICompatibleProvider, ProviderError, ReplayProvider, make_provider


def test_missing_credentials_fail_clearly(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_COMPATIBLE_BASE_URL", raising=False)
    monkeypatch.setattr("gjcore.env.REPO_ROOT", tmp_path)  # no .env file
    with pytest.raises(MissingCredentialsError, match="OPENAI_COMPATIBLE_BASE_URL"):
        OpenAICompatibleProvider(model="some-model")


def test_unknown_provider_rejected():
    with pytest.raises(ProviderError):
        make_provider("nope")


def test_prompts_render_without_missing_variables():
    sc = [s for s, _ in load_records(repo_path("generation/scenarios"), "scenarios")][0]
    text = prompting.stage1_prompt(sc, sc["task_types"][0], "2026-09-27")
    assert "{{" not in text and sc["goal_seed"] in text
    ex = [r for r, _ in load_examples(repo_path("data/raw/examples"))][0]
    assert "{{" not in prompting.stage2_prompt(ex["task_type"], ex["input"])
    assert "{{" not in prompting.stage3_prompt(ex["task_type"], ex["input"], ex["expected_output"], ["unnecessary_questions"])


def test_bundled_schema_has_no_refs():
    assert "$ref" not in json.dumps(prompting.bundled_schema("input_context"))


def _scenario_for(example):
    return {"id": "sc-test-001", "domain": example["domain"], "language": example["language"],
            "input_language": example["input_language"], "goal_size": example["goal_size"] if example["goal_size"] != "n/a" else "medium",
            "safety_category": example["safety_category"], "persona": "x", "goal_seed": "x",
            "task_types": [example["task_type"]]}


def test_generate_candidate_end_to_end_with_replayed_responses():
    ex = next(r for r, _ in load_examples(repo_path("data/raw/examples")) if r["id"] == "gj-daily-001")
    replies = iter([json.dumps(ex["input"], ensure_ascii=False), json.dumps(ex["expected_output"], ensure_ascii=False)])
    rec, notes = generate_candidate(None, _scenario_for(ex), ex["task_type"], 7, "run-test",
                                    today=ex["input"]["today"], call=lambda s, u: next(replies))
    assert rec["id"] == "gj-gen-00007" and rec["provenance"]["method"] == "pipeline_generated"
    assert rec["scenario_group"] == "sc-test-001"


def test_generate_candidate_rejects_invalid_output():
    ex = next(r for r, _ in load_examples(repo_path("data/raw/examples")) if r["id"] == "gj-daily-001")
    bad = dict(ex["expected_output"], total_minutes=999)
    replies = iter([json.dumps(ex["input"]), json.dumps(bad)])
    with pytest.raises(StageError) as e:
        generate_candidate(None, _scenario_for(ex), ex["task_type"], 1, "run-test", today=ex["input"]["today"],
                           call=lambda s, u: next(replies))
    assert e.value.stage == "output"


def test_replay_provider(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text('{"response": "a"}\n{"response": "b"}\n')
    rp = ReplayProvider(responses_path=str(p))
    assert rp.complete("s", "u") == "a" and rp.complete("s", "u") == "b"
    with pytest.raises(ProviderError):
        rp.complete("s", "u")


class _FakeStream:
    def __init__(self, message, calls, kwargs):
        self.message, self.calls, self.kwargs = message, calls, kwargs

    def __enter__(self):
        self.calls.append(self.kwargs)
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.message


def _fake_anthropic(monkeypatch, message, calls):
    import types
    anthropic = pytest.importorskip("anthropic")

    class FakeClient:
        def __init__(self, **kw):
            self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(
                stream=lambda **kwargs: _FakeStream(message, calls, kwargs)))

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


def test_anthropic_provider_call_shape(monkeypatch):
    import types
    from generation.generators.providers import AnthropicProvider
    calls = []
    msg = types.SimpleNamespace(stop_reason="end_turn", content=[types.SimpleNamespace(type="text", text='{"ok": 1}')])
    _fake_anthropic(monkeypatch, msg, calls)
    p = AnthropicProvider(model="claude-opus-5", effort="high", fallbacks="default")
    assert p.complete("sys", "user") == '{"ok": 1}'
    kw = calls[0]
    assert kw["model"] == "claude-opus-5" and kw["system"] == "sys"
    assert kw["fallbacks"] == "default" and kw["betas"] == ["server-side-fallback-2026-07-01"]
    assert kw["output_config"] == {"effort": "high"} and "temperature" not in kw


def test_anthropic_provider_refusal(monkeypatch):
    import types
    from generation.generators.providers import AnthropicProvider, RefusalError
    msg = types.SimpleNamespace(stop_reason="refusal", content=[], stop_details=types.SimpleNamespace(category="bio"))
    _fake_anthropic(monkeypatch, msg, [])
    with pytest.raises(RefusalError):
        AnthropicProvider(model="claude-opus-5").complete("s", "u")
