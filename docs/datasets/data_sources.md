# Data Sources

## Planned source family

- Smart Data Models domain repositories and shared schema definitions.
- Rocketfuel IMW2002 `weights.intra` and `latencies.intra` files for ISP-style backbone topologies.

## Rocketfuel source policy

- Primary source: `https://research.cs.washington.edu/networking/rocketfuel/maps/weights-dist.tar.gz`
- Required AS pairs: `3967` (Exodus) and `1239` (Sprint)
- Import mode: download raw archive once, extract `*.weights.intra` and `*.latencies.intra`, convert offline into ndnSIM annotated topology files, then run scenarios against the converted annotated topologies.
- Fallback policy: if the official archive is unavailable, clone `cawka/ndnSIM-sample-topologies` only for reference inventory; it does not replace the official `3967/1239` IMW2002 files.

## Output contract

The workflow will transform external schemas and metadata into versioned local artifacts for:

- objects
- queries
- qrels
- hierarchy summaries
- topology mappings

## Topology defaults

- `rf_3967_exodus` is the default medium-scale Rocketfuel topology.
- `rf_1239_sprint` is the default large-scale Rocketfuel topology.
