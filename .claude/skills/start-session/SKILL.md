---
name: start-session
description: Fresh-session protocol for the GoalJourney repository. Use at the start of a new Claude Code session, before any large or multi-step task, after a context compaction when the project state is unclear, or when the user says "start session" / "where are we". Reconstructs the project state from the repository (state files, git, health check); never asks the user to paste an earlier conversation.
---
# Start a session

Goal: before doing substantial work, know the state of the project and the active milestone from
the repository alone. CLAUDE.md is already loaded, so don't re-read it.

## 1. Repository state

```bash
git status -sb
git branch --show-current
git log --oneline -10
git stash list
```

- **Uncommitted changes** may be unfinished work from an interrupted session. Never discard them.
  Work out what they are with `git diff --stat`. If their purpose is unclear, ask before changing
  them.
- **Branch.** Compare the current branch with the branch the session instructions designate. Work
  and push only on the designated one.

## 2. Read the state files, in this order

1. `docs/PROJECT_STATE.md`: versions, health, blockers.
2. `docs/ACTIVE_MILESTONE.md`: objective, tasks, acceptance criteria, progress, next action.
3. `docs/DECISIONS.md`: skim the `D-NNN` titles, and read in full the ones the task touches.
4. `docs/ROADMAP.md`: where the active milestone sits.

Don't read `DATASET_SPEC.md`, the audits or other large docs in full now. Read only the sections
the task needs.

## 3. Minimal health check (~10 s)

```bash
python3 scripts/gj.py validate | tail -4                  # expect RESULT: PASS
python3 scripts/gj.py revisions check | tail -1           # expect ✓ …
python3 scripts/gj.py eval build-cases --check            # expect ✓ … match
```

Full `make check` takes about 2 minutes. Run it before committing, not necessarily now.

- If a check fails, decide whether it is the active work in progress (continue it) or a regression
  (report it before starting anything new).
- If the state files contradict git (commits after "Last updated", or claims the checks refute),
  trust the repository. Verify with commands, and plan to correct the state files as part of the
  work.

## 4. Place the request in the active milestone

- Map the user's request to a task or acceptance criterion in `ACTIVE_MILESTONE.md`.
- If the milestone is marked *proposed* or has no owner brief, or the request doesn't belong to it,
  confirm the scope with one short question before substantial work, unless the request is already
  explicit.
- Check the decisions the task touches. A task that would contradict a decision needs a new or
  superseding decision first. Never override one silently.

## 5. Summarise internally, then proceed

Hold a short internal summary:

- branch and last commit;
- versions;
- active milestone and next action;
- health;
- blockers;
- which files the task will change;
- which skill applies (`/dataset-review`, `/dataset-generation`, `/evaluation`, `/release-check`,
  and `/milestone-complete` at the end).

Tell the user at most a one-line orientation, unless they asked for a status report.

## Rules that apply for the rest of the session

- Keep durable facts in the repository, not only in the conversation.
- At checkpoints, commit and update the progress in `ACTIVE_MILESTONE.md`.
- Keep large files out of the context (`docs/CONTEXT_MANAGEMENT.md` §6). Use subagents only when
  the rules in §7 say so.
