# Context management

How GoalJourney work is organised across many independent Claude Code sessions without exhausting
the context window. The short version is in `CLAUDE.md`; this file is the full policy.

## 1. Session rule

* **One major milestone per primary session.** Plan, implement, verify and complete it
  (`/milestone-complete`) in one session.
* **When the milestone is complete, start a new session** for the next one. Do not carry the old
  conversation forward: everything the next session needs is in the repository.
* **Checkpoint long milestones.** If a milestone outgrows one session, stop at a checkpoint:
  1. commit the work in progress;
  2. update the Progress and Next action sections of `docs/ACTIVE_MILESTONE.md`;
  3. continue in a fresh session with `/start-session`.
* **Unrelated small tasks** (a doc fix, a question) don't need the milestone ritual. They still must
  not leave the state files wrong.

## 2. State rule

The repository is the durable, authoritative project state. Conversation history is not. If a chat
statement and the repository disagree, the repository wins: verify with commands, then fix whichever
is wrong.

| File | Holds | Update when |
|---|---|---|
| `docs/PROJECT_STATE.md` | Versions, branches, capabilities, health, blockers — facts only | A milestone completes, a version bumps, or a blocker appears or clears |
| `docs/ACTIVE_MILESTONE.md` | The one active milestone: objective, tasks, acceptance criteria, progress, blockers, next action | At every checkpoint, and at completion (then replace it with the next milestone) |
| `docs/DECISIONS.md` | Durable product and architecture decisions (D-NNN) | A decision is made or superseded; never delete entries |
| `docs/ROADMAP.md` | Milestone-level plan and status | A milestone starts, completes or is re-scoped |
| `CHANGELOG.md` | What changed, per release or milestone | Milestone completion |

`tests/test_orchestration.py` keeps the versions in `PROJECT_STATE.md` in sync with
`configs/versions.yaml` and checks the structure of the orchestration files.

## 3. Recovery rule

At the beginning of a new milestone session, run `/start-session`, or do the same by hand. Inspect
the following before doing substantial work:

1. `CLAUDE.md` (loaded automatically);
2. `docs/PROJECT_STATE.md`;
3. `docs/ACTIVE_MILESTONE.md`;
4. `docs/DECISIONS.md`;
5. `docs/ROADMAP.md`;
6. `git status` and `git log --oneline -10`.

Also run the minimal health check (`gj validate`, `gj revisions check`,
`gj eval build-cases --check`; about 10 s).

**Never ask the user to paste a previous conversation.** If something is missing from the state
files, reconstruct it from git history and the docs, then write it down.

## 4. Compaction rule

* **Automatic compaction stays on.** Never disable it.
* **The threshold is early.** `.claude/settings.json` sets `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=75`,
  so compaction starts at about 75% of the window instead of close to full. This leaves room to
  finish the current step coherently.
* **Before a likely compaction, save state.** When context is high or a large step is done:
  1. commit the work in progress, or write it into the relevant file (never leave the only copy of
     a decision in the conversation);
  2. update `ACTIVE_MILESTONE.md` progress.
* **Personal overrides** go in `.claude/settings.local.json`, which is git-ignored.

## 5. Context inspection

* **`/context`** shows what fills the window: memory files, rules, skills, tools and messages. Check
  it after large exploratory steps, or when responses start losing earlier details.
* **`/compact <focus>`** compacts at a natural breakpoint, with an instruction about what to keep.
  For example: `/compact keep the task list, failing test names, files changed and open questions;
  drop exploration output`.
* **`/clear`** is for switching to an unrelated task, and only after state is saved in the repo.

## 6. Keeping large content out of the window

Read what the task needs, not whole files.

| Content | Size | Read it by |
|---|---|---|
| `data/{train,validation,test}/goaljourney-v*.jsonl` | ~0.4 MB each | `grep` for an id, or `python3 scripts/gj.py stats`; never read whole |
| `evaluation/cases/v0.2.0/*.yaml` (generated) | up to 160 KB | read the builder in `evaluation/builders/v0_2_0/` instead, or `grep -n` a case id |
| `data/revisions/snapshots/*.json` | 72 files, 0.75 MB | `gj revisions diff <example-id>` |
| `review/audit_findings_v*.json` | ~100 KB | `gj audit --record <id>` or `gj audit` summary |
| `data/raw/examples/*.yaml` | up to 78 KB | `grep -n "id: gj-…"`, then read that range |
| `DATASET_SPEC.md`, policy/audit docs | 10–40 KB | the section you need (`grep -n "^## "`) |
| Command output (`make check`, eval runs, leakage) | long | `tail`, `grep`, or read `report.md`, not `predictions.jsonl` |

A sweeping read that yields only findings belongs in a subagent (§7).

## 7. Orchestration: when to use subagents

Specialist subagents are in `.claude/agents/`. Each has a narrow job, works in its own context, reads
only what its task needs, and returns concise findings with stated uncertainty.

| Agent | Use it for |
|---|---|
| `dataset-auditor` | Auditing a batch of examples or ledger revisions against the spec, policies and known issues |
| `evaluation-engineer` | Analysing eval runs and reports, coverage and discrimination; drafting eval cases in the builders |
| `verification-reviewer` | Verification protocols and results: capabilities (POL-A), evidence ceilings (POL-B), contradictions |
| `safety-reviewer` | Safety classifications, sensitive domains, referrals, privacy and memory |
| `architecture-reviewer` | Designs and structural changes vs `docs/DECISIONS.md`, versioning and immutability |
| `code-reviewer` | A diff before commit: correctness, tests, repository conventions |

**Use a subagent when:**

* a task reads many files but only the findings are needed, e.g. auditing 20 examples or
  summarising an evaluation report;
* independent analyses can run in parallel, e.g. `safety-reviewer` and `verification-reviewer` on
  the same batch;
* a specialist second look adds value before committing, e.g. `code-reviewer` on a large diff;
* context isolation protects the main session from bulky intermediate output.

**Do not use a subagent when:**

* the task is a simple sequential edit;
* only one or two files are involved;
* the next step depends on detailed context from the previous one, e.g. fixing a validator while
  watching test failures;
* briefing the agent would cost more than doing the work.

Subagents are never spawned by default for every task.

**How to brief one.** A subagent starts cold. Give it:

* the exact question;
* the files or ids to read;
* the relevant decision or policy ids;
* the expected output format.

Its report is not shown to the user, so relay what matters. Subagents never record review decisions
or approve anything. The main session owns every edit and commit, except edits explicitly delegated
to `evaluation-engineer` in `evaluation/builders/`.

## 8. Skills and rules: loaded on demand

* **Skills** (`.claude/skills/`) hold step-by-step workflows. They load only when invoked or when
  their description matches the task.

  | Skill | What it is |
  |---|---|
  | `/start-session` | fresh-session protocol |
  | `/milestone-complete` | completion protocol |
  | `/dataset-review` | review workflow |
  | `/dataset-generation` | generation workflow |
  | `/evaluation` | eval workflow |
  | `/release-check` | releases, gates and pre-training readiness |

  A separate `model-training` skill was considered and deferred. No training code exists yet, and
  training is blocked by the gates. `/release-check` holds the pre-training readiness checklist. Write
  the training skill together with the training code in M3.
* **Rules** (`.claude/rules/`) are path-scoped with `paths:` frontmatter. They load only when files
  in their area are touched.

  | Rule | Area |
  |---|---|
  | `product` | policies, capabilities, the navigator prompt |
  | `ai` | providers, prompts, runners |
  | `dataset` | data, schemas, review, pipelines |
  | `evaluation` | builders and cases |
  | `testing` | tests, validators, metrics |
  | `security` | secrets, credentials, config |

## 9. Protecting against context pollution

`CLAUDE.md` is loaded into every session, so it holds only what every session needs, in under 200
lines (a test enforces the limit). **Never put these into `CLAUDE.md`:**

| Content | Where it belongs |
|---|---|
| Full datasets or example records | `data/` (read by id) |
| Long evaluation cases | `evaluation/builders/` / `evaluation/cases/` |
| Historical chat transcripts or session logs | nowhere; distil the outcome into the state files or `CHANGELOG.md` |
| Large research or audit reports | `docs/` (e.g. `DATASET_AUDIT_v*.md`) |
| Full schemas | `schemas/`; `DATASET_SPEC.md` describes them |
| Subsystem implementation notes | the matching `.claude/rules/*.md` (path-scoped) or a skill |
| Step-by-step workflows | `.claude/skills/*/SKILL.md` |

When adding to `CLAUDE.md`, ask whether every session needs it. If not, put a pointer in
`CLAUDE.md` and the content elsewhere.
