# Decision Log

Updated: 2026-04-15 (PHASE 1 diagnostic)

## D0: Phase 0 gate — PASSED
**Date**: 2026-04-15  
**Decision**: Phase 0 audit complete.  
**Basis**: See state_model.md.

## D1.1: routing_main zeros — root cause identified
**Date**: 2026-04-15  
**Finding**: Committed `matchesBitmap` is buggy — treats entire `;`-delimited constraint as one key. Fix exists in dirty tree but is uncommitted.  
**Required action**: Commit the fix, rebuild, rerun routing_main.  
**Impact**: Unblocks Figures 4, 6, 7 (routing support, candidate shrinkage, deadline summary).

## D1.2: flat_iroute = inf_tag_forwarding — root cause identified
**Date**: 2026-04-15  
**Finding**: `extraTagWeight` boost is applied uniformly because all level-0 summaries have identical exhaustive tag bitmaps. Adding the same constant to all scores doesn't change ranking.  
**Required action**: Either (a) make tag bitmaps domain-selective, (b) drop inf_tag_forwarding as a separate baseline, or (c) redesign the tag-based scoring.  
**Recommendation**: Drop inf_tag_forwarding and note it as aliased to flat_iroute. Fixing the dataset is workload-redesign scope (PHASE 3). Option (b) is cheapest and most honest.

## Pending decisions

### D2: Route A vs Route B [PHASE 2]
Preliminary assessment: Route B. Formal decision after PHASE 1 metric repair.

### D3: object_main workload design [PHASE 3]
Deferred.

### D4: inf_tag_forwarding treatment
Options documented in D1.2. Decision should be made together with workload redesign.
