# Metric Semantics Reference

Last updated: 2026-04-19 (PHASE 2 scheduled; PHASE 1 baseline preserved below)

## Phase 2 semantics (2026-04-19, pending rerun)

The following semantics are **scheduled** and take effect only after the next full rerun
(`tools/run_mainline_review_stage.sh full_mainline --max-workers 1` plus downstream
aggregation). Until rerun lands, Phase 1 semantics below remain authoritative for all
sealed aggregates in `results/aggregate/mainline/`.

### Strict relevance at 3 call sites

`ns-3/src/ndnSIM/apps/hiroute-ingress-app.cpp:1047` computes `relevant` via
`isStrongRelevantObject(queryId, objectId)` (grade `>= 2` qrel). Because that boolean
then drives three distinct decisions:

1. `firstFetchRelevant` recording at line 1049 — first-fetch quality metric tightens.
2. Manifest fallback decision at line 1057-1063 — sequential fallback now continues past
   any grade-1 (loosely relevant) match and only stops at a grade-2 match.
3. Terminal `finishActiveQuery(relevant, …)` at line 1072 — `success_at_1` tightens to
   "strongly relevant fetch," not "any-grade fetch."

Expected aggregate impact (pending rerun confirmation):

- `hiroute` `success_at_1` currently `1.0` on the compact `object_main` workload is
  expected to drop to roughly the `0.6–0.8` band because some queries whose terminal
  fetch is grade-1 (loosely relevant) but not grade-2 will now be counted as
  `wrong_object`.
- `first_fetch_relevant_rate` for `hiroute` currently `0.620833` will move, likely
  downward.
- `central_directory` is expected to stay near `1.0` since its oracle ranking surfaces
  the highest-graded qrel first.

The rerun must complete under a clean git tree per CLAUDE.md before any of these numbers
can be promoted to paper-facing text.

### New derived rescue metrics

The next aggregate rebuild introduces two derived rate metrics that together replace the
current ambiguous `manifest_rescue_rate`:

- `within_reply_manifest_rescue_rate` — `(success_at_1 == 1) & (manifest_fetch_index > 0)`.
  Measures rescue that happens by advancing through the current discovery reply's manifest
  without issuing a new probe. This is the semantic the Python scripts
  (`build_object_main_manifest_sweep.py:69`, `build_ablation_summary.py:73`) intended all
  along.
- `cross_probe_manifest_rescue_rate` —
  `(success_at_1 == 1) & (cumulative_manifest_fetches > 0) & (manifest_fetch_index == 0)`.
  Measures rescue that requires a fresh probe because the previous probe's full manifest
  was exhausted. Requires the new `cumulative_manifest_fetches` column (see below).

The legacy `manifest_rescue_rate` column remains in outputs for one release cycle for
backward compatibility; consumers should migrate to the two split metrics.

### New C++ log column

`ns-3/src/ndnSIM/apps/hiroute-ingress-app.cpp` will append a new query-log column
`cumulative_manifest_fetches` that counts manifest-entry advances across all probes of a
single query. Unlike `manifest_fetch_index`, this counter is **not reset** on new
discovery replies, so cross-probe rescue becomes observable. Validation gates that
checksum the log schema must accept the new column.

### aggregate_query_metrics.py manifest_rescue_rate status

A prior revision of `aggregate_query_metrics.py` is documented in the Phase 1 section
below (line describing `(manifest_hit_at_5 == 1) & (success_at_1 == 0)`) as having an
inverted definition. That earlier bug is **no longer present**: the current
`aggregate_query_metrics.py:92` defines
`manifest_rescue = (success_at_1 == 1) & (manifest_fetch_index > 0)`, which matches
`build_object_main_manifest_sweep.py:69` and `build_ablation_summary.py:73`. The Phase 1
annotation is retained below for historical record.

In Phase 2 the three builders gain the two split metrics
(`within_reply_manifest_rescue_rate`, `cross_probe_manifest_rescue_rate`) and
legacy `manifest_rescue_rate` is retained as an alias of `within_reply_manifest_rescue_rate`
during the deprecation window.

---

## Query-level metrics (from C++ ingress query_log.csv)

### success_at_1

| Property | Value |
|----------|-------|
| C++ origin | `hiroute-ingress-app.cpp:finishActiveQuery()` |
| True semantics | **Terminal end-to-end success** after all manifest fallback and probe replanning |
| Paper name | ServiceSuccess@1 |
| Paper definition | "whether the first fetched object satisfies the query" |
| **Semantic gap** | **OVERSTATED** — paper says "first fetched" but code measures terminal outcome after all retries |
| Values | 0 or 1 per query |
| Notes | If manifest position 0 fails but position 2 succeeds via fallback, this records 1. To measure actual first-choice quality, use `first_fetch_relevant` instead. |

### first_fetch_relevant (NEW — added 2026-04-15)

| Property | Value |
|----------|-------|
| C++ origin | `hiroute-ingress-app.cpp:handleFetchReply()` |
| True semantics | Whether the **very first fetched object** (before any manifest fallback) was relevant |
| Values | 0, 1, or empty (if no fetch was ever attempted, e.g. predicate_miss) |
| Notes | Recorded on the first `handleFetchReply` call per query. Not affected by subsequent manifest fallback or probe replanning. |

### manifest_fetch_index (NEW — added 2026-04-15)

| Property | Value |
|----------|-------|
| C++ origin | `hiroute-ingress-app.cpp:finishActiveQuery()` — reads `m_activeQuery.manifestFetchIndex` |
| True semantics | 0-based position within the manifest at which the final (terminal) object was fetched |
| Values | 0 to manifest_size-1. 0 means the first manifest entry was used. |
| Notes | If `manifest_fetch_index > 0` and `success_at_1 == 1`, this indicates a manifest rescue. Derived metric: `manifest_rescue = (manifest_fetch_index > 0) & (success_at_1 == 1)`. |

### failure_type

| Property | Value |
|----------|-------|
| C++ origin | `hiroute-ingress-app.cpp` — set at multiple terminal points |
| True semantics | **Terminal** failure category after exhausting all retries |
| Values | `predicate_miss`, `wrong_domain`, `wrong_object`, `no_reply`, `fetch_timeout`, `none`/`success` |
| Taxonomy | Mutually exclusive and exhaustive for terminal state |
| **Semantic gap** | Does not distinguish first-failure-stage from terminal state. `wrong_object` means all manifest + probe retries failed, not "first object was wrong." |

### wrong_domain

| Property | Value |
|----------|-------|
| True semantics | All probed controllers returned empty manifests — no relevant domain was reached |
| C++ trigger | `sendDiscoveryProbe()` exhausts probe budget with no manifest entries, OR all discovery replies are empty |
| Notes | Dominant failure mode in current object_main (9.2% for baselines). Indicates domain-selection failure, not object-ranking failure. |

### wrong_object

| Property | Value |
|----------|-------|
| True semantics | A manifest was received and objects were fetched, but all were irrelevant. Terminal state. |
| C++ trigger | `handleFetchReply()` finds fetched object irrelevant after exhausting manifest fallback AND probe replanning |
| Current status | **0.0 for all schemes in all experiments** — the workload has zero intra-domain object ambiguity |

### manifest_hit_at_r (CSV: manifest_hit_at_5)

| Property | Value |
|----------|-------|
| C++ origin | `hiroute-ingress-app.cpp:handleDiscoveryReply()` — `m_activeQuery.manifestHit` |
| True semantics | Whether the **last probe's manifest** contained at least one relevant object |
| **Label mismatch** | CSV column says `manifest_hit_at_5` but the C++ code checks up to `requestedManifestSize` (1, 2, or 3 in object_main, not 5) |
| Notes | Only reflects the last probe's manifest (reset on probe advance). Also available as `manifest_hit_at_3` with identical values. |

### discovery_bytes

| Property | Value |
|----------|-------|
| C++ origin | `hiroute-ingress-app.cpp:sendDiscoveryProbe()` — `m_activeQuery.discoveryBytes += parameters.size()` |
| True semantics | **TX-side Interest application parameter bytes** only |
| **Semantic gap** | Does not include Interest name/header overhead, reply Data payload, or Data header/signature. Name implies total discovery traffic. |

### num_remote_probes

| Property | Value |
|----------|-------|
| C++ origin | `hiroute-ingress-app.cpp:sendDiscoveryProbe()` — incremented per probe |
| True semantics | Count of discovery probe Interests sent |
| Semantic match | EXACT |

### latency_ms

| Property | Value |
|----------|-------|
| C++ origin | `hiroute-ingress-app.cpp:finishActiveQuery()` — `Simulator::Now() - startedAt` |
| True semantics | Simulation wall-clock time from query dispatch to terminal resolution |
| Includes | All retry time (manifest fallback, probe replanning) |
| Semantic match | EXACT |

## Derived metrics (computed in Python aggregation)

### best_object_chosen_given_relevant_domain

| Property | Value |
|----------|-------|
| Script | `aggregate_query_metrics.py` |
| True semantics | `success_at_1` conditioned on final domain being relevant (NaN otherwise) |
| **Status** | VACUOUS — always 1.0 because success_at_1 is terminal (includes rescue) and wrong-domain queries are excluded |

### manifest_rescue_rate

| Property | Value |
|----------|-------|
| Script | `aggregate_query_metrics.py` line 79 |
| True semantics | `(manifest_hit_at_5 == 1) & (success_at_1 == 0)` — manifest contained relevant object BUT query still failed |
| **Semantic gap** | This is the **opposite** of manifest rescue. It measures failure despite manifest presence. True rescue would be `(manifest_fetch_index > 0) & (success_at_1 == 1)`. |

## CLAUDE.md instrumentation contract status

| Required metric | Status |
|----------------|--------|
| `first_probe_relevant_domain_hit` | NOT IMPLEMENTED |
| `first_probe_domain_rank` | NOT IMPLEMENTED |
| `first_manifest_top1_correct` | **NOW AVAILABLE** as `first_fetch_relevant` |
| `manifest_rescue_rank` | **NOW DERIVABLE** as `manifest_fetch_index` when `success_at_1 == 1` |
| `final_end_to_end_success` | Already exists as `success_at_1` (terminal) |
| `failure_stage` | NOT IMPLEMENTED (would need domain_selection vs local_resolution) |
| `num_relevant_domains` | NOT IMPLEMENTED |
| `num_confuser_domains` | NOT IMPLEMENTED |
| `num_confuser_objects` | NOT IMPLEMENTED |
