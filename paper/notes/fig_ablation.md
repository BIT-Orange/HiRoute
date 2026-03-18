# Figure: fig_ablation

## Purpose

- Summarize the compact object-hard ablation at `manifest_size=1`.
- Isolate the benefit of the full hierarchy before wider fallback can wash out ranking differences.

## Built from

- `results/aggregate/v3/compact/ablation_summary.csv`

## Promoted runs

- `exp_ablation_v3_compact` promoted runs on commit `d335cd4` and the compact postprocess fix on commit `ce17889`.

## Observations

- At `manifest_size=1`, the compact ablation carries a real ordering: `full_hiroute (0.9375)` > `predicates_plus_flat (0.908333)` > `predicates_only (0.841667)` >> `flat_semantic_only (0.575)`.
- The same ordering appears in wrong-object rate, with `full_hiroute` at `0.0625` and `flat_semantic_only` at `0.175`.
- The paper-facing takeaway is now mechanism evidence rather than sanity-only diagnosis: the full hierarchy is most useful when fallback is tight enough that local ranking still matters.

## Caveats

- Larger manifest settings remain in `ablation_summary.csv`, but the paper-facing figure intentionally fixes `manifest_size=1`.
- Panel C should use a single cost metric consistently; the current compact paper path uses discovery bytes rather than switching between bytes and probes.
