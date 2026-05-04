# `fig_overview` / `fig_query` Revision Notes

## Confirmed Issues

- `paper/paper.tex` referenced `figures/fig_query.png` instead of the available PDF asset.
- Both figures framed the query input too much like online natural-language decomposition, while the current prototype consumes offline-preprocessed query rows with structured predicate fields and semantic references.
- `fig_overview` did not make the discovery exchange read clearly as ordinary NDN Interest/Data carrying `ApplicationParameters` and a ranked manifest reply.

## Applied Repo Changes

- Updated [paper.tex](/Users/jiyuan/Desktop/HiRoute/paper/paper.tex:188) to use `figures/fig_query.pdf`.
- Tightened the `fig_query` caption wording from `Query decomposition` to `Query structuring`.
- Synced the paper-local figure directory by copying the current figure assets into [paper/figures](/Users/jiyuan/Desktop/HiRoute/paper/figures).

## Reference Assets

- Original local references:
  - [fig_overview_reference.png](/Users/jiyuan/Desktop/HiRoute/paper/figures/fig_overview_reference.png)
  - [fig_query_reference.png](/Users/jiyuan/Desktop/HiRoute/paper/figures/fig_query_reference.png)
- GPT concept drafts:
  - [fig_overview_gpt_draft.png](/Users/jiyuan/Desktop/HiRoute/paper/figures/fig_overview_gpt_draft.png)
  - [fig_overview_gpt_draft.pdf](/Users/jiyuan/Desktop/HiRoute/paper/figures/fig_overview_gpt_draft.pdf)
  - [fig_query_gpt_draft.png](/Users/jiyuan/Desktop/HiRoute/paper/figures/fig_query_gpt_draft.png)
  - [fig_query_gpt_draft.pdf](/Users/jiyuan/Desktop/HiRoute/paper/figures/fig_query_gpt_draft.pdf)

## Draft Intent

- `fig_overview` draft keeps the same high-level composition but shifts the ingress wording toward `Query Structuring & Encoding`, clarifies the discovery callouts as controller-directed `Interest(s)` and manifest-bearing `Data`, and adds a lightweight summary embedding reference.
- `fig_query` draft keeps the same conceptual layout but recasts the left input as an offline-preprocessed `Example Query Row`, updates the semantic hint fields to include `intent facet` and `query embedding ref`, and relabels the hierarchy as `L0 Domain Root`, `L1 Coarse Predicate Cells`, and `L2 Semantic Microclusters`.

## Remaining Caveat

- The GPT drafts are suitable as concept/layout guides, but the final paper-facing PDFs should still be manually text-polished before replacing the canonical figure assets.
