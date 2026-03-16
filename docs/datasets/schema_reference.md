# Schema Reference

## `data/processed/ndnsim/objects_master.csv`

- `object_id`
- `domain_id`
- `zone_id`
- `zone_type`
- `service_class`
- `semantic_facet`
- `freshness_class`
- `time_bucket`
- `vendor_template_id`
- `canonical_name`
- `producer_node_id`
- `controller_node_id`
- `payload_size_bytes`
- `unit`
- `value_type`
- `object_version`
- `object_text_id`

## `data/processed/ndnsim/queries_master.csv`

- `query_id`
- `split`
- `ingress_node_id`
- `start_time_ms`
- `query_text`
- `zone_constraint`
- `zone_type_constraint`
- `service_constraint`
- `freshness_constraint`
- `ambiguity_level`
- `difficulty`
- `intended_domain_count`
- `ground_truth_count`
- `query_family`
- `workload_tier`
- `intent_facet`
- `query_text_id`

## `data/processed/ndnsim/object_embedding_index.csv`

- `object_id`
- `object_text_id`
- `embedding_row`

## `data/processed/ndnsim/query_embedding_index.csv`

- `query_id`
- `query_text_id`
- `embedding_row`

## `data/processed/ndnsim/summary_embedding_index.csv`

- `centroid_row`
- `domain_id`
- `level`
- `cell_id`

## `data/processed/eval/qrels_object.csv`

- `query_id`
- `object_id`
- `domain_id`
- `relevance`

## `data/processed/eval/qrels_domain.csv`

- `query_id`
- `domain_id`
- `is_relevant_domain`

## `data/processed/ndnsim/hslsa_export.csv`

- `domain_id`
- `level`
- `cell_id`
- `parent_id`
- `zone_bitmap`
- `zone_type_bitmap`
- `service_bitmap`
- `freshness_bitmap`
- `semantic_tag_bitmap`
- `centroid_row`
- `radius`
- `object_count`
- `controller_prefix`
- `version`
- `ttl_ms`
- `export_budget`

## `data/processed/ndnsim/topology_mapping_<topology_id>.csv`

- `node_id`
- `role`
- `domain_id`
- `zone_id`
- `controller_prefix`
- `producer_count`

## `data/processed/ndnsim/controller_local_index.csv`

- `domain_id`
- `cell_id`
- `object_id`
- `local_rank_hint`

## `data/processed/ndnsim/cell_membership.csv`

- `object_id`
- `domain_id`
- `level0_cell`
- `level1_cell`
- `level2_cell`
