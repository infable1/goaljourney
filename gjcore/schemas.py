"""JSON Schema registry: loads every schema of one schema version and validates by name or operation.

The current version lives in schemas/*.json; older versions are frozen under
schemas/archive/v<version>/ (see schemas/archive/README.md). Records carry `schema_version` and are
validated against the schema set of their own version, so old releases stay reproducible.
"""
from functools import lru_cache

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .io import load_json
from .paths import SCHEMAS_DIR

BASE = "https://schemas.goaljourney.invalid/v{version}/"

OPERATION_SCHEMAS = {
    "goal_clarification": "goal_clarification",
    "feasibility_assessment": "feasibility",
    "journey_generation": "journey_generation",
    "task_generation": "task_generation",
    "verification_protocol_design": "verification_protocol_design",
    "verification_result": "verification_result",
    "route_adaptation": "route_adaptation",
    "daily_plan": "daily_plan",
    "navigator_response": "navigator_response",
    "goal_change": "goal_change",
    "web_research_decision": "web_research_decision",
    "safety_classification": "safety",
    "memory_extraction": "memory_extraction",
    "progress_update": "progress_update",
}

# Operations whose output is shown to the user (must carry message_to_user in the user's language).
USER_FACING_OPERATIONS = {op for op in OPERATION_SCHEMAS if op not in {"memory_extraction", "web_research_decision"}}


def current_version() -> str:
    from .config import versions
    return versions()["schema_version"]


def version_key(version: str) -> tuple:
    return tuple(int(p) for p in str(version).split("."))


def available_versions() -> list:
    archived = [p.name[1:] for p in (SCHEMAS_DIR / "archive").glob("v*") if p.is_dir()]
    return sorted(set(archived) | {current_version()}, key=version_key)


def _resolve(version):
    cur = current_version()
    version = cur if version is None else str(version)
    if version == cur:
        return version, SCHEMAS_DIR
    d = SCHEMAS_DIR / "archive" / f"v{version}"
    if not d.is_dir():
        raise KeyError(f"no schemas for version {version!r}; known: {available_versions()}")
    return version, d


@lru_cache(maxsize=None)
def _load_all(version=None):
    version, directory = _resolve(version)
    base = BASE.format(version=version)
    schemas, resources = {}, []
    for path in sorted(directory.glob("*.json")):
        schema = load_json(path)
        expected_id = base + path.name
        if schema.get("$id") != expected_id:
            raise ValueError(f"{path}: $id must be {expected_id!r}, got {schema.get('$id')!r}")
        Draft202012Validator.check_schema(schema)
        schemas[path.stem] = schema
        resources.append((expected_id, Resource.from_contents(schema, default_specification=DRAFT202012)))
    return schemas, Registry().with_resources(resources)


def schema_names(version=None):
    return sorted(_load_all(version)[0])


@lru_cache(maxsize=None)
def validator(name: str, version=None) -> Draft202012Validator:
    schemas, registry = _load_all(version)
    if name not in schemas:
        raise KeyError(f"Unknown schema {name!r}; known: {sorted(schemas)}")
    return Draft202012Validator(schemas[name], registry=registry)


def _format_error(err) -> str:
    loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
    msg = err.message
    if len(msg) > 300:
        msg = msg[:300] + "..."
    return f"{loc}: {msg}"


def validate(name: str, instance, version=None) -> list:
    """Return a list of human-readable error strings (empty if valid)."""
    errors = sorted(validator(name, version).iter_errors(instance), key=lambda e: list(e.absolute_path))
    return [_format_error(e) for e in errors]


def validate_output(operation: str, output, version=None) -> list:
    if operation not in OPERATION_SCHEMAS:
        return [f"<root>: unknown operation {operation!r}"]
    errors = validate(OPERATION_SCHEMAS[operation], output, version)
    if isinstance(output, dict) and output.get("type") != operation:
        errors.insert(0, f"type: expected {operation!r}, got {output.get('type')!r}")
    return errors
