# Blockers and Risks

Updated: 2026-04-15 (after PHASE 1 P1.1/P1.2 diagnostic)

## Critical blockers

### B1: routing_main predicate matching bug — ROOT CAUSE FOUND, FIX EXISTS
- **Status**: Fix exists as uncommitted change in dirty tree
- **Fix**: Commit `matchesBitmap` split-on-semicolon fix in `hiroute-summary-entry.cpp`, rebuild binary, rerun routing_main
- **Blocks**: Figures 4, 6, 7
- **Risk**: Rerun may still show problems — the fix is necessary but may not be sufficient if the routing_main workload has other issues

### B2: Paper Eq. 2 describes vector scoring that doesn't exist — UNCHANGED
- **Resolution**: Route B decision (PHASE 2)

### B3: Manifest sweep metric-invariant — UNCHANGED
- **Resolution**: Workload redesign (PHASE 3)

### B4: success_at_1 misnamed — UNCHANGED
- **Resolution**: Metric instrumentation (PHASE 1 next steps)

## Resolved blockers

### B1-diagnostic: routing_main zeros
- **Resolved**: Root cause is `matchesBitmap` bug treating multi-token constraints as single key
- **Status**: Diagnosis complete; fix implementation pending

### B1.2-diagnostic: flat_iroute = inf_tag_forwarding
- **Resolved**: Root cause is uniform tag bitmaps making extraTagWeight a no-op
- **Status**: Must decide treatment in PHASE 3 or drop as aliased baseline

## High risks — UNCHANGED

- R1: flat_iroute = inf_tag_forwarding (root cause known, fix deferred)
- R2: Single seed (must add variance in PHASE 4)
- R3: Instrumentation contract unimplemented (PHASE 1 next steps)
