"""Environment/credential handling.

Secrets live only in the process environment or in a git-ignored `.env` file.
`require_env` fails with an actionable message instead of a KeyError deep in a request.
"""
import os

from .paths import REPO_ROOT


class MissingCredentialsError(RuntimeError):
    pass


def load_dotenv(path=None) -> None:
    """Minimal .env loader: KEY=VALUE lines; never overrides variables already set."""
    path = path or REPO_ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def require_env(name: str, purpose: str) -> str:
    load_dotenv()
    value = os.environ.get(name, "").strip()
    if not value:
        raise MissingCredentialsError(
            f"Missing environment variable {name} (needed for {purpose}). "
            f"Set it in your shell or in a git-ignored .env file (see .env.example). "
            f"Secrets are never read from config files."
        )
    return value
