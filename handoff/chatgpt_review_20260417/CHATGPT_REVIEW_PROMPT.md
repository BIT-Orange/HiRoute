Please review this HiRoute experiment bundle as a critical technical reviewer.

Context:

- The project is converging on Route B: rewrite the paper to match the implemented system rather than adding missing semantic-centroid / cosine-similarity machinery.
- The included bundle contains only the key source files, refreshed mainline aggregates, rendered figures, and stage decision artifacts.
- The current gate state is:
  - `object_main = ready_for_main_figure`
  - `ablation = ready_for_support_figure`
  - `routing_main = completed`
  - `state_scaling = completed`
  - `robustness = completed`
  - `full_mainline = completed`

What I want from you:

1. Check whether the current Route B narrative is actually supported by the included data.
2. Identify the strongest and weakest claims the authors can still make without overstating the implementation.
3. Review the object-level result carefully:
   - HiRoute reaches `1.0` terminal success but only about `0.620833` first-fetch correctness.
   - Manifest rescue is still invariant at `0.0`.
   - Is this still a main-figure result, and if so, what is the honest claim?
4. Review the ablation result carefully:
   - terminal-success ordering is clean
   - cost ordering is not clean
   - first-fetch ordering is not identical to terminal-success ordering
   - Is the current support-figure interpretation technically sound?
5. Review routing/state/robustness:
   - `routing_main` has saturated terminal success, so is it only a support figure now?
   - `state_scaling` is state-only with `query_count = 0` by design; is that framing clear and defensible?
   - `robustness` shows degradation for HiRoute under `controller_down`; is the resulting story still useful?
6. Call out any contradictions between:
   - stage decisions
   - aggregate CSVs
   - figure implications
   - likely paper claims

Please prioritize:

- claim/data mismatches
- overstatements
- hidden assumptions
- missing controls
- whether the current figures are publication-credible for Route B

Do not waste time on style. Focus on technical validity and publication risk.
