# Metric Semantics Reference

Last updated: 2026-04-26 (strict/loose relevance split implemented)

## TL;DR for paper-facing readers (read this first)

- `mean_success_at_1` (and the bare column `success_at_1`) is **terminal strong success after sequential manifest fallback completes**. It is **NOT** first-returned-object top-1 success. Paper text should use `terminal_strong_success_rate` (or the prose "terminal strong success") and never call this metric "top-1" or "first-object".
- The actual first-choice quality metric is `first_fetch_relevant` / `first_fetch_strong_relevant_rate`. Paper-facing prose should be "first-fetch strong correctness".
- `manifest_rescue_rate` is the legacy alias for `within_reply_manifest_rescue_rate`. The split into `within_reply_*` and `cross_probe_*` is the supported way to talk about rescue.
- `wrong_object_rate` is terminal-state failure (no qrel-2 object after all fallback). It is NOT "first object was wrong but later rescued."
- On the current `object_main` workload, `hiroute` failures are 100% `predicate_miss`; `wrong_object` and `wrong_domain` columns are zero. This means the manifest sweep is dominated by the predicate filter stage, so neither manifest size nor controller-side cosine has a chance to act inside admissible domains. Do not present `mean_success_at_1` movement across `manifest{1,2,3}` as evidence of object-stage ranking quality.
- **Manifest-sweep monotonicity is an aggregate property, not a per-query property.** On `object_main` and `ablation`, the discovery engine's scoring interacts with manifest size, so individual queries can succeed at manifest size 1 and fail at manifest size 3 (and vice versa) while the per-scheme mean `success_at_1` still rises monotonically across the sweep. The paper claim on these experiments is the aggregate gain, not per-query stability. `tools/validate_manifest_regression.py --allow-success-regression-with-aggregate-gain` (passed by `tools/run_mainline_review_stage.py` for these two experiments) demotes per-query regressions to warnings while keeping aggregate-mean regression as a hard error. The current diagnostic snapshot records 200+ per-query regressions for `hiroute` between manifest 1 and manifest 3; the aggregate mean over those same queries rises from 0.142 to 0.592.

## Phase 2 semantics

The runtime now records strict and loose relevance separately. Paper-facing success
should use strict relevance unless explicitly labeled as a loose diagnostic.

### Strict relevance at 3 call sites

`ns-3/src/ndnSIM/apps/hiroute-ingress-app.cpp:handleFetchReply()` computes a qrel
grade through `objectRelevanceGrade(queryId, objectId)`. Grade `>= 2` is strict
relevance; grade `> 0` is loose relevance. The strict boolean drives three decisions:

1. `firstFetchRelevant` recording at line 1049 — first-fetch quality metric tightens.
2. Manifest fallback decision at line 1057-1063 — sequential fallback now continues past
   any grade-1 (loosely relevant) match and only stops at a grade-2 match.
3. Terminal `finishActiveQuery(relevant, …)` at line 1072 — `success_at_1` tightens to
   "strongly relevant fetch," not "any-grade fetch."

The same query log also records diagnostic loose metrics:

- `terminal_loose_success` — whether any fetched object would have satisfied the older
  loose qrel semantics during the terminal query attempt path.
- `first_fetch_loose_relevant` — whether the first fetched object had qrel grade `> 0`.
- `final_object_relevance_grade` — qrel grade of the final object passed to
  `finishActiveQuery`, or `0` when no final object is recorded.

The rerun must complete under a clean git tree before any refreshed numbers can be
promoted to paper-facing text.

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

### C++ log columns

`cumulative_manifest_fetches` counts manifest-entry advances across all probes of a
single query. Unlike `manifest_fetch_index`, this counter is **not reset** on new
discovery replies, so cross-probe rescue is observable. The strict/loose diagnostic
columns above are emitted in the same query log and normalized by `run_experiment.py`.

### aggregate_query_metrics.py manifest_rescue_rate status

A prior revision of `aggregate_query_metrics.py` is documented in the Phase 1 section
below (line describing `(manifest_hit_at_5 == 1) & (success_at_1 == 0)`) as having an
inverted definition. That earlier bug is **no longer present**: the current
`aggregate_query_metrics.py:92` defines
`manifest_rescue = (success_at_1 == 1) & (manifest_fetch_index > 0)`, which matches
`build_object_main_manifest_sweep.py:69` and `build_ablation_summary.py:73`. The Phase 1
annotation is retained below for historical record.

The aggregate builders emit strict/loose rates:
`terminal_strong_success_rate`, `terminal_loose_success_rate`,
`first_fetch_strong_relevant_rate`, and `first_fetch_loose_relevant_rate`. The legacy
`manifest_rescue_rate` is retained as an alias of `within_reply_manifest_rescue_rate`
during the deprecation window.

---

## Query-level metrics (from C++ ingress query_log.csv)

### success_at_1

| Property | Value |
|----------|-------|
| C++ origin | `hiroute-ingress-app.cpp:finishActiveQuery()` |
| True semantics | **Terminal strict end-to-end success** after all manifest fallback and probe replanning |
| Paper name | Terminal strong success |
| Paper definition | Must be described as terminal success, not first-object top-1 success |
| **Semantic gap** | Historical `success_at_1` name is overloaded; use `terminal_strong_success_rate` in paper-facing aggregates |
| Values | 0 or 1 per query |
| Notes | If manifest position 0 fails but position 2 succeeds via fallback, this records 1. To measure actual first-choice quality, use `first_fetch_relevant` instead. |

### first_fetch_relevant (NEW — added 2026-04-15)

| Property | Value |
|----------|-------|
| C++ origin | `hiroute-ingress-app.cpp:handleFetchReply()` |
| True semantics | Whether the **very first fetched object** (before any manifest fallback) had qrel grade `>= 2` |
| Values | 0, 1, or empty (if no fetch was ever attempted, e.g. predicate_miss) |
| Notes | Recorded on the first `handleFetchReply` call per query. Use `first_fetch_loose_relevant` for the grade `> 0` diagnostic. |

### terminal_loose_success / first_fetch_loose_relevant

| Property | Value |
|----------|-------|
| C++ origin | `hiroute-ingress-app.cpp:handleFetchReply()` and `finishActiveQuery()` |
| True semantics | Loose qrel grade `> 0` diagnostic; not the paper-facing strict success metric |
| Values | 0 or 1 |
| Notes | These fields explain how much apparent success came from older loose relevance semantics. They must not replace strict success unless the paper explicitly downscopes the claim. |

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
| Notes | This is a terminal failure state, not "the first returned object was wrong but later rescued." Use `first_fetch_strong_relevant_rate` and the rescue split to analyze first-choice object quality. |

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
| True semantics | Terminal strong success conditioned on the final domain being strongly relevant |
| **Semantic gap** | Despite the historical name, this is not a first-object or best-object ranking metric; it still inherits terminal fallback semantics from `success_at_1`. |

### manifest_rescue_rate

| Property | Value |
|----------|-------|
| Script | `aggregate_query_metrics.py`, `build_object_main_manifest_sweep.py`, `build_ablation_summary.py` |
| True semantics | Legacy alias for `within_reply_manifest_rescue_rate`: `(success_at_1 == 1) & (manifest_fetch_index > 0)` |
| Notes | A prior Phase 1 revision used the opposite definition, `(manifest_hit_at_5 == 1) & (success_at_1 == 0)`. Current paper-facing analysis should use the split rescue columns. |

## CLAUDE.md instrumentation contract status

| Required metric | Status |
|----------------|--------|
| `first_probe_relevant_domain_hit` | Implemented in the raw query log and promoted into object/ablation aggregates |
| `first_probe_domain_rank` | Implemented in the raw query log and promoted into object/ablation aggregates |
| `first_manifest_top1_correct` | **NOW AVAILABLE** as `first_fetch_relevant` |
| `manifest_rescue_rank` | **NOW DERIVABLE** as `manifest_fetch_index`/`mean_manifest_rescue_rank_success_only` when `success_at_1 == 1` |
| `final_end_to_end_success` | Already exists as `success_at_1` (terminal) |
| `failure_stage` | Implemented in the raw query log and aggregated into domain-selection/local-resolution/fetch rates |
| `num_relevant_domains` | Implemented in the raw query log and promoted into object/ablation aggregates |
| `num_confuser_domains` | Implemented in the raw query log and promoted into object/ablation aggregates |
| `num_confuser_objects` | Implemented in the raw query log and promoted into object/ablation aggregates |
