# Todo Audit 2026-03-13

This audit cross-checks `Todo.md` and `paper/main.tex` against the current HiRoute implementation.

## Resolved In This Batch

- Robustness injection now targets the dominant query domain instead of the first controller or the first topology link.
- Link-failure mode now disables controller-adjacent links for the selected target domain, which is materially closer to the paper's intended physical-failure stress.
- Staleness mode now records and targets the same dominant domain so Figure 9 reflects a deliberate semantic-drift stress point.

## Still Misaligned With `paper/main.tex`

### 1. Hierarchy default is still too fine

- Current `configs/hierarchy/hiroute_hkm_v1.yaml` partitions level-1 cells by `zone_id + service_class + freshness_class`.
- The paper's default design specifies coarse predicate cells based on `zone + service class`, with freshness kept in the predicate sketch rather than the partition key.
- Impact: many current level-2 microclusters collapse into singleton cells, which weakens the causal story for hierarchical refinement and local manifest ranking.

### 2. Semantic microclusters are still too shallow

- The current hierarchy export often produces one object per level-2 cell.
- The paper expects balanced semantic microclusters within each predicate cell.
- Impact: controller-side local ranking is less meaningful than intended, and candidate-shrinkage behavior is harder to interpret.

### 3. Figure 8 is only partially aligned

- Current `exp_scaling_v1` compares `rf_3967_exodus` and `rf_1239_sprint`.
- The paper's state-scaling design also expects sweeps over object count per domain and domain count under a bounded export budget.
- Impact: the current scaling figure validates topology growth, but not the full "state tracks budget rather than object population" claim.

### 4. Candidate shrinkage remains under-instrumented

- Current Figure 6 mostly reflects predicate-screening shrinkage.
- The paper's intended interpretation also needs frontier contraction after hierarchical refinement.
- Impact: the figure does not yet fully separate "predicate elimination" from "semantic refinement" benefits.

## Next Implementation Priority

1. Rebuild the hierarchy so level-1 uses `zone + service` and level-2 forms non-trivial balanced microclusters.
2. Regenerate dataset artifacts and rerun the official experiment matrix from a clean commit.
3. Extend state-scaling experiments to sweep object count and domain count under fixed export budgets.
4. Extend candidate-shrinkage logging to capture pre-filter, post-filter, post-refinement, and post-manifest stages explicitly.
