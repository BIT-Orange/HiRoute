EXP ?= configs/experiments/exp_main_v1.yaml
SCHEME ?= hiroute
SEED ?= 1
MODE ?= official
TOPOLOGY ?= configs/topologies/rocketfuel_3967_exodus.yaml

.PHONY: download-rocketfuel convert-topologies topology-map dataset validate-dataset run aggregate promote figures paper-check

download-rocketfuel:
	bash scripts/download/download_rocketfuel.sh

convert-topologies:
	mkdir -p data/interim/topologies
	cd ns-3 && ./waf --run "hiroute-convert-rocketfuel --latency=../data/raw/rocketfuel/3967/3967.latencies.intra --weights=../data/raw/rocketfuel/3967/3967.weights.intra --output=../data/interim/topologies/rf_3967_exodus.annotated.txt --graphviz=../data/interim/topologies/rf_3967_exodus.dot"
	cd ns-3 && ./waf --run "hiroute-convert-rocketfuel --latency=../data/raw/rocketfuel/1239/1239.latencies.intra --weights=../data/raw/rocketfuel/1239/1239.weights.intra --output=../data/interim/topologies/rf_1239_sprint.annotated.txt --graphviz=../data/interim/topologies/rf_1239_sprint.dot"

topology-map:
	python3 scripts/build_dataset/build_topology_mapping.py --topology-config $(TOPOLOGY)

dataset:
	python3 scripts/build_dataset/build_all.py --config configs/datasets/smartcity_v1.yaml --topology-config $(TOPOLOGY)

validate-dataset:
	python3 scripts/build_dataset/validate_dataset.py --topology-config $(TOPOLOGY)

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
