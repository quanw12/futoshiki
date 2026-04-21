# Harness Spec (Local)

This document defines the contract for task execution under `.agent`.

## 1) Inputs

- Task objective (required)
- Scope boundaries (required)
- Acceptance criteria (recommended)
- Constraints (optional)

## 2) Execution model

Recommended model: hybrid

- Planning: lightweight ReAct reasoning
- Execution: typed tool actions
- Verification: explicit checks after substantive edits

## 3) Phase template

Each phase must produce:

```md
status: success|warning|error
summary: <one-line result>
next_actions:
  - <action 1>
  - <action 2>
artifacts:
  - <file path or output id>
```

## 4) Error handling

On error, include:

- probable root cause
- safe retry command or step
- stop condition to avoid loops

## 5) Completion criteria

A task is complete when:

1. Requested change is implemented.
2. Relevant validations were attempted and reported.
3. Artifacts are documented.
4. Remaining risk is explicitly stated (if any).
