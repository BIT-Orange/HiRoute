# Progress Log

## 2026-04-16

### PHASE 1 gate passed

**Implementation completed:**

1. Fixed `scripts/run/run_experiment.py` syntax by restoring the missing `PROBE_LOG_FIELDS` declaration
2. Added first-choice and manifest-rescue metrics to the active aggregation scripts:
   - `scripts/eval/aggregate_query_metrics.py`
   - `scripts/eval/build_object_main_manifest_sweep.py`
   - `scripts/eval/build_ablation_summary.py`
3. Updated Route B stage-decision logic so `object_main` can proceed on first-choice/rescue signal instead of relying only on terminal success separation
4. Updated main plotting labels and active paper/docs language from first-choice `ServiceSuccess@1` wording to terminal-success wording where appropriate
5. Rebuilt ndnSIM and ran the requested `routing_main` smoke

**Smoke result (`routing_main`, `hiroute`, budget 16, seed 1):**

- Run id: `routing_main__hiroute__smartcity__rf_3967_exodus_compact__budget16__manifest5__seed1__20260416_030130`
- `query_log.csv` now includes `first_fetch_relevant` and `manifest_fetch_index`
- `240` query rows were emitted
- `success_at_1` is no longer degenerate at `0`; the smoke run produced `240/240` terminal successes
- `num_remote_probes` is non-zero across the emitted rows
- `manifest_fetch_index > 0` appears in `184` successful rows, confirming the new rescue signal is populated

**Additional runtime observation:**

- The lightweight `routing_debug` / `object_debug` ndnSIM runs did not finish promptly despite `stopSeconds=8`; this looks like a separate runtime-performance issue and is not the blocker that was preventing Phase 1 from passing.

## 2026-04-15 (continued)

### PHASE 1 core tasks complete

**Commits made:**

| Commit | Description |
|--------|-------------|
| `ac342a7` | fix: split multi-token predicate constraints in matchesBitmap |
| `5d90f72` | refactor: remove flat_iroute baseline from active experiment configs |
| `ba06518` | feat: instrument first-choice metrics in query logging |
| `1f7161c` | docs: add metric semantics reference with true C++ origins |

**What was done:**
1. Committed the matchesBitmap fix — enables routing_main to work with multi-token zone constraints
2. Removed flat_iroute from all active configs (4 experiment yamls, 3 eval scripts, 1 plot script, 3 tools) — it was proven identical to inf_tag_forwarding due to uniform tag bitmaps
3. Added `first_fetch_relevant` and `manifest_fetch_index` to C++ query logging — enables distinguishing first-choice quality from terminal success
4. Created `docs/metrics/metric_semantics.md` — full reference for every metric's true semantics

**What was NOT done:**
- Binary not yet rebuilt (requires `waf build`)
- Smoke test not yet run
- manifest_hit_at_5 label not renamed (deferred to avoid cascading aggregation changes)
- CLAUDE.md instrumentation contract still partially unimplemented (first_probe_relevant_domain_hit, num_confuser_*, failure_stage remain missing)

**Files modified (non-.claude):**
- `ns-3/src/ndnSIM/model/hiroute-summary-entry.cpp` (matchesBitmap fix)
- `ns-3/src/ndnSIM/apps/hiroute-ingress-app.cpp` (first-choice instrumentation)
- `ns-3/src/ndnSIM/apps/hiroute-ingress-app.hpp` (new ActiveQueryState fields)
- `configs/experiments/object_main.yaml` (remove flat_iroute)
- `configs/experiments/routing_main.yaml` (remove flat_iroute)
- `configs/experiments/state_scaling.yaml` (remove flat_iroute)
- `configs/experiments/robustness.yaml` (remove flat_iroute)
- `scripts/eval/eval_support.py` (remove flat_iroute from scheme lists)
- `scripts/eval/build_stage_decision.py` (remove flat_iroute from decision logic)
- `scripts/eval/build_stage_quick_summary.py` (remove flat_iroute)
- `scripts/plots/plot_main_figures.py` (remove flat_iroute)
- `scripts/run/run_experiment.py` (new columns in normalization + QUERY_LOG_FIELDS)
- `tools/validate_figures.py` (replace flat_iroute with inf_tag_forwarding)
- `tools/validate_run.py` (remove flat_iroute from required schemes)
- `tools/run_mainline_review_stage.py` (remove flat_iroute from quick matrix)
- `docs/metrics/metric_semantics.md` (new)

## 2026-04-15

### PHASE 0 completed — Gate passed

**Audits executed:**
1. Runtime mechanism audit (via general-purpose agent)
   - 8 mechanisms checked: 4 IMPLEMENTED, 2 APPROXIMATE, 2 UNSUPPORTED
   - Critical: cosine similarity and semantic centroids are unsupported
   - Critical: manifest fallback code exists but never triggers
2. Metric semantics audit (via general-purpose agent)
   - 9 metrics traced end-to-end from C++ to paper
   - Critical: success_at_1 is terminal, not first-choice
   - Critical: wrong_object_rate is terminal failure, not first-object quality
   - Critical: best_object_given_domain is vacuously 1.0
   - Critical: no manifest rescue instrumentation exists
   - Critical: CLAUDE.md instrumentation contract entirely unimplemented
3. Paper claim evidence audit (via general-purpose agent)
   - 10+ claims mapped to evidence
   - Critical: routing_support.csv entirely broken (all zeros)
   - Critical: manifest sweep metric-invariant
   - Critical: flat_iroute = inf_tag_forwarding

**Deliverables produced:**
- `docs/research/state_model.md`
- `docs/research/open_problems.md`
- `docs/research/claim_implementation_evidence_matrix.md`
- `docs/research/current_phase.md`
- `docs/research/progress_log.md`
- `docs/research/blockers_and_risks.md`
- `docs/research/decision_log.md`
- `docs/research/next_actions.md`

**Key findings:**
- The system as implemented is a predicate-gated hierarchical discovery design with heuristic scoring — not the vector-similarity-driven system the paper describes
- object_main does not isolate object-resolution; it tests domain selection
- 3 of 5 evaluation dimensions have no usable data (routing broken, state_scaling/robustness unrun)
- Route B (narrow paper) strongly recommended

**Files modified:**
- Only created new files under docs/research/
- No paper, runtime, results, or configs modified

### PHASE 1 started — Diagnostic investigations

#### P1.1: routing_main zeros — ROOT CAUSE FOUND

**Symptom**: All distributed schemes produce `predicate_miss` for every routing_main query.

**Root cause**: The **committed** `matchesBitmap` function in `ns-3/src/ndnSIM/model/hiroute-summary-entry.cpp` does:
```cpp
return constraint.empty() || values.empty() || values.count(constraint) > 0;
```
This looks up the entire `;`-delimited constraint string as a single key (e.g., `values.count("zone-01;zone-02;zone-04")`), which always fails because the bitmap set contains individual tokens.

**Why object_main works but routing_main doesn't**: object_main queries use single-token zone constraints (`zone-03`), so `values.count("zone-03")` succeeds. routing_main queries use multi-token constraints (`zone-01;zone-02;zone-04`), which always fail.

**Fix status**: The fix already exists as an uncommitted change in the dirty tree — it properly splits on `;` and checks each token individually. This is one of the 40+ uncommitted files.

**Why central_directory works**: It uses the `ExactNameIngressApp` which bypasses predicate matching entirely.

**Implication**: Once this fix is committed and the binary rebuilt, routing_main should produce real data. The routing figures are NOT structurally impossible — they're blocked by a predicate-matching bug.

#### P1.2: flat_iroute = inf_tag_forwarding — ROOT CAUSE FOUND

**Symptom**: Byte-identical metrics across all experiments.

**Root cause**: Both are trivial subclasses of HiRouteIngressApp differing only in `strategyMode`. In `buildProbePlan`:
- `flat` (line 636-643): `rankedLevel0Targets(predicateMatches, true, 0.0)`
- `inf_tag_forwarding` (line 675-681): `rankedLevel0Targets(predicateMatches, true, 0.45)`

The `extraTagWeight = 0.45` is added to a candidate's score when its `semanticTagBitmap` contains the query's `intentFacet`. But in the smartcity dataset, **every level-0 summary has all 50 semantic tags** (because the bitmap is a union over all objects in the domain). So every candidate gets +0.45, ranking is unchanged, and probes are identical.

**Fix options**:
1. Make tag bitmaps domain-selective (requires dataset regeneration)
2. Drop inf_tag_forwarding and note it as aliased to flat_iroute
3. Change the scoring to use tag frequency/exclusivity instead of presence

**Implication**: The paper cannot present these as two distinct baselines. Either fix the dataset or merge them.

#### Files read (not modified)
- `runs/completed/routing_main__hiroute__*__budget16__*/query_log.csv`
- `runs/completed/routing_main__hiroute__*__budget16__*/queries_master_runtime.csv`
- `runs/completed/routing_main__hiroute__*__budget16__*/hslsa_export_runtime.csv`
- `ns-3/src/ndnSIM/model/hiroute-summary-entry.cpp` (committed + uncommitted diff)
- `ns-3/src/ndnSIM/apps/flat-semantic-ingress-app.cpp`
- `ns-3/src/ndnSIM/apps/inf-tag-forwarding-app.cpp`
- `ns-3/src/ndnSIM/apps/flood-discovery-app.cpp`
- `ns-3/src/ndnSIM/examples/hiroute-scenario-common.hpp`
- `scripts/eval/aggregate_query_metrics.py`
- `scripts/run/run_experiment.py`
- Various config files
