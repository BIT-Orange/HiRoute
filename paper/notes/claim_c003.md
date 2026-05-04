# Claim C-003

## Text

HiRoute keeps exported discovery state bounded by the configured summary budget in the state-only
scaling experiment. Figure 8 supports that bounded-state claim only; it does not measure query
success, latency, or discovery bytes. Figure 9 is a diagnostic degradation profile for stale
summaries and controller failures, not a clean robustness win or final promotion result.

## Supported by

- `results/figures/mainline/fig_state_scaling.pdf`
- `results/figures/mainline/fig_robustness.pdf`

## Aggregates

- `results/aggregate/mainline/state_scaling_summary.csv`
- `results/aggregate/mainline/robustness_summary.csv`

## Source runs

- `state_scaling`
- `robustness`, pending raw-run provenance repair or clean rerun

## Status

Figure 8 support-only; Figure 9 diagnostic/blocking until robustness provenance and clean-promotion
gates pass
