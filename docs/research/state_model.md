# Project State Model

Generated: 2026-04-15 (PHASE 0 audit synthesis)

## 1. What the paper claims the system is

HiRoute is presented as a **hierarchical semantic name-resolution architecture** for NDN-IoT that:
- Separates hard constraints (predicates) from soft semantics (vector similarity)
- Uses cosine similarity Sim(v_q, μ_c) between query vectors and cell centroids (Eq. 2)
- Performs bounded hierarchical refinement over summary trees
- Returns ranked manifests from domain controllers for sequential fallback
- Bounds exported inter-domain state by a summary budget
- Is evaluated on: service success, discovery overhead, candidate shrinkage, deadline latency, state scaling, and robustness

## 2. What the runtime actually implements

The ndnSIM code implements a **predicate-gated hierarchical discovery system with heuristic tag/hint scoring**:

### Genuinely implemented (4 mechanisms)
- **Predicate elimination**: Hard gate before scoring. `MatchesPredicate()` filters entries by zone/service/freshness constraints before any scoring occurs.
- **Hierarchical refinement**: 3-level parent→child traversal in `buildProbePlan()`. Level-0 entries are ranked, winners expanded to level-1 children, re-ranked, expanded again.
- **Manifest fallback**: Sequential manifest traversal in `handleFetchReply()`. If the first manifest entry is irrelevant, subsequent entries are tried in order.
- **Reliability-aware suppression**: EWMA-based reliability scores + TTL-based negative cache. Functional for hiroute/full_hiroute modes.

### Approximate (2 mechanisms)
- **Covering radii**: Used as a minor tiebreaker (0.2/(1+r)) in `computeSemanticScore`, not for geometric distance/pruning.
- **Manifest generation**: Controller builds ranked manifests, but ranking uses heuristic string-match scoring (`semanticFacetScore` = exact intentFacet match), not embedding similarity.

### Unsupported (2 mechanisms)
- **Cosine similarity scoring**: `computeSemanticScore()` uses frontier hint matching (0.45), intent facet tag bitmap (0.45), radius inverse (0.2). No vector operations, no dot products, no cosine similarity. `residualVector` field exists in the request struct but is never read.
- **Semantic centroids**: `centroidRow` in HiRouteSummaryEntry is an integer row index, never dereferenced to a vector. No centroid vector storage or computation exists.

## 3. What the metrics actually measure

| Metric name | Paper says | Code actually measures | Gap |
|------------|-----------|----------------------|-----|
| `success_at_1` | "first fetched object satisfies query" | Terminal success after all manifest fallback + probe retry | OVERSTATED — not first-choice |
| `wrong_object_rate` | Object-level ranking quality | Terminal failure: all retries exhausted, wrong object | UNDERSTATED — hides rescued failures |
| `manifest_hit_at_5` | Manifest contains relevant object (top-5) | Manifest contains relevant object (up to requestedManifestSize, not 5) | MISLABELED |
| `best_object_chosen_given_relevant_domain` | Object selection quality conditional on reaching right domain | Terminal success conditional on final domain relevance | VACUOUS — always 1.0 |
| `discovery_bytes` | Discovery traffic | TX-side Interest parameter bytes only | UNDERSTATED |
| `wrong_domain` | Domain selection failure | Probes exhausted without getting any manifest entries | EXACT |
| `probe_count` | Remote probes issued | Count of sendDiscoveryProbe() calls | EXACT |
| `latency_ms` | End-to-end completion time | Simulation time from dispatch to finishActiveQuery | EXACT |

### Missing metrics (from CLAUDE.md instrumentation contract — none implemented)
- `first_probe_relevant_domain_hit`
- `first_probe_domain_rank`
- `first_manifest_top1_correct`
- `manifest_rescue_rank`
- `failure_stage` (domain_selection vs local_resolution vs fetch)
- `num_relevant_domains`, `num_confuser_domains`, `num_confuser_objects`

## 4. Does object_main isolate the mechanism it claims to test?

**No.** object_main is framed as a manifest/object-resolution experiment, but:
- `wrong_object_rate = 0.0` universally — there is no object-level resolution problem
- All baseline failures are `wrong_domain` (9.2%) — domain selection, not object ranking
- Manifest sizes 1/2/3 produce identical metrics — manifest fallback never triggers
- `best_object_chosen_given_relevant_domain = 1.0` for all schemes — trivially perfect
- The workload has zero intra-domain object ambiguity

**What it actually tests**: Whether the scheme's hierarchical/predicate/facet scoring reaches the correct domain. HiRoute achieves 100% (vs 90.8% for baselines), demonstrating domain-selection superiority, not object-resolution superiority.

## 5. What can be retained vs downgraded

### Retainable as primary evidence
- **Ablation mechanism ordering** (with caveats): full_hiroute (1.0) > predicates_plus_flat (0.908) > predicates_only (0.842) > flat_semantic_only (0.575). This genuinely shows that predicate filtering + hierarchy helps domain selection. Must be framed as domain-selection evidence, not object-resolution evidence.

### Must be downgraded to diagnostic/support
- **object_main manifest sweep**: Shows scheme comparison but NOT manifest effect. Can show domain-selection superiority (hiroute vs baselines) but cannot claim manifest benefit.
- **failure_breakdown**: Useful diagnostic showing wrong_domain dominance, not a paper-facing result.

### Must be discarded or rebuilt
- **routing_support.csv**: All zeros for distributed schemes. Catastrophically broken. Cannot be used.
- **candidate_shrinkage.csv**: All zeros for distributed schemes. Cannot be used.
- **deadline_summary.csv**: All zeros for distributed schemes. Cannot be used.
- **state_scaling**: No data exists.
- **robustness**: No data exists.

## 6. Top 10 most dangerous paper-facing mismatches (ranked)

1. **routing_main completely broken** — 3 figures bound to vacuous data
2. **Eq. 2 cosine similarity unsupported** — signature equation has no code backing
3. **Manifest sweep metric-invariant** — core object_main contribution has zero signal
4. **zero wrong_object universally** — cannot claim object-resolution benefit
5. **success_at_1 misnamed** — paper says "first fetched" but code measures terminal
6. **best_object_given_domain vacuous** — always 1.0, no discrimination
7. **flat_iroute = inf_tag_forwarding** — two "distinct" baselines are identical
8. **state_scaling + robustness = no data** — 2 paper figures are placeholders
9. **candidate_shrinkage = no data** — progressive filtering narrative has no evidence
10. **single seed, single topology** — no variance, no generalizability claim

## 7. Route A vs Route B preliminary assessment

**Strong recommendation: Route B (narrow the paper claim).**

Rationale:
- Route A (implement vector scoring) requires: storing dense centroid vectors in HiRouteSummaryEntry, loading query embeddings at runtime, implementing cosine similarity in computeSemanticScore, doing the same in controller evaluateCandidates, then regenerating ALL experiment data. This is 2-4 weeks of implementation + re-experimentation.
- Route B (narrow to match implementation) requires: rewriting ~15-20 paper paragraphs to describe the actual heuristic mechanism, removing/reframing Eq. 2, adjusting Table I. The hierarchical refinement, predicate filtering, manifest fallback, and reliability cache are genuinely implemented and form a coherent contribution.
- The system as implemented already demonstrates a meaningful result: predicate-gated hierarchical discovery with heuristic scoring outperforms flat approaches for domain selection. This is a publishable contribution — it just isn't the cosine-similarity-driven contribution the paper currently claims.

**This is a preliminary assessment. Formal Route A/B decision is PHASE 2.**
