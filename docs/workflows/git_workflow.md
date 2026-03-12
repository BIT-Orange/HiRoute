# Git Workflow

## Repository policy

- This repository uses one top-level Git root only.
- Formal results must come from committed, clean states.
- Each validated batch of work is committed immediately.

## Allowed commit prefixes

- `plan`
- `data`
- `feat`
- `fix`
- `eval`
- `paper`
- `chore`

## Branch naming

- `feat/...`
- `exp/...`
- `fix/...`
- `paper/...`
- `data/...`
- `chore/...`

## Tagging

- `dataset-smartcity-v1`
- `exp-main-v1-frozen`
- `figures-<milestone>`
- `paper-draft-v<round>`

## Commit discipline

1. Stage only one coherent batch of changes.
2. Run at least the smoke checks relevant to that batch.
3. Commit before starting the next batch.
4. Do not generate official figures from a dirty worktree.
