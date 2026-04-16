# Open Problems

Generated: 2026-04-15 (PHASE 0 audit)

## P1: routing_main is catastrophically broken [CRITICAL]

**Symptom**: `routing_support.csv` shows 0.0 for ALL metrics (success, probes, bytes, latency) for every distributed scheme. Only `central_directory` produces any data.

**Implication**: Figures 4, 6, 7 (routing support, candidate shrinkage, deadline summary) are all bound to vacuous data. Three paper figures have no content.

**Possible causes** (to investigate in PHASE 1):
- routing_main uses `workload_tier: routing_main` — different from object_main's `workload_tier: object_main`. The routing tier queries may fail predicate matching for all distributed schemes.
- The `budget` parameter (8/16/32) in routing_main may interact differently with the scheme configurations.
- The `manifest_size: 5` default in routing_main (vs 1 in object_main) may cause different behavior.

**Action**: Must diagnose root cause before routing figures can be included. If unfixable in time, downgrade to appendix/future work.

## P2: Manifest sweep is metric-invariant [CRITICAL]

**Symptom**: Changing manifest_size from 1 to 3 produces byte-identical results for every scheme.

**Root cause analysis**:
- manifest_size IS passed to ndnSIM (confirmed in runner code and scenario wiring)
- Controller DOES build manifests of the requested size
- Ingress DOES implement sequential manifest fallback (lines 970-974, 1053-1057)
- BUT: wrong_object_rate = 0.0 means the first manifest entry is always correct
- Therefore: the fallback path never triggers because it's never needed
- The workload has zero intra-domain object ambiguity

**Action**: Redesign workload to introduce object ambiguity (PHASE 3). Until then, paper cannot claim manifest benefit.

## P3: Paper describes vector scoring; code implements heuristic scoring [CRITICAL]

**Symptom**: Equation 2 defines Sim(v_q, μ_c) as cosine similarity. `computeSemanticScore` uses tag bitmap matching and frontier hint scoring. No vector math exists in the codebase.

**Details**:
- `residualVector` field in HiRouteDiscoveryRequest exists but is never read
- `centroidRow` field in HiRouteSummaryEntry is loaded but never dereferenced
- `computeSemanticScore` scoring: frontier hint match (0.45/0.35/0.2), intent facet tag match (0.45), radius inverse (0.2)

**Action**: Route A/B decision in PHASE 2. Recommendation: Route B (narrow paper).

## P4: success_at_1 is misnamed [HIGH]

**Symptom**: The paper defines ServiceSuccess@1 as "whether the first fetched object satisfies the query." The C++ code logs this as terminal success after all manifest fallback and probe retry.

**Details**: `finishActiveQuery(bool success, ...)` is called only after exhausting manifest entries and probe fallbacks. If manifest position 0 fails but position 1 succeeds, success=1 is still recorded. The metric is "final end-to-end success," not "first-choice correctness."

**Action**: Rename to `final_success` or qualify the paper definition. Need a new metric for actual first-choice quality.

## P5: wrong_object is terminal, not first-choice [HIGH]

**Symptom**: `wrong_object_rate = 0.0` universally. The paper expects this to reflect first-object ranking quality.

**Details**: The C++ code sets `failure_type = "wrong_object"` only at line 1082 (terminal state) or when `advanceToNextProbe("wrong_object")` exhausts all options. It is never set for an intermediate failed manifest entry that is later rescued.

**Action**: Must instrument first-choice tracking (was the first manifest entry correct?) separately from terminal outcome.

## P6: flat_iroute and inf_tag_forwarding produce identical results [MEDIUM]

**Symptom**: Both schemes show byte-identical metrics (success=0.908333, wrong_domain=22/240, bytes=505.4125, probes=3.220833) across all manifest sizes in object_main.

**Possible causes**:
- They may share the same code path with different names
- The workload may not stress the difference between them
- Instrumentation may collapse distinct behaviors

**Action**: Check baseline config files and code paths for these two schemes.

## P7: State-scaling and robustness experiments do not exist [MEDIUM]

**Symptom**: No mainline data for `state_scaling` or `robustness`. Paper reserves Figures 8 and 9 for them.

**Action**: Run these experiments after mainline is fixed, or downscope to future work.

## P8: Single seed, single topology [MEDIUM]

**Symptom**: All experiments use seed=1 only, topology=rf_3967_exodus_compact only.

**Action**: Add at least one additional seed. Consider a second topology for appendix. Without variance, no statistical claims can be made.

## P9: Claim note C-002 contradicts sealed data [LOW]

**Symptom**: C-002 says "the diagnostic failure mix that motivated the rerun was dominated by wrong_object." Sealed data shows zero wrong_object.

**Action**: Update the note to match reality, or flag it as historical context only.
