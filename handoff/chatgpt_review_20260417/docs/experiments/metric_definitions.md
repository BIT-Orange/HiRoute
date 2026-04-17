# Metric Definitions

## Mainline headline metrics

- `success_at_1`: end-to-end terminal success after any enabled sequential manifest fallback completes. It is not a first-fetch-only metric.
- `first_fetch_relevant`: whether the first fetched object was relevant before any manifest rescue.
- `manifest_fetch_index`: zero-based index of the manifest entry that eventually succeeded; values `> 0` indicate a manifest rescue.
- `manifest_hit_at_5`: compatibility column name for manifest-hit-at-`r`; the runtime checks up to the requested manifest size rather than a literal top-5.
- `ndcg_at_5`: ranking quality over object-level qrels for the returned manifest.
- `num_remote_probes`: number of cross-domain controller probes issued for a query.
- `discovery_bytes`: discovery-plane bytes exchanged for a query.
- `latency_ms`: end-to-end query completion time in milliseconds.
- `relevant_domain_reached_at_1`: whether the first probed domain is relevant under `qrels_domain`.
- `relevant_domain_reached_at_k`: whether any probed domain is relevant under `qrels_domain`.
- `manifest_rescue_rate`: derived metric `(manifest_fetch_index > 0) & (success_at_1 == 1)`.

## Failure taxonomy

The active code path emits exactly these `failure_type` labels:

- `predicate_miss`: no admissible probe plan was constructed from the query predicates.
- `wrong_domain`: the probed domain/controller path did not return a relevant manifest.
- `wrong_object`: a relevant domain was reached, but the fetched object was not relevant.
- `no_reply`: discovery failed because the selected controller did not reply before timeout.
- `fetch_timeout`: object fetch failed after discovery because the fetch phase timed out.

`failure_breakdown.csv` is a diagnostic aggregate. It may also include synthetic `success` rows during postprocessing so that rates sum to one.
