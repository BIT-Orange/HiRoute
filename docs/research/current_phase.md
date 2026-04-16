# Current Phase

**Phase**: 1 — Metric Semantics & Observability Repair  
**Started**: 2026-04-15  
**Status**: PHASE 1 GATE PASSED

## Completed

- [x] P1.1: Diagnose routing_main zeros → matchesBitmap bug
- [x] P1.2: Diagnose flat_iroute = inf_tag_forwarding → uniform tag bitmaps
- [x] P1.3: Commit matchesBitmap fix (commit ac342a7)
- [x] P1.4: Remove flat_iroute from active configs (commit 5d90f72)
- [x] P1.5: Instrument first-choice metrics — first_fetch_relevant + manifest_fetch_index (commit ba06518)
- [x] P1.6-1.8: Metrics schema documentation (commit 1f7161c)

## Remaining

- [ ] Phase 2: Route A vs Route B paper/experiment decision and full mainline rerun
- [ ] Investigate the long-running behavior of `routing_debug` / `object_debug` ndnSIM runs, which did not finish promptly despite `stopSeconds=8`

## Phase 1 gate criteria

- [x] matchesBitmap fix committed
- [x] First-choice metrics exist in C++ logging
- [x] success_at_1 semantics documented (terminal, not first-choice)
- [x] Metrics schema documented
- [x] Binary rebuilt and smoke test passed

## Phase 1 closure evidence

- `2026-04-16`: `cd ns-3 && ./waf build` completed successfully.
- `2026-04-16`: `routing_main` smoke run completed successfully under
  `routing_main__hiroute__smartcity__rf_3967_exodus_compact__budget16__manifest5__seed1__20260416_030130`.
- Smoke validation summary:
  - `query_log.csv` contains `first_fetch_relevant` and `manifest_fetch_index`
  - `240/240` rows populated
  - `240/240` rows have non-zero end-to-end success
  - `240/240` rows have at least one remote probe
  - `184` rows show manifest rescue (`manifest_fetch_index > 0` with terminal success)

## Notes

- The current `run_experiment.py` interface uses `--mode official`; older notes that say `--mode run` are stale.
