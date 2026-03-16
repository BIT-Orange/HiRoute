# Figure: fig_candidate_shrinkage

## Purpose

- Show HiRoute's staged frontier contraction and separate it from cross-method probe breadth.

## Built from

- `results/aggregate/candidate_shrinkage.csv`

## Promoted runs

- `exp_routing_main_v2` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- In the left panel, `hiroute` still provides the clearest mechanism signal in the v2 results. At budget `16`, the frontier shrinks from `1.0` at `all_domains` to `0.409896` by the `refined_cells/probed_cells` stage, while `flat_iroute`, `flood`, and `inf_tag_forwarding` stay around `0.603125`.
- In the right panel, the cross-method comparison now reports discovery breadth directly through mean remote probes/query. At budget `16`, `hiroute` uses `2.325` probes/query, below `2.8625` for both `flat_iroute` and `inf_tag_forwarding`, though still above `2.1875` for `flood`.
- This figure is therefore still a valid mechanism figure even though the main routing workload no longer separates methods on success.

## Caveats

- `oracle`, `flood`, and `flat_iroute` are intentionally not placed on the staged contraction curve because they do not share the same hierarchical refinement pipeline.
