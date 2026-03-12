# Metric Definitions

## Primary metrics

- `success_at_1`: fraction of queries whose top returned object matches the object-level qrels.
- `manifest_hit_at_5`: fraction of queries whose relevant object appears in the top-5 manifest.
- `ndcg_at_5`: ranking quality over object-level qrels for the returned manifest.
- `num_remote_probes`: count of cross-domain probes used to satisfy a query.
- `discovery_bytes`: total bytes exchanged in the discovery plane for a query.
- `latency_ms`: end-to-end query completion time in milliseconds.

## Failure accounting

- `wrong_domain_failure`: no selected domain contains a relevant object.
- `wrong_object_failure`: selected domain is relevant but returned object is not relevant.
- `budget_exhausted`: refinement or probe budget ends before a valid resolution.
- `stale_summary_failure`: discovery decision was invalidated by stale summary state.
