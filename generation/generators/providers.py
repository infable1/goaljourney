"""LLM providers behind one interface: complete(system, user) -> text.

* anthropic          — teacher model for synthetic generation, via the official `anthropic` SDK
                       (optional dependency: `pip install anthropic`). Streaming + refusal handling,
                       server-side refusal fallbacks enabled by default.
* openai_compatible  — any OpenAI-compatible chat-completions endpoint (vLLM, Ollama, llama.cpp server,
                       ...). Intended for serving open-weight models, e.g. the fine-tuned navigator
                       under evaluation. Plain HTTPS, no SDK.
* replay             — offline canned responses from a JSONL file (tests, dry runs, CI).

Credentials come only from the environment / .env (gjcore.env.require_env) and fail loudly.
"""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from gjcore.config import load_config
from gjcore.env import require_env
from gjcore.io import read_jsonl


class ProviderError(RuntimeError):
    pass


class RefusalError(ProviderError):
    """The model declined the request (stop_reason == "refusal") and no fallback served it."""


class BaseProvider:
    name = "base"

    def __init__(self, model: str, **params):
        self.model = model
        self.params = params

    def complete(self, system: str, user: str) -> str:
        raise NotImplementedError

    def describe(self) -> dict:
        """Recorded in run manifests for reproducibility (never includes secrets)."""
        return {"provider": self.name, "model": self.model,
                **{k: v for k, v in self.params.items() if "key" not in k.lower()}}


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, model, api_key_env="ANTHROPIC_API_KEY", max_tokens=32000, effort=None,
                 fallbacks="default", timeout_seconds=600, **_ignored):
        super().__init__(model, max_tokens=max_tokens, effort=effort, fallbacks=fallbacks)
        try:
            import anthropic  # optional dependency, only needed for generation
        except ImportError as e:
            raise ProviderError("The 'anthropic' package is required for provider 'anthropic': pip install anthropic") from e
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=require_env(api_key_env, "the Anthropic teacher model"),
                                           timeout=timeout_seconds)

    def complete(self, system: str, user: str) -> str:
        kwargs = dict(model=self.model, max_tokens=self.params["max_tokens"], system=system,
                      messages=[{"role": "user", "content": user}])
        if self.params.get("effort"):
            kwargs["output_config"] = {"effort": self.params["effort"]}
        if self.params.get("fallbacks"):
            # Server-side refusal fallback: a declined request is re-run on Anthropic's recommended model.
            kwargs["betas"] = ["server-side-fallback-2026-07-01"]
            kwargs["fallbacks"] = self.params["fallbacks"]
        # Streaming avoids HTTP timeouts on long outputs (full journeys can be long).
        with self._client.beta.messages.stream(**kwargs) as stream:
            message = stream.get_final_message()
        if message.stop_reason == "refusal":
            category = getattr(getattr(message, "stop_details", None), "category", None)
            raise RefusalError(f"model declined the request (category={category})")
        if message.stop_reason == "max_tokens":
            raise ProviderError("output truncated at max_tokens; raise max_tokens in configs/generation.yaml")
        return "".join(b.text for b in message.content if b.type == "text")


class OpenAICompatibleProvider(BaseProvider):
    name = "openai_compatible"

    def __init__(self, model, api_key_env="OPENAI_COMPATIBLE_API_KEY", base_url_env="OPENAI_COMPATIBLE_BASE_URL",
                 max_tokens=8000, temperature=None, timeout_seconds=300, api_key_optional=True, **_ignored):
        if not model:
            raise ProviderError("provider 'openai_compatible' needs a model name (--model or configs)")
        super().__init__(model, max_tokens=max_tokens, temperature=temperature)
        self.base_url = require_env(base_url_env, "the OpenAI-compatible endpoint base URL").rstrip("/")
        try:
            self.api_key = require_env(api_key_env, "the OpenAI-compatible endpoint")
        except Exception:
            if not api_key_optional:
                raise
            self.api_key = None  # local servers (vLLM, Ollama) often need no key
        self.timeout = timeout_seconds

    def complete(self, system: str, user: str) -> str:
        body = {"model": self.model, "max_tokens": self.params["max_tokens"],
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if self.params.get("temperature") is not None:
            body["temperature"] = self.params["temperature"]
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=json.dumps(body).encode("utf-8"),
                                     headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            raise ProviderError(f"HTTP {e.code} from {self.base_url}: {detail}") from e
        except urllib.error.URLError as e:
            raise ProviderError(f"cannot reach {self.base_url}: {e.reason}") from e
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"unexpected response shape: {str(data)[:300]}") from e


class ReplayProvider(BaseProvider):
    """Returns recorded responses in order (or keyed by prompt text when a 'user' field is present)."""
    name = "replay"

    def __init__(self, model="replay", responses_path=None, **_ignored):
        super().__init__(model)
        if not responses_path:
            raise ProviderError("provider 'replay' needs responses_path")
        self._rows = read_jsonl(Path(responses_path))
        self._by_user = {r["user"]: r["response"] for r in self._rows if "user" in r}
        self._i = 0

    def complete(self, system: str, user: str) -> str:
        if user in self._by_user:
            return self._by_user[user]
        if self._i >= len(self._rows):
            raise ProviderError("replay responses exhausted")
        row = self._rows[self._i]
        self._i += 1
        return row["response"]


PROVIDERS = {p.name: p for p in (AnthropicProvider, OpenAICompatibleProvider, ReplayProvider)}


def make_provider(name=None, model=None, config_name="generation", **overrides) -> BaseProvider:
    cfg = load_config(config_name)
    name = name or cfg.get("provider")
    if name not in PROVIDERS:
        raise ProviderError(f"unknown provider {name!r}; choose one of {sorted(PROVIDERS)}")
    params = dict((cfg.get("providers") or {}).get(name, {}))
    params.update({k: v for k, v in overrides.items() if v is not None})
    params["model"] = model or params.get("model")
    return PROVIDERS[name](**params)


def with_retries(fn, retries=3, backoff=(2, 4, 8)):
    """Retry transient provider failures (not refusals, not credential errors)."""
    for attempt in range(retries + 1):
        try:
            return fn()
        except RefusalError:
            raise
        except ProviderError:
            if attempt == retries:
                raise
            time.sleep(backoff[min(attempt, len(backoff) - 1)])
