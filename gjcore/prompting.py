"""The navigator model's runtime prompt format — shared by SFT export and model evaluation so the
model is evaluated with exactly the prompt it was trained on."""
import json
from functools import lru_cache

from .config import load_config
from .paths import repo_path


@lru_cache(maxsize=None)
def navigator_system_prompt(path=None) -> str:
    path = path or load_config("export")["navigator_prompt"]
    return repo_path(path).read_text(encoding="utf-8").strip()


def _dumps(obj) -> str:
    cfg = load_config("export")
    return json.dumps(obj, ensure_ascii=cfg.get("ensure_ascii", False), indent=cfg.get("json_indent"),
                      separators=None if cfg.get("json_indent") else (",", ":"))


def prompt_messages(input_ctx: dict) -> list:
    """[system, user] messages for one request. The user turn is the request object as JSON."""
    return [{"role": "system", "content": navigator_system_prompt()},
            {"role": "user", "content": _dumps(input_ctx)}]


def assistant_message(output: dict) -> dict:
    return {"role": "assistant", "content": _dumps(output)}
