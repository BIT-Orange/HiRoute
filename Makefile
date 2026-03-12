EXP ?= configs/experiments/exp_main_v1.yaml
SCHEME ?= hiroute
SEED ?= 1
MODE ?= official

.PHONY: dataset validate-dataset run aggregate promote figures paper-check

dataset:
	python3 scripts/build_dataset/build_all.py --config configs/datasets/smartcity_v1.yaml

validate-dataset:
	python3 scripts/build_dataset/validate_dataset.py

run:
	python3 scripts/run/run_experiment.py --experiment $(EXP) --scheme $(SCHEME) --seed $(SEED) --mode $(MODE)

aggregate:
	python3 scripts/eval/aggregate_experiment.py --experiment $(EXP)

promote:
	python3 scripts/eval/promote_runs.py --experiment $(EXP)

figures:
	python3 scripts/plots/plot_experiment.py --experiment $(EXP)

paper-check:
	python3 tools/validate_figures.py --experiment $(EXP) --aggregate results/aggregate/main_success_overhead.csv --figure-note paper/notes/fig_main_success_overhead.md
