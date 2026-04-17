# HiRoute ChatGPT Review Bundle

## Snapshot

- Date: `2026-04-17`
- Branch: `develop/mainline-rerun-20260416`
- Relevant implementation commits:
  - `2302c15` `Refine mainline rerun reuse and state-only gating`
  - `35262c1` `Mark generic stages completed in status`
  - `a3a00be` `Fix duplicate-scheme mainline plotting`
  - `30a7a5d` `Record refreshed mainline figure status`

This bundle is a compact handoff for external review. It includes the key source files, refreshed mainline aggregates, rendered figures, and stage decision/check artifacts. It does not include the full raw `runs/completed/` tree.

## Current Gate State

- `object_main`: `ready_for_main_figure`
- `ablation`: `ready_for_support_figure`
- `routing_main`: `completed`
- `state_scaling`: `completed`
- `robustness`: `completed`
- `full_mainline`: `completed`

## Key Results

- `object_main`
  - `hiroute`: terminal success `1.0`, first-fetch correctness `0.620833`, manifest rescue `0.0`
  - `inf_tag_forwarding`: terminal success `0.908333`, first-fetch correctness `0.670833`
  - stage decision: object figure is still usable, but the live story is terminal success versus first-fetch correctness, not manifest rescue
- `ablation`
  - clean terminal-success ordering across all manifest sizes:
    - `full_hiroute 1.0`
    - `predicates_plus_flat 0.908333`
    - `predicates_only 0.841667`
    - `flat_semantic_only 0.575`
  - stage decision: support figure, mechanism ordering clean
- `routing_main`
  - success is saturated at `1.0` for all active schemes, so this is not a headline success figure
  - at budget `16`, `hiroute` still improves probes/bytes over `predicates_only` and `inf_tag_forwarding`
- `state_scaling`
  - this is a `state_only` experiment
  - `query_count = 0` and query-side metrics are intentionally empty / `NaN`
  - exported-state outputs are valid and traceable
- `robustness`
  - `central_directory` stays flat at `1.0`
  - `hiroute` degrades under `controller_down` to `0.727273` min success, while `stale_summaries` stays at `1.0`
  - recovery incurs extra probes for `hiroute`

## Suggested Review Questions

- Does the current evidence support a Route B paper framing better than a Route A framing?
- Is `object_main` still strong enough to keep as the primary figure if first-fetch correctness remains far below terminal success for HiRoute?
- Is the ablation interpretation sound even though first-fetch correctness is not ordered the same way as terminal success?
- Should `routing_main` remain a support figure only, given saturated terminal success?
- Are there obvious claim/data mismatches, missing controls, or figure interpretation risks in `state_scaling` or `robustness`?

## Bundle Layout

- `code/`: key source and workflow files
- `results/aggregate/mainline/`: refreshed mainline CSV/trace artifacts
- `results/figures/mainline/`: rendered mainline PDF/PNG figures
- `review_artifacts/`: stage checks and decision JSONs used for the current gating state
- `CHATGPT_REVIEW_PROMPT.md`: a ready-to-paste review prompt
