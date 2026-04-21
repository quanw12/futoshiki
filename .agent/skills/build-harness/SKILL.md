---
name: build-harness
description: Local harness workflow for scoped repository tasks with deterministic reporting and safe recovery.
---

# Build Harness (Local)

Use this skill when running project tasks through the local `.agent` harness.

## Goal

Execute tasks with predictable outputs, minimal risk, and clear recovery instructions.

## Workflow

1. Parse request and restate objective in one sentence.
2. Gather context from relevant files only.
3. Build a short execution plan (3-5 steps).
4. Execute step-by-step and verify after edits.
5. Return structured result for each phase.

## Output contract

Every phase should return:

- `status`: success | warning | error
- `summary`: one-line outcome
- `next_actions`: exact next steps
- `artifacts`: files changed, logs, or generated outputs

## Recovery contract

For each failure:

- root cause hint
- safe retry instruction
- explicit stop condition

## Constraints

- Keep scope local to this repository.
- Prefer small diffs and clear rationale.
- Do not include unrelated refactors.
