"""Config loading. Configs never contain secrets (see gjcore.env)."""
from functools import lru_cache

from .io import load_yaml
from .paths import CONFIGS_DIR


@lru_cache(maxsize=None)
def load_config(name: str) -> dict:
    """Load configs/<name>.yaml."""
    return load_yaml(CONFIGS_DIR / f"{name}.yaml")


def versions() -> dict:
    return load_config("versions")
