# Dataset Design

The formal dataset target is `smartcity_v1`. It combines Smart Data Models metadata, a synthetic
object/query generator, offline text embeddings, constrained hierarchy export, and Rocketfuel-based
topology mappings for ndnSIM scenarios.

Official embeddings are generated with `sentence-transformers/all-MiniLM-L6-v2`. The workflow pins
its Hugging Face cache inside `data/interim/cache/huggingface/` so dataset builds remain writable
inside the project workspace.

## End-to-end pipeline

1. `make download-smartdatamodels`
2. `make extract-sdm-subjects`
3. `make build-service-ontology`
4. `make convert-topologies`
5. `make dataset TOPOLOGY=configs/topologies/rocketfuel_3967_exodus.yaml`
6. `make validate-dataset TOPOLOGY=configs/topologies/rocketfuel_3967_exodus.yaml`

## Managed configs

- `configs/datasets/smartcity_v1.yaml`: dataset manifest and output contract
- `configs/datasets/service_ontology_rules.yaml`: editable subject-to-service mapping
- `configs/datasets/smartcity_object_generation.yaml`: object generation rules
- `configs/datasets/smartcity_query_generation.yaml`: query generation rules
- `configs/hierarchy/hiroute_hkm_v1.yaml`: hierarchy export settings

The canonical tracked registry for dataset versions lives in `data/registry/`.
