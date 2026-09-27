"""JSON Schema registry: loads every schema in schemas/ and validates by name or operation."""
from functools import lru_cache

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .io import load_json
from .paths import SCHEMAS_DIR

BASE_URI = "https://schemas.goaljourney.invalid/v0.1.0/"

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


@lru_cache(maxsize=1)
def _load_all():
    schemas = {}
    resources = []
    for path in sorted(SCHEMAS_DIR.glob("*.json")):
        schema = load_json(path)
        expected_id = BASE_URI + path.name
        if schema.get("$id") != expected_id:
            raise ValueError(f"{path.name}: $id must be {expected_id!r}, got {schema.get('$id')!r}")
        Draft202012Validator.check_schema(schema)
        schemas[path.stem] = schema
        resources.append((expected_id, Resource.from_contents(schema, default_specification=DRAFT202012)))
    registry = Registry().with_resources(resources)
    return schemas, registry


def schema_names():
    return sorted(_load_all()[0])


@lru_cache(maxsize=None)
def validator(name: str) -> Draft202012Validator:
    schemas, registry = _load_all()
    if name not in schemas:
        raise KeyError(f"Unknown schema {name!r}; known: {sorted(schemas)}")
    return Draft202012Validator(schemas[name], registry=registry)


def _format_error(err) -> str:
    loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
    msg = err.message
    if len(msg) > 300:
        msg = msg[:300] + "..."
    return f"{loc}: {msg}"


def validate(name: str, instance) -> list:
    """Return a list of human-readable error strings (empty if valid)."""
    errors = sorted(validator(name).iter_errors(instance), key=lambda e: list(e.absolute_path))
    return [_format_error(e) for e in errors]


def validate_output(operation: str, output) -> list:
    if operation not in OPERATION_SCHEMAS:
        return [f"<root>: unknown operation {operation!r}"]
    errors = validate(OPERATION_SCHEMAS[operation], output)
    if isinstance(output, dict) and output.get("type") != operation:
        errors.insert(0, f"type: expected {operation!r}, got {output.get('type')!r}")
    return errors
