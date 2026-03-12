# Open Questions

## Hypothesis Cards

### H-001

**Question**  
Can hierarchical constraint-guided discovery reduce wrong-object failures compared with flat
semantic routing under ambiguous IoT workloads?

**Motivation**  
Flat semantic routing may reach a relevant domain but still fail at object-level resolution when
queries share similar service intent and partial constraints.

**Independent variables**  
summary budget, ambiguity level, manifest size

**Dependent variables**  
ServiceSuccess@1, wrong-object failure rate, probes/query, discovery_bytes, latency_ms

**Required implementation**  
hierarchical summaries, manifest reply, object-level qrels, promoted run gating

**Status**  
planned
