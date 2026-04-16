# Claim → Implementation → Evidence Matrix

Generated: 2026-04-15 (PHASE 0 audit)

## Legend

- **Impl**: IMPLEMENTED / APPROXIMATE / UNSUPPORTED
- **Evidence**: YES / PARTIAL / NO / STALE / BROKEN
- **Danger**: HIGH / MEDIUM / LOW

## Matrix

| # | Paper Claim | Impl Status | Evidence Status | Key Data | Danger |
|---|------------|-------------|-----------------|----------|--------|
| 1 | Cosine similarity scoring (Eq. 2: Sim(v_q, μ_c)) | UNSUPPORTED | N/A — untestable | computeSemanticScore uses heuristic tag/hint matching, no vector math | HIGH |
| 2 | Semantic centroids stored and consumed | UNSUPPORTED | N/A | centroidRow is int index, never dereferenced to vector | HIGH |
| 3 | Manifest size improves object resolution | IMPLEMENTED (fallback code exists) | NO — metric-invariant | manifest 1/2/3 produce identical results for all schemes | HIGH |
| 4 | Reduces unnecessary remote probes (routing) | IMPLEMENTED | BROKEN | routing_support.csv: all distributed schemes = 0.0 for every metric | HIGH |
| 5 | Narrows domain-to-object gap | IMPLEMENTED | NO | wrong_object_rate = 0.0 universally; no object-level failures to narrow | HIGH |
| 6 | Candidate shrinkage via hierarchical filtering | IMPLEMENTED | BROKEN | candidate_shrinkage.csv: 0.0 at all stages for distributed schemes | HIGH |
| 7 | Deadline-sensitive latency | IMPLEMENTED | BROKEN | deadline_summary.csv: 0% satisfaction for distributed schemes | HIGH |
| 8 | Ablation shows mechanism ordering | IMPLEMENTED | PARTIAL | Success ordering is clean (0.575 < 0.842 < 0.908 < 1.0), but all failures are wrong_domain, not wrong_object; invariant across manifest | MEDIUM |
| 9 | Predicate filtering eliminates before ranking | IMPLEMENTED | YES (implicit) | Code confirms hard gate before scoring | LOW |
| 10 | Hierarchical refinement (3-level traversal) | IMPLEMENTED | YES (implicit) | buildProbePlan does genuine parent→child traversal | LOW |
| 11 | Manifest fallback (sequential) | IMPLEMENTED | UNTRIGGERED | Code exists but wrong_object=0 means it never fires | MEDIUM |
| 12 | Reliability-aware suppression | IMPLEMENTED | YES (implicit) | EWMA + negative cache functional for hiroute/full_hiroute modes | LOW |
| 13 | Bounded exported state | IMPLEMENTED | NO DATA | No state_scaling experiment in mainline | MEDIUM |
| 14 | Robustness under failures/staleness | IMPLEMENTED | NO DATA | No robustness experiment in mainline | MEDIUM |
| 15 | Covering radii in semantic distance | APPROXIMATE | N/A | Used as tiebreaker (0.2/(1+r)), not geometric distance | LOW |
| 16 | flat_iroute vs inf_tag_forwarding distinction | UNCLEAR | NO | Identical metrics in every experiment | MEDIUM |
| 17 | Single-seed evaluation | N/A | WEAK | Only seed=1; no variance information | MEDIUM |

## Summary

- **HIGH danger** (items 1-7): 7 claims that are either unsupported by code or have broken/invariant evidence
- **MEDIUM danger** (items 8, 11, 13-14, 16-17): 6 claims with partial or missing evidence
- **LOW danger** (items 9-10, 12, 15): 4 claims that are genuinely implemented and directionally supported

## Critical path

The project cannot be submitted until items 1-7 are resolved. Items 1-2 require the Route A/B decision. Items 3-7 require fixing the routing_main/object_main experiments or downscoping the paper.
