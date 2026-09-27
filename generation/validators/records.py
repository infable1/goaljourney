"""Record-level validation of training examples.

validate_example(record) runs, in order:
  1. envelope schema (schemas/example_record.json)
  2. operation output schema for expected_output
  3. semantic lint of expected_output (must be error-free) and, from v0.1.1, of the input
  4. consistency checks between metadata, input and output
  5. contrastive self-test: every rejected output must be schema-valid (so preference pairs
     teach behaviour, not formatting) and the linter must catch every failure mode that is
     declared ALWAYS_DETECTABLE.

Every step uses the schemas and lint rules of the record's own `schema_version`, so a released
version validates exactly as it did when it was released.
"""
from dataclasses import dataclass, field

from gjcore import schemas
from gjcore.io import canonical_json

from . import semantic
from . import text as T


@dataclass
class ContrastiveResult:
    id: str
    failure_modes: list
    detected_codes: list
    detected_modes: list
    undetected_required: list


@dataclass
class RecordReport:
    id: str
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    contrastive: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.errors


def _user_texts(record):
    conv = ((record.get("input") or {}).get("conversation")) or []
    return [m.get("content", "") for m in conv if m.get("role") == "user"]


def validate_example(record: dict, strict: bool = False) -> RecordReport:
    rid = record.get("id", "<missing id>")
    rep = RecordReport(rid)
    version = record.get("schema_version")
    if version not in schemas.available_versions():
        rep.errors.append(f"schema_version {version!r} is not one of {schemas.available_versions()}")
        return rep

    env_errors = schemas.validate("example_record", record, version)
    rep.errors += [f"ENVELOPE {e}" for e in env_errors]
    op = record.get("task_type")
    out = record.get("expected_output")
    ctx = record.get("input") or {}
    ann = record.get("annotations") or {}
    lang = record.get("language")
    safety = record.get("safety_category")
    if op not in schemas.OPERATION_SCHEMAS or not isinstance(out, dict):
        rep.errors.append("cannot validate expected_output: unknown task_type or missing output")
        return rep

    if ctx.get("operation") != op:
        rep.errors.append(f"input.operation {ctx.get('operation')!r} != task_type {op!r}")
    rep.errors += [f"OUTPUT_SCHEMA {e}" for e in schemas.validate_output(op, out, version)]

    for issue in semantic.lint_output(op, out, ctx, ann, lang, safety, version):
        (rep.errors if issue.level == "error" or strict else rep.warnings).append(str(issue))
    for issue in semantic.lint_input(ctx, version):
        (rep.errors if issue.level == "error" or strict else rep.warnings).append(f"INPUT {issue}")

    # ---- metadata consistency
    if op in schemas.USER_FACING_OPERATIONS and out.get("response_language") != lang:
        rep.errors.append(f"language {lang!r} != expected_output.response_language {out.get('response_language')!r}")
    texts = _user_texts(record)
    if texts:
        detected = T.detect_input_language(texts)
        if detected != record.get("input_language"):
            rep.warnings.append(f"input_language={record.get('input_language')!r} but user messages look {detected!r}")
    behaviors = set(record.get("behavior", []))
    if "decision_summary" in behaviors and not out.get("decision_summary"):
        rep.errors.append("behavior 'decision_summary' but expected_output has no decision_summary")
    if "verification_retry" in behaviors and not ctx.get("verification_history"):
        rep.errors.append("behavior 'verification_retry' but input has no verification_history")
    if "time_adaptation" in behaviors and (out.get("trigger") or {}).get("type") not in {"less_time", "more_time"}:
        rep.errors.append("behavior 'time_adaptation' needs trigger less_time/more_time")
    if "memory" in behaviors and op != "memory_extraction" and not ann.get("must_not_mention"):
        rep.errors.append("behavior 'memory' (isolation) needs annotations.must_not_mention")
    if op == "goal_clarification" and not ("known_targets" in ann or "critical_targets" in ann):
        rep.warnings.append("clarification example without known_targets/critical_targets annotations")

    # ---- contrastive self-test
    expected_canon = canonical_json(out)
    for i, cst in enumerate(record.get("contrastive", []) or []):
        cid = cst.get("id", f"contrastive[{i}]")
        cout = cst.get("output")
        modes = cst.get("failure_modes", [])
        schema_errs = schemas.validate_output(op, cout, version) if isinstance(cout, dict) else ["not an object"]
        if schema_errs:
            rep.errors += [f"CONTRASTIVE {cid} schema: {e}" for e in schema_errs[:5]]
        if isinstance(cout, dict) and canonical_json(cout) == expected_canon:
            rep.errors.append(f"CONTRASTIVE {cid} is identical to expected_output")
        issues = semantic.lint_output(op, cout, ctx, ann, lang, safety, version) if isinstance(cout, dict) else []
        codes = sorted({iss.code for iss in issues})
        detected_modes = [m for m in modes if semantic.FAILURE_MODE_CODES.get(m, set()) & set(codes)]
        missing = [m for m in modes if m in semantic.ALWAYS_DETECTABLE and m not in detected_modes]
        if missing:
            rep.errors.append(f"CONTRASTIVE {cid}: linter did not detect always-detectable failure mode(s) {missing} (codes seen: {codes})")
        if schemas.version_key(version) >= schemas.version_key("0.1.1"):
            # A rejected output should differ from the chosen one only in its tagged failure modes (KI-032).
            tagged = set().union(*(semantic.FAILURE_MODE_CODES.get(m, set()) for m in modes)) if modes else set()
            untagged = sorted({iss.code for iss in issues if iss.level == "error"} - tagged)
            if untagged:
                rep.warnings.append(f"CONTRASTIVE {cid}: error codes outside its tagged failure modes {modes}: {untagged}")
        rep.contrastive.append(ContrastiveResult(cid, modes, codes, detected_modes, missing))
    return rep


def check_unique_ids(records):
    seen, dups = set(), set()
    for r in records:
        rid = r.get("id")
        if rid in seen:
            dups.add(rid)
        seen.add(rid)
    return sorted(dups)
