# Next Actions

Updated: 2026-04-15 (P1.1 and P1.2 diagnostic complete)

## PHASE 1 — Remaining tasks

### 1.3 Commit the matchesBitmap fix and rebuild [REQUIRED — unblocks routing]
- The fix is already in the dirty tree at `ns-3/src/ndnSIM/model/hiroute-summary-entry.cpp`
- Must commit this specific change (not the entire dirty tree)
- Then rebuild the ndnSIM binary
- Then do a small diagnostic routing_main run to verify the fix works
- **Requires user approval**: this modifies runtime C++ code (already modified but uncommitted)

### 1.4 Decide inf_tag_forwarding treatment [REQUIRED — unblocks baseline comparison]
- Recommendation: drop as separate baseline, note as aliased to flat_iroute
- Alternative: defer to PHASE 3 workload redesign if tag bitmap selectivity can be fixed there
- **Requires user input**: which option to take

### 1.5 Instrument first-choice vs terminal metrics [REQUIRED — unblocks object_main interpretation]
- Add `manifestFetchIndex` at finish time to query_log.csv
- Derive `first_manifest_position_correct` = 1 if manifestFetchIndex == 0 && success
- Derive `manifest_rescue_rank` = manifestFetchIndex if success && manifestFetchIndex > 0
- Update aggregation scripts to propagate these
- **Can proceed independently** — does not block routing fix

### 1.6 Rename/qualify success_at_1
- Add `first_object_correct` column alongside existing `success_at_1`
- Update paper text to distinguish "terminal success" from "first-choice quality"
- Rename `success_at_1` to `terminal_success` in new runs (keep old name as alias for traceability)

### 1.7 Fix manifest_hit_at_5 label
- Small fix in run_experiment.py normalization to use actual requestedManifestSize

### 1.8 Create metrics schema doc
- `docs/metrics/metric_semantics.md`

### 1.9 Small-sample smoke test
- After fixes 1.3 + 1.5, run 10-query diagnostics for both routing_main and object_main
- Verify new metrics produce expected, non-degenerate output

## Order of operations

```
1.3 (commit matchesBitmap fix + rebuild)     ← FIRST, unblocks routing
  ↓
1.4 (inf_tag_forwarding decision)             ← can be decided now
  ↓
1.5 (instrument first-choice metrics)         ← can start in parallel with 1.3
  ↓
1.6 (rename success_at_1)                     ← after 1.5
1.7 (fix manifest_hit_at_5)                   ← small, can parallel
1.8 (metrics schema doc)                      ← after 1.5, 1.6
  ↓
1.9 (smoke test)                              ← LAST, validates everything
```

## Estimated remaining effort for PHASE 1

| Task | Effort | Blocks |
|------|--------|--------|
| 1.3 commit + rebuild + diagnostic | 1 session | Figures 4/6/7 |
| 1.4 inf_tag decision | 5 min | Baseline count |
| 1.5 first-choice instrumentation | 0.5 session | object_main interpretation |
| 1.6 success_at_1 rename | 15 min | Paper metric names |
| 1.7 manifest_hit fix | 5 min | Minor label |
| 1.8 metrics doc | 20 min | Documentation |
| 1.9 smoke test | 0.5 session | PHASE 1 gate |
