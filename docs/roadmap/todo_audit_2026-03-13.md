# Todo Audit 2026-03-13

This audit cross-checks `Todo.md` and `paper/main.tex` against the current HiRoute implementation.

## Resolved In This Batch

- The Smart Data Models workload now materializes sixteen active data domains instead of eight, which matches the large-topology experiment design in `Todo.md`.
- The official runner now slices runtime objects, qrels, summaries, and controller-local indexes by the active topology domains, so `rf_3967_exodus` runs on an eight-domain subset while `rf_1239_sprint` exercises the full sixteen-domain deployment.
- Figure 8 now shows the intended fixed-budget state scaling behavior on both topologies: the `rf_1239_sprint` domain sweep reaches `16` active domains and exported summaries grow from `64 -> 128 -> 192 -> 256` under the fixed budget.
- The HiRoute reliability path now uses the correct domain identifiers, combines cell/domain EWMA, applies predicate-aware domain suppression, and replans after failed probes instead of marching through a stale static frontier.
- Figure 9 now reflects the repaired fallback behavior: `hiroute` recovers to `0.868852` under stale summaries, `0.803279` under link failure, and `0.688525` under domain failure.
- Robustness injection now targets the dominant query domain instead of the first controller or the first topology link.
- Link-failure mode now disables controller-adjacent links for the selected target domain, which is materially closer to the paper's intended physical-failure stress.
- Staleness mode now records and targets the same dominant domain so Figure 9 reflects a deliberate semantic-drift stress point.
- The robustness experiments now produce non-trivial degradation curves, which means Figure 9 is testing a real failure path instead of a nearly no-op scenario.
- The default hierarchy now partitions level-1 cells by `zone_id + service_class`, which matches the paper's default predicate-cell design.
- The hierarchy builder now enforces a minimum object count per semantic microcluster, which removed the earlier flood of singleton level-2 cells.
- Figure 6 now reads explicit staged search traces (`all_domains -> predicate_filtered_domains -> level0 -> level1 -> refined -> probed -> manifest`) instead of inferring everything from one predicate-shrinkage scalar.
- Figure 8 now uses fixed-budget sweeps over objects per domain and active domain count, which restores the control-plane scaling experiment described in `paper/main.tex`.

## Residual Risk

- Figure 9 is now aligned with the paper's intended failure model and the repaired fallback path materially improves `hiroute`, but domain failure remains the harshest case and still deserves future tuning if the paper wants to claim stronger resilience.
- Figure 8 is now structurally correct and uses the proper active-domain counts, but it is intentionally a state-only scenario, so its query-side columns in the aggregate are placeholders rather than full end-to-end workload measurements.
