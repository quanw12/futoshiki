# Local Agent Harness

This folder contains a project-local harness for running agent tasks without affecting global setup.

## Layout

- `.agent/skills/build-harness/SKILL.md`: local skill for task execution flow.
- `.agent/skills/karpathy-guidelines/SKILL.md`: mandatory pre-task behavior guardrail.
- `.agent/skills/ui-design/SKILL.md`: UI/UX best practices.
- `.agent/skills/high-end-visual-design/SKILL.md`: premium visual direction.
- `.agent/skills/framer-motion/SKILL.md`: smooth animation and performance guidance.
- `.agent/rules/LOCAL_AGENT_RULES.md`: local rules and guardrails.
- `.agent/HARNESS_SPEC.md`: harness contracts (input/output/error handling).
- `.agent/TASK_TEMPLATE.md`: reusable task brief template.

## How to use

1. Keep prompts and task context in `.md` files inside this folder.
2. Apply the local rule first, then read `karpathy-guidelines` before any task.
3. Execute tasks using the template to keep output predictable.
4. Store run notes in the same folder for reproducibility.

## Scope

- Local-only: this harness is for this repository.
- No global config changes required.
