# Figure: fig_ablation

## Purpose

- Summarize component-level tradeoffs across the current comparison set.

## Built from

- `results/aggregate/ablation_summary.csv`

## Promoted runs

- Current `exp_ablation_v2` promoted runs on commit `c4e7cfc`.

## Observations

- The corrected ablation no longer supports the old causal story. `full_hiroute`, `predicates_only`, and `predicates_plus_flat` all reach `1.0` success on the current `object_hard` bundle once sequential fallback is enforced.
- Only `flat_semantic_only` still fails badly (`0.141667` success, `0.858333` wrong-object rate, `605.770833` discovery bytes/query), which shows that semantics without the hard predicate header is not sufficient.
- The current takeaway is therefore a workload diagnosis: the present `object_hard` tier is still too constraint-dominant for a publication-grade ablation, because predicates remain strong enough to recover full success even without the full hierarchy.

## Caveats

- Treat Figure 10 as `sanity-only` until the object-level workload is hardened.
