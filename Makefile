PYTHON ?= .venv/bin/python3
PIP ?= .venv/bin/pip
EXP ?= configs/experiments/exp_routing_main_v2.yaml
SCHEME ?= hiroute
SEED ?= 1
MODE ?= official
TOPOLOGY ?= configs/topologies/rocketfuel_3967_exodus.yaml
TOPOLOGY_ID ?=
VARIANT ?=
BUDGET ?=

.PHONY: venv download-smartdatamodels extract-sdm-subjects build-service-ontology embed-texts download-rocketfuel convert-topologies topology-map dataset validate-dataset run aggregate promote figures paper-check

venv:
	python3 -m venv .venv
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt

download-smartdatamodels:
	bash scripts/download/download_smartdatamodels.sh

extract-sdm-subjects:
	$(PYTHON) scripts/preprocess/extract_sdm_subjects.py

build-service-ontology:
	$(PYTHON) scripts/preprocess/build_service_ontology.py

download-rocketfuel:
	bash scripts/download/download_rocketfuel.sh

convert-topologies:
	mkdir -p data/interim/topologies
	cd ns-3 && ./waf --run "hiroute-convert-rocketfuel --latency=../data/raw/rocketfuel/3967/3967.latencies.intra --weights=../data/raw/rocketfuel/3967/3967.weights.intra --output=../data/interim/topologies/rf_3967_exodus.annotated.txt --graphviz=../data/interim/topologies/rf_3967_exodus.dot"
	cd ns-3 && ./waf --run "hiroute-convert-rocketfuel --latency=../data/raw/rocketfuel/1239/1239.latencies.intra --weights=../data/raw/rocketfuel/1239/1239.weights.intra --output=../data/interim/topologies/rf_1239_sprint.annotated.txt --graphviz=../data/interim/topologies/rf_1239_sprint.dot"

topology-map:
	$(PYTHON) scripts/build_dataset/build_topology_mapping.py --topology-config $(TOPOLOGY)

embed-texts:
	$(PYTHON) scripts/build_dataset/embed_texts.py --config configs/datasets/smartcity_v2.yaml

dataset:
	$(PYTHON) scripts/build_dataset/build_all.py --config configs/datasets/smartcity_v2.yaml --topology-config $(TOPOLOGY)

validate-dataset:
	$(PYTHON) scripts/build_dataset/validate_dataset.py --topology-config $(TOPOLOGY)

run:
	$(PYTHON) scripts/run/run_experiment.py --experiment $(EXP) --scheme $(SCHEME) --seed $(SEED) --mode $(MODE) $(if $(TOPOLOGY_ID),--topology-id $(TOPOLOGY_ID),) $(if $(VARIANT),--variant $(VARIANT),) $(if $(BUDGET),--budget $(BUDGET),)

aggregate:
	$(PYTHON) scripts/eval/aggregate_experiment.py --experiment $(EXP)

promote:
	$(PYTHON) scripts/eval/promote_runs.py --experiment $(EXP)

figures:
	$(PYTHON) scripts/plots/plot_experiment.py --experiment $(EXP)

paper-check:
	$(PYTHON) tools/validate_figures.py --experiment $(EXP) --aggregate results/aggregate/main_success_overhead.csv --figure-note paper/notes/fig_main_success_overhead.md
