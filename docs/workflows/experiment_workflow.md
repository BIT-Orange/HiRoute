# Experiment Workflow

## Mandatory stages

1. Define or update a hypothesis card in `docs/roadmap/open_questions.md`.
2. Register the planned experiment in `docs/experiments/experiment_matrix.md`.
3. Freeze the experiment config in `configs/experiments/`.
4. Run a dry run into `runs/pending/`.
5. Run official seeds into `runs/completed/`.
6. Aggregate only from registries.
7. Promote only runs that satisfy the configured promotion rule.
8. Bind promoted figures to paper claims and revision notes.

## Hard rules

- No formal run without an experiment config.
- No formal run without a run manifest.
- Dry runs never enter promoted results.
- Aggregation must read tracked registries instead of manual path lists.
- Paper figures must originate from promoted runs only.
- Each figure requires a figure note and a registry entry.

## Standard outputs per run

- `manifest.yaml`
- `stdout.log`
- `stderr.log`
- `query_log.csv`
- `probe_log.csv`
- `search_trace.csv`
- `state_log.csv`
- `failure_event_log.csv`
- `config_snapshot/`
- `git_snapshot.txt`
- `env_snapshot.txt`
- `notes.md`
