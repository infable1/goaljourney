"""Repository-relative paths. Everything resolves from the repo root, not the CWD."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = REPO_ROOT / "schemas"
CONFIGS_DIR = REPO_ROOT / "configs"
PROMPTS_DIR = REPO_ROOT / "prompts"
DATA_DIR = REPO_ROOT / "data"
EVALUATION_DIR = REPO_ROOT / "evaluation"


def repo_path(p) -> Path:
    """Resolve a path from config (relative to the repo root) to an absolute Path."""
    p = Path(p)
    return p if p.is_absolute() else REPO_ROOT / p


def rel(p) -> str:
    """Render a path relative to the repo root for reports and manifests."""
    try:
        return str(Path(p).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(p)
