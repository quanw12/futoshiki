# Local Agent Rules

These rules apply to all tasks executed through this repository-local harness.

## Execution rules

1. Prefer minimal, reversible edits.
2. Do not modify unrelated files.
3. Validate after changes (lint/test/build when applicable).
4. Report assumptions and blockers explicitly.
5. Before starting any task, read `.agent/skills/karpathy-guidelines/SKILL.md`.

## Tooling rules

1. Read before writing.
2. Use structured outputs for each step:
   - `status`
   - `summary`
   - `next_actions`
   - `artifacts`
3. If a command fails, provide root-cause hint and safe retry path.
4. For UI work, also read relevant skills under `.agent/skills` (`ui-design`, `high-end-visual-design`, `framer-motion`).

## Safety rules

1. Never use destructive commands unless requested.
2. Do not expose secrets from env files or credentials.
3. Keep all harness artifacts within `.agent` unless user asks otherwise.
