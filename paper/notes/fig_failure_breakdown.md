# Figure: fig_failure_breakdown

## Purpose

- Present the compact object-main manifest sweep as the primary effectiveness figure.
- Show how object-level success and wrong-object rate change with manifest size under `object_hard_v3`.

## Built from

- `results/aggregate/v3/compact/object_main_manifest_sweep.csv`
- `results/aggregate/v3/compact/failure_breakdown.csv` remains a support aggregate, not the paper-facing chart.

## Promoted runs

- `exp_object_main_v3_compact` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- The clearest compact discriminative signal is object-level semantic resolution, not routing success.
- At `manifest_size=1`, `hiroute` reaches `0.9375` success with `0.0625` wrong-object rate, while `flat_iroute` and `inf_tag_forwarding` stay tied at `0.908333` success with `0.091667` wrong-object rate.
- `central_directory` remains the upper reference at `1.0`, but the compact paper-facing claim is that `hiroute` is more manifest-efficient at local semantic resolution than the strong distributed baselines.
- Larger manifests do not create a stronger separation than `manifest_size=1`; the main story is that the ranking advantage is already visible before broader fallback has much room to help.

## Caveats

- The support `failure_breakdown.csv` is still useful for appendix diagnosis, but Figure 5 itself is no longer a stacked failure-composition chart.
- The compact interpretation should stay centered on wrong-object reduction and manifest-efficient resolution rather than on a broad claim of universal dominance.
