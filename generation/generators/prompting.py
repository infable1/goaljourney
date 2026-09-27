"""Rendering of the versioned teacher prompts (prompts/generation/v<ver>/)."""
import copy
import json
from functools import lru_cache

from gjcore import schemas
from gjcore.config import versions
from gjcore.io import load_yaml, sha256_file
from gjcore.paths import EVALUATION_DIR, PROMPTS_DIR
from gjcore.prompting import navigator_system_prompt


def prompt_dir(version=None):
    return PROMPTS_DIR / "generation" / f"v{version or versions()['generation_prompt_version']}"


@lru_cache(maxsize=None)
def template(name, version=None) -> str:
    return (prompt_dir(version) / name).read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def operation_guides(version=None) -> dict:
    return load_yaml(prompt_dir(version) / "operation_guides.yaml")


@lru_cache(maxsize=None)
def failure_mode_catalogue(version=None) -> dict:
    return load_yaml(prompt_dir(version) / "failure_modes.yaml")


def prompt_file_hashes(version=None) -> dict:
    d = prompt_dir(version)
    return {p.name: sha256_file(p) for p in sorted(d.iterdir()) if p.is_file()}


def render(text: str, **variables) -> str:
    for key, value in variables.items():
        text = text.replace("{{" + key + "}}", value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=1))
    missing = [seg.split("}}")[0] for seg in text.split("{{")[1:]]
    if missing:
        raise KeyError(f"unrendered template variables: {missing}")
    return text


def bundled_schema(name: str) -> dict:
    """Inline all $refs so the teacher sees one self-contained schema."""
    registry = {n: schemas.validator(n).schema for n in schemas.schema_names()}

    def resolve(ref, base):
        file, _, pointer = ref.partition("#")
        doc = registry[file.removesuffix(".json")] if file else registry[base]
        node = doc
        for part in [p for p in pointer.split("/") if p]:
            node = node[part]
        return node, (file.removesuffix(".json") if file else base)

    def walk(node, base, depth):
        if isinstance(node, dict):
            if "$ref" in node and depth < 12:
                target, new_base = resolve(node["$ref"], base)
                merged = {**copy.deepcopy(target), **{k: v for k, v in node.items() if k != "$ref"}}
                return walk(merged, new_base, depth + 1)
            return {k: walk(v, base, depth) for k, v in node.items()
                    if k not in ("$schema", "$id", "$defs")}
        if isinstance(node, list):
            return [walk(v, base, depth) for v in node]
        return node

    return walk(registry[name], name, 0)


def rubric_summary() -> str:
    rubric = load_yaml(EVALUATION_DIR / "rubrics" / "dataset_quality_rubric.yaml")
    return "\n".join(f"- {name}: {spec['question']}" for name, spec in rubric["criteria"].items())


def stage1_prompt(scenario, operation, today) -> str:
    guide = operation_guides()[operation]
    lang = {"ru": "Russian", "en": "English", "mixed": "a natural mix of Russian and English (one predominant)"}[scenario["input_language"]]
    return render(template("stage1_input.md"), operation=operation, today=today,
                  scenario_json=json.dumps(scenario, ensure_ascii=False, indent=1),
                  operation_input_hint=guide["input_hint"], input_language_hint=lang,
                  input_schema=json.dumps(bundled_schema("input_context"), ensure_ascii=False))


def stage2_prompt(operation, input_ctx, few_shot=None) -> str:
    block = ""
    if few_shot:
        block = ("Reference example of a good output for the same operation (different situation — do not copy its content):\n"
                 f"Input:\n{json.dumps(few_shot['input'], ensure_ascii=False)}\n"
                 f"Output:\n{json.dumps(few_shot['expected_output'], ensure_ascii=False)}\n")
    return render(template("stage2_output.md"), operation=operation,
                  navigator_principles=navigator_system_prompt(),
                  operation_guide=operation_guides()[operation]["guide"],
                  rubric_summary=rubric_summary(), few_shot_block=block,
                  input_json=json.dumps(input_ctx, ensure_ascii=False, indent=1),
                  output_schema=json.dumps(bundled_schema(schemas.OPERATION_SCHEMAS[operation]), ensure_ascii=False))


def stage3_prompt(operation, input_ctx, expected, failure_modes) -> str:
    cat = failure_mode_catalogue()
    defs = "\n".join(f"- {m}: {cat[m]['definition']}" for m in failure_modes)
    return render(template("stage3_contrastive.md"), operation=operation, failure_modes=", ".join(failure_modes),
                  failure_mode_definitions=defs, input_json=json.dumps(input_ctx, ensure_ascii=False, indent=1),
                  expected_json=json.dumps(expected, ensure_ascii=False, indent=1),
                  output_schema=json.dumps(bundled_schema(schemas.OPERATION_SCHEMAS[operation]), ensure_ascii=False))
