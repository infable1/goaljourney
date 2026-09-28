"""Claude Code orchestration files: CLAUDE.md, .claude/ (settings, rules, skills, agents) and the
durable state files in docs/. These tests keep them well-formed and in sync with the repository
(docs/CONTEXT_MANAGEMENT.md)."""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CLAUDE = ROOT / ".claude"
STATE_FILES = ["docs/PROJECT_STATE.md", "docs/ACTIVE_MILESTONE.md", "docs/DECISIONS.md", "docs/ROADMAP.md"]
REQUIRED_SKILLS = {"start-session", "milestone-complete", "dataset-review", "dataset-generation", "evaluation",
                   "release-check"}
KNOWN_TOOLS = {"Read", "Grep", "Glob", "Bash", "Edit", "Write"}
# Only this agent may edit files, and only in evaluation/builders/ when explicitly delegated (CONTEXT_MANAGEMENT §7).
EDITING_AGENTS = {"evaluation-engineer"}
SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
]


def _text(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _frontmatter(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.relative_to(ROOT)}: missing YAML frontmatter"
    head, _, body = text[4:].partition("\n---\n")
    meta = yaml.safe_load(head)
    assert isinstance(meta, dict), f"{path.relative_to(ROOT)}: frontmatter is not a mapping"
    return meta, body


def _orchestration_files():
    return [ROOT / "CLAUDE.md", *sorted(CLAUDE.rglob("*.md")), *sorted(CLAUDE.glob("*.json")),
            *(ROOT / f for f in STATE_FILES), ROOT / "docs/CONTEXT_MANAGEMENT.md"]


def test_claude_md_is_concise_and_points_to_the_state_files():
    text = _text("CLAUDE.md")
    assert len(text.splitlines()) <= 200, "CLAUDE.md must stay under 200 lines (docs/CONTEXT_MANAGEMENT.md §9)"
    for ref in [*STATE_FILES, "docs/CONTEXT_MANAGEMENT.md"]:
        assert ref in text, f"CLAUDE.md does not reference {ref}"
    assert "/start-session" in text and "/milestone-complete" in text


def test_settings_json_is_valid_and_keeps_autocompact_on():
    settings = json.loads(_text(".claude/settings.json"))
    pct = settings["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"]
    assert isinstance(pct, str) and pct.isdigit() and 1 <= int(pct) <= 100
    assert "DISABLE_AUTO_COMPACT" not in settings.get("env", {}), "auto-compaction must stay enabled"
    assert "Read(./.env)" in settings.get("permissions", {}).get("deny", [])
    assert not (CLAUDE / "settings.local.json").exists() or ".claude/settings.local.json" in _text(".gitignore")


def test_no_secret_like_values_in_orchestration_files():
    for path in _orchestration_files():
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            assert not match, f"{path.relative_to(ROOT)}: secret-like value {match.group(0)[:12]}…"


def test_skills_are_well_formed():
    found = {}
    for skill_dir in sorted(p for p in (CLAUDE / "skills").iterdir() if p.is_dir()):
        skill = skill_dir / "SKILL.md"
        assert skill.exists(), f"{skill_dir.relative_to(ROOT)} has no SKILL.md"
        meta, body = _frontmatter(skill)
        assert meta.get("name") == skill_dir.name, f"{skill.relative_to(ROOT)}: name must equal the directory"
        assert re.fullmatch(r"[a-z0-9-]{1,64}", meta["name"])
        assert isinstance(meta.get("description"), str) and len(meta["description"]) >= 40
        assert body.strip()
        found[meta["name"]] = meta
    assert REQUIRED_SKILLS <= set(found), f"missing skills: {REQUIRED_SKILLS - set(found)}"
    claude_md = _text("CLAUDE.md")
    for name in found:
        assert f"/{name}" in claude_md, f"CLAUDE.md does not list the skill /{name}"


def test_agents_are_narrow_and_well_formed():
    agents = sorted((CLAUDE / "agents").glob("*.md"))
    assert agents, "no subagents defined"
    claude_md, context = _text("CLAUDE.md"), _text("docs/CONTEXT_MANAGEMENT.md")
    for path in agents:
        meta, body = _frontmatter(path)
        name = meta.get("name")
        assert name == path.stem, f"{path.relative_to(ROOT)}: name must equal the file name"
        assert name not in {"general-purpose", "general", "assistant"}, "no general-purpose duplicate agent"
        assert isinstance(meta.get("description"), str) and len(meta["description"]) >= 40
        tools = {t.strip() for t in str(meta.get("tools", "")).split(",") if t.strip()}
        assert tools and tools <= KNOWN_TOOLS, f"{name}: tools must be an explicit subset of {sorted(KNOWN_TOOLS)}"
        if tools & {"Edit", "Write"}:
            assert name in EDITING_AGENTS, f"{name}: only {sorted(EDITING_AGENTS)} may edit files"
        assert "## Output" in body and "uncertainty" in body.lower(), f"{name}: needs an output format with uncertainty"
        assert "never" in body.lower()
        assert name in claude_md and name in context, f"{name} is not listed in CLAUDE.md and CONTEXT_MANAGEMENT.md"


def test_rules_are_path_scoped_to_existing_files():
    rules = sorted((CLAUDE / "rules").glob("*.md"))
    assert {p.stem for p in rules} >= {"product", "ai", "dataset", "testing", "security"}
    for path in rules:
        meta, body = _frontmatter(path)
        globs = meta.get("paths")
        assert isinstance(globs, list) and globs, f"{path.relative_to(ROOT)}: needs a non-empty `paths` list"
        for pattern in globs:
            assert any(ROOT.glob(pattern)), f"{path.relative_to(ROOT)}: `{pattern}` matches no file"
        assert body.strip()


def test_state_files_have_their_sections():
    required = {
        "docs/PROJECT_STATE.md": [r"Last updated: \d{4}-\d{2}-\d{2}", r"^## Versions", r"^## Health", r"^## Blockers"],
        "docs/ACTIVE_MILESTONE.md": [r"^## Milestone ", r"^### Objective", r"^### Acceptance criteria",
                                     r"^### Progress", r"^### Next action"],
        "docs/DECISIONS.md": [r"^\*\*D-001 — "],
        "docs/ROADMAP.md": [r"^\| Milestone \| Goal \| Status \|", r"^## Standing constraints"],
    }
    for rel, patterns in required.items():
        text = _text(rel)
        for pattern in patterns:
            assert re.search(pattern, text, re.M), f"{rel}: missing `{pattern}`"
    ids = re.findall(r"^\*\*(D-\d{3}) — ", _text("docs/DECISIONS.md"), re.M)
    assert len(ids) == len(set(ids)), "decision ids must be unique"


def test_project_state_versions_match_config():
    versions = yaml.safe_load(_text("configs/versions.yaml"))
    rows = dict(re.findall(r"^\| ([a-z /]+?) \| ([^|]+?) \|", _text("docs/PROJECT_STATE.md"), re.M))
    for row, key in [("dataset", "dataset_version"), ("schema", "schema_version"), ("pipeline", "pipeline_version"),
                     ("evaluation", "evaluation_version")]:
        assert rows.get(row) == versions[key], (
            f"docs/PROJECT_STATE.md says {row} {rows.get(row)}, configs/versions.yaml says {versions[key]}")
    prompts = f"{versions['navigator_prompt_version']} / {versions['generation_prompt_version']}"
    assert rows.get("navigator prompt / generation prompts") == prompts
    assert rows.get("base model") == (versions["base_model"]["name"] or "unset")


def test_gitignore_keeps_local_and_secret_files_out():
    lines = {line.strip() for line in _text(".gitignore").splitlines()}
    for pattern in [".env", ".claude/settings.local.json", "checkpoints/", "*.safetensors", "exports/", "scratch/",
                    "evaluation/reports/*/"]:
        assert pattern in lines, f".gitignore must contain {pattern}"
