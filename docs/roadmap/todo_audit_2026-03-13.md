# Todo Audit 2026-03-13

This audit cross-checks `Todo.md` and `paper/main.tex` against the current HiRoute implementation.

## Resolved In This Batch

- Robustness injection now targets the dominant query domain instead of the first controller or the first topology link.
- Link-failure mode now disables controller-adjacent links for the selected target domain, which is materially closer to the paper's intended physical-failure stress.
- Staleness mode now records and targets the same dominant domain so Figure 9 reflects a deliberate semantic-drift stress point.
- The robustness experiments now produce non-trivial degradation curves, which means Figure 9 is testing a real failure path instead of a nearly no-op scenario.
- The default hierarchy now partitions level-1 cells by `zone_id + service_class`, which matches the paper's default predicate-cell design.
- The hierarchy builder now enforces a minimum object count per semantic microcluster, which removed the earlier flood of singleton level-2 cells.
- Figure 6 now reads explicit staged search traces (`all_domains -> predicate_filtered_domains -> level0 -> level1 -> refined -> probed -> manifest`) instead of inferring everything from one predicate-shrinkage scalar.
- Figure 8 now uses fixed-budget sweeps over objects per domain and active domain count, which restores the control-plane scaling experiment described in `paper/main.tex`.

## Still Misaligned With `paper/main.tex`

### 1. Robustness is now informative, but not yet good

- After the stronger injections, `hiroute` no longer dominates Figure 9.
- Impact: this is no longer a measurement bug; it is an implementation weakness that now deserves protocol-level work rather than scenario-level fixes.

### 2. Scaling still uses eight active application domains

- The current Smart Data Models workload maps objects and summaries onto eight active data domains, even when the Rocketfuel topology exposes more routing partitions.
- Impact: Figure 8 now has the correct fixed-budget sweep semantics, but the domain-count panel tops out at eight active data domains instead of exploring a denser data-plane deployment on `rf_1239_sprint`.

## Next Implementation Priority

1. Improve protocol robustness so `hiroute` degrades less sharply under targeted stale summaries and controller-domain failures.
2. Expand the dataset/topology binding so the large Rocketfuel topology can host more than eight active application domains.
3. Revisit Figure 9 after robustness fixes to confirm whether the failure sensitivity is architectural or implementation-specific.
