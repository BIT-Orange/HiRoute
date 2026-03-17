# Colab Workflow

This workflow is for long-running `smartcity_v3` ndnSIM experiments that are too heavy for a local laptop.
It assumes the repository is pushed to GitHub with the required `v3` inputs tracked in git.

## What Must Be In GitHub

The Colab runtime must be able to clone one repository and run immediately. The tracked payload should therefore include:

- all code under `ns-3/`, `scripts/`, `tools/`, `configs/`, `paper/`
- `requirements.txt`
- `data/processed/smartcity_v3/**`
- `data/processed/ndnsim/topology_mapping_rf_3967_exodus.csv`
- `data/processed/ndnsim/topology_mapping_rf_1239_sprint.csv`
- `data/interim/topologies/rf_3967_exodus.annotated.txt`
- `data/interim/topologies/rf_1239_sprint.annotated.txt`
- `data/processed/eval/workload_audit_v3.json`

Raw downloads and local run directories remain outside git.

## Local Preparation

1. Commit code plus the tracked `v3` inputs.
2. Push the branch to GitHub.
3. Open [`colab/HiRoute_v3_remote_runner.ipynb`](/Users/jiyuan/Desktop/HiRoute/colab/HiRoute_v3_remote_runner.ipynb) in Colab.

## Remote Build

The notebook performs four steps:

1. Clone the selected branch from GitHub using a personal access token.
2. Create a Colab-local virtualenv, install Python dependencies, and build `ns-3`/`ndnSIM`.
3. Run selected experiment matrices with [`scripts/run/run_experiment_matrix.py`](/Users/jiyuan/Desktop/HiRoute/scripts/run/run_experiment_matrix.py).
4. Commit and push registries, aggregates, tables, and figures back to git.

## Matrix Runner Defaults

`run_experiment_matrix.py` resumes from `runs/registry/runs.csv` and skips already completed combinations.

For experiments that define `frontier_schemes` and `reference_schemes`:

- frontier schemes run across the full sweep
- reference schemes run only at the configured default budget or default manifest size

This matches the promotion and figure-validation rules and avoids wasting large-machine time on unused sweep points.

## Recommended Colab Settings

- `max_workers=1` for first-pass official runs
- only increase to `2` after verifying memory stability
- use a runtime with high system RAM; GPU VRAM does not help ndnSIM
- do not rely on `python3 -m venv` in Colab; the hosted `/usr/local` Python often does not match Ubuntu's `python3-venv` packages cleanly
- use `python3 -m virtualenv .venv` instead, after `python3 -m pip install virtualenv`

## Result Return Path

After the notebook pushes results:

```bash
git pull --rebase origin <branch>
```

Pull back:

- `runs/registry/*.csv`
- `results/aggregate/v3/*.csv`
- `results/tables/v3/*.csv`
- `results/figures/v3/*.pdf`

Do not pull `runs/completed/**` from Colab. The formal registry and aggregate outputs are the canonical return artifacts.
