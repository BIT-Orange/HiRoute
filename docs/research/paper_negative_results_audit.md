# HiRoute 论文“负面结果 / 未入文实验 / 诚实承认”审计

Generated: 2026-04-19

## 审计口径

- 当前论文主证据以 `results/aggregate/mainline/*.csv` 为准。
- 对外口径以 `paper/main.tex` 与 `paper/notes/*.md` 为准。
- `paper/notes/revision_log.md` 与 `docs/metrics/metric_semantics.md` 作为内部补充证据使用。
- `docs/research/*.md` 中 2026-04-15 的 PHASE 0 审计文档属于历史内部意见；若与当前 sealed mainline aggregate 冲突，应标记为“旧审计 / 历史问题”，不能直接当作当前论文事实。
- `results/aggregate/*.csv` 中不在 `mainline/` 下的结果统一视为 legacy experiment，不作为当前论文主证据。
- 文中的 `foo.csv:5,10` 这类定位均指 1-based 行号；对 CSV 来说第 1 行是表头。

## 总表

| 问题 | 正文是否承认 | 数据是否支持 | 口径标签 | 证据路径 |
| --- | --- | --- | --- | --- |
| First-fetch 明显不如 terminal success | 是 | 是 | `正文承认` | `paper/main.tex:297-323`, `paper/notes/fig_ablation.md:29-31`, `paper/notes/fig_object_manifest_sweep.md:30-33`, `results/aggregate/mainline/object_main_manifest_sweep.csv:5,10`, `results/aggregate/mainline/ablation_summary.csv:4,13` |
| 当前 workload 上 manifest rescue 没有信号 | 是 | 是 | `正文承认` | `paper/main.tex:314-323`, `paper/notes/fig_object_manifest_sweep.md:31-33`, `results/aggregate/mainline/object_main_manifest_sweep.csv:2-10`, `results/aggregate/mainline/failure_breakdown.csv:3-4,9-10,15-16` |
| HiRoute 在 latency 上没有优势 | 是 | 是 | `正文承认` | `paper/main.tex:338-349`, `paper/notes/fig_deadline_summary.md:24-31`, `results/aggregate/mainline/deadline_summary.csv:10-13,18-24` |
| Robustness 只能读成 degradation profile，不是全面鲁棒 | 是 | 是 | `正文承认` | `paper/main.tex:364-375`, `paper/notes/fig_robustness.md:25-33`, `results/aggregate/mainline/robustness_summary.csv:2-5` |
| routing slice 不是 headline win，只是 support figure | 是 | 是 | `正文承认` | `paper/main.tex:299-310`, `paper/notes/fig_routing_support.md:25-32`, `results/aggregate/mainline/routing_support.csv:2-15` |
| object_main 实际主要测到 domain selection，不是 object ranking | 否，正文只弱化未直说 | 是 | `内部承认` | `paper/notes/claim_c002.md:5-14`, `docs/research/state_model.md:63-72`, `results/aggregate/mainline/failure_breakdown.csv:3-4,9-10,15-16`, `results/aggregate/mainline/object_main_manifest_sweep.csv:2-10` |
| `success_at_1` 的语义比论文表面读法更“终态化” | 否 | 是 | `内部承认` | `docs/metrics/metric_semantics.md:83-93`, `results/aggregate/mainline/object_main_manifest_sweep.csv:5,10`, `results/aggregate/mainline/ablation_summary.csv:4,13` |
| Phase 2 rerun 后 HiRoute 当前 `1.0` 可能掉到 `0.6–0.8` | 否 | 当前仅有预测，未落地 | `待补实验` | `docs/metrics/metric_semantics.md:24-36`, `paper/notes/revision_log.md:5-11`, `results/aggregate/mainline/object_main_manifest_sweep.csv:5,10` |
| `fig_failure_breakdown` 已归档，不是当前正文图 | 否 | 是 | `已归档` | `paper/notes/fig_failure_breakdown.md:1-7`, `results/aggregate/mainline/failure_breakdown.csv:1-20` |
| `fig_main_success_overhead` 已归档，被 `fig_routing_support` 取代 | 否 | 是 | `已归档` | `paper/notes/fig_main_success_overhead.md:1-8`, `paper/notes/fig_routing_support.md:29-32`, `results/aggregate/mainline/routing_support.csv:12-15` |
| 仓库里存在比当前正文更难看的 legacy robustness 结果 | 否 | 是 | `已归档` | `results/aggregate/robustness_summary.csv:1-4`, `paper/notes/revision_log.md:31-38` |
| 还没写进正文、但内部已经明确要补做 adversarial stale_summaries | 否 | 是，当前 mainline 正显示现有版本过弱 | `待补实验` | `paper/notes/fig_robustness.md:33`, `paper/notes/revision_log.md:9-11`, `results/aggregate/mainline/robustness_summary.csv:4-5` |
| 还没写进正文、但内部已经明确要重做 object_main workload | 否 | 是，当前 mainline 没有 object ambiguity | `待补实验` | `paper/notes/revision_log.md:11`, `results/aggregate/mainline/object_main_manifest_sweep.csv:5,10`, `results/aggregate/mainline/failure_breakdown.csv:3-4,9-10,15-16` |
| 部分旧审计文档已经过时，不能直接当当前事实 | 否 | 是，且与当前 sealed mainline 冲突 | `内部承认` | `docs/research/state_model.md:74-79`, `docs/research/claim_implementation_evidence_matrix.md:17-28`, `results/aggregate/mainline/routing_support.csv:2-15`, `results/aggregate/mainline/deadline_summary.csv:18-24`, `results/aggregate/mainline/robustness_summary.csv:1-5` |

## 1. 正文明确承认，且实验数据也确实不好

| 问题 | 结论一句话 | 数据点 | 文件位置 | 口径标签 |
| --- | --- | --- | --- | --- |
| First-fetch 明显不如 terminal success | 当前论文已经把 HiRoute 写成“靠层级搜索 + recovery 拿到终态成功”，而不是 first-choice ranking 很强。 | `hiroute` 在 `object_main` 上 `mean_success_at_1 = 1.0`，但 `first_fetch_relevant_rate = 0.620833`；`full_hiroute` 在 `ablation` 上也同样是 `1.0` 对 `0.620833`。 | `paper/main.tex:297-323`, `paper/notes/fig_ablation.md:29-31`, `paper/notes/fig_object_manifest_sweep.md:30-33`, `results/aggregate/mainline/object_main_manifest_sweep.csv:5,10`, `results/aggregate/mainline/ablation_summary.csv:4,13` | `正文承认` |
| Manifest rescue 在当前 workload 上没有信号 | 论文已经诚实承认当前 workload 没有暴露出 meaningful manifest-rescue signal。 | `object_main_manifest_sweep.csv` 中所有方案、所有 `manifest_size` 的 `manifest_rescue_rate = 0.0`；`failure_breakdown.csv` 中 `wrong_object = 0.0` 全局成立。 | `paper/main.tex:314-323`, `paper/notes/fig_object_manifest_sweep.md:31-33`, `results/aggregate/mainline/object_main_manifest_sweep.csv:2-10`, `results/aggregate/mainline/failure_breakdown.csv:3-4,9-10,15-16` | `正文承认` |
| HiRoute 在 latency 上没有优势 | 当前正文和 figure note 已经把这部分改成 support-side tradeoff，不能再写成 latency winner。 | `routing_main` `budget=16` 下，`hiroute mean_latency_ms = 240.825`，`inf_tag_forwarding = 191.008333`，`central_directory = 83.525`。 | `paper/main.tex:338-349`, `paper/notes/fig_deadline_summary.md:24-31`, `results/aggregate/mainline/deadline_summary.csv:10-13,18-24` | `正文承认` |
| Robustness 不是“全面鲁棒”，而是故障画像 | 当前正文只允许把 robustness 读成 degradation profile：controller loss 确实伤到 HiRoute，stale summaries 这个场景又太弱。 | `controller_down / hiroute` 的 `min_success_after_event = 0.727273`；`stale_summaries / hiroute` 的 `min_success_after_event = 1.0`。 | `paper/main.tex:364-375`, `paper/notes/fig_robustness.md:29-33`, `results/aggregate/mainline/robustness_summary.csv:2-5` | `正文承认` |
| routing slice 只是 support figure | 正文已经明确说明 routing slice 在当前 workload 上不是 headline effectiveness claim。 | `routing_support.csv` 中多个 distributed scheme 在各 budget 下 `mean_success_at_1 = 1.0`，说明 terminal end-to-end success 已经饱和。 | `paper/main.tex:299-310`, `paper/notes/fig_routing_support.md:29-32`, `results/aggregate/mainline/routing_support.csv:2-15` | `正文承认` |

## 2. 正文弱化表述，但内部材料承认得更狠

| 问题 | 结论一句话 | 数据点 | 文件位置 | 口径标签 |
| --- | --- | --- | --- | --- |
| `object_main` 实际主要测到的是 domain selection | 内部材料已经把话说得更直：当前 `object_main` 并不能支持 object-resolution benefit，只能支持 domain-selection dominated 的解释。 | `wrong_object = 0.0` 全局成立；唯一非零失败项是 `inf_tag_forwarding wrong_domain = 0.091667`；`hiroute` 与 `central_directory` 在 `wrong_object` 上都为 `0.0`。 | `paper/notes/claim_c002.md:5-14`, `docs/research/state_model.md:63-72`, `results/aggregate/mainline/failure_breakdown.csv:3-4,9-10,15-16`, `results/aggregate/mainline/object_main_manifest_sweep.csv:2-10` | `内部承认` |
| `success_at_1` 不是严格 first fetch | 内部 metric 文档明确指出 `success_at_1` 记录的是 manifest fallback 和 reprobe 之后的 terminal success，而不是第一发对象质量。 | 当前 `object_main` / `ablation` 里 `success_at_1 = 1.0` 但 `first_fetch_relevant_rate = 0.620833` 的分离，本身就与“第一发成功率”直觉不一致。 | `docs/metrics/metric_semantics.md:83-93`, `results/aggregate/mainline/object_main_manifest_sweep.csv:5,10`, `results/aggregate/mainline/ablation_summary.csv:4,13` | `内部承认` |
| Phase 2 rerun 之后当前 `1.0` 可能会掉 | 内部已经预告：严格 relevance 语义落地后，HiRoute 当前 `object_main` 的 `1.0` 只是 Phase 1 sealed 值，不是稳定终值。 | `metric_semantics.md` 明确预测 `hiroute success_at_1` 可能从当前 sealed `1.0` 掉到 `0.6–0.8`；当前 sealed mainline 仍然是 `1.0`。 | `docs/metrics/metric_semantics.md:24-36`, `paper/notes/revision_log.md:5-11`, `results/aggregate/mainline/object_main_manifest_sweep.csv:5,10` | `待补实验` |
| 部分旧审计文档已经过时 | 2026-04-15 的 PHASE 0 审计把若干图判成“全坏 / 无数据”，但这些判断已经被后续 mainline rerun 覆盖。 | 旧审计声称 `routing_support/deadline/robustness` 不可用；当前 sealed mainline 中这些表已经有非零数据，`robustness_summary.csv` 也已存在。 | `docs/research/state_model.md:74-79`, `docs/research/claim_implementation_evidence_matrix.md:17-28`, `results/aggregate/mainline/routing_support.csv:2-15`, `results/aggregate/mainline/deadline_summary.csv:18-24`, `results/aggregate/mainline/robustness_summary.csv:1-5` | `内部承认` |

## 3. 做过但没有保留在当前正文里的实验 / 图

| 问题 | 结论一句话 | 数据点 | 文件位置 | 口径标签 |
| --- | --- | --- | --- | --- |
| `fig_failure_breakdown` 已归档 | 当前论文没有把 failure breakdown 当正文图，只保留为 appendix / diagnostic aggregate。 | 当前对应诊断数据仍保留在 `failure_breakdown.csv`，其中 `wrong_domain = 0.091667`、`wrong_object = 0.0`。 | `paper/notes/fig_failure_breakdown.md:1-7`, `results/aggregate/mainline/failure_breakdown.csv:1-20` | `已归档` |
| `fig_main_success_overhead` 已归档 | 早期的 main success vs overhead 图已从当前 paper path 移除，被 `fig_routing_support` 替代。 | 当前正文的替代图是 `routing_support`，其 active support slice 以 `reach / bytes / shrinkage` 为主，而不是 headline success-overhead。 | `paper/notes/fig_main_success_overhead.md:1-8`, `paper/notes/fig_routing_support.md:29-32`, `results/aggregate/mainline/routing_support.csv:12-15` | `已归档` |
| 旧版 robustness harsher scenarios 仍在仓库里 | 仓库里保留了比当前 mainline 正文更“难看”的 legacy robustness 结果，但这些没有进入当前正文图。 | legacy `robustness_summary.csv` 记录了 `staleness = 0.868852`、`link failure = 0.803279`、`domain failure = 0.688525`。 | `results/aggregate/robustness_summary.csv:1-4`, `paper/notes/revision_log.md:31-38` | `已归档` |

## 4. 还没写进论文、但内部已经明确说要补做或重跑

| 问题 | 结论一句话 | 数据点 | 文件位置 | 口径标签 |
| --- | --- | --- | --- | --- |
| 需要更强的 `stale_summaries` 变体 | 当前 stale-summaries 场景太弱，内部已经明确要补一个 adversarial 版本；在补出来前，不能把现有结果写成强 robustness 证据。 | 当前 `stale_summaries / hiroute` 的 `min_success_after_event = 1.0`，正是“压力不够”的直接证据。 | `paper/notes/fig_robustness.md:33`, `paper/notes/revision_log.md:9-11`, `results/aggregate/mainline/robustness_summary.csv:4-5` | `待补实验` |
| 需要重做 `object_main` workload | 内部已经明确要通过 workload redesign 引入真正 object ambiguity；不然 manifest rescue 和 wrong-object 仍然不会出信号。 | 当前 `object_main` 中 `manifest_rescue_rate = 0.0`、`wrong_object = 0.0`，说明这个 slice 还没有构造出 object-level ambiguity。 | `paper/notes/revision_log.md:11`, `results/aggregate/mainline/object_main_manifest_sweep.csv:5,10`, `results/aggregate/mainline/failure_breakdown.csv:3-4,9-10,15-16` | `待补实验` |
| 需要全量 Phase 2 semantics rerun | 内部已经把 Phase 2 metric semantics 定义好，但没有重新生成 sealed mainline；这意味着当前 paper-facing 数字只是在旧语义下封存。 | 当前 sealed `hiroute success_at_1 = 1.0` 仍是 Phase 1 结果；内部文档预计新语义下会落到 `0.6–0.8` 区间。 | `docs/metrics/metric_semantics.md:24-36`, `paper/notes/revision_log.md:5-11`, `results/aggregate/mainline/object_main_manifest_sweep.csv:5,10` | `待补实验` |

## 处理规则

- 凡是引用 `docs/research/*.md` 的地方，都应在正文外部使用，并明确标注为“历史内部审计意见”。
- 凡是引用 `results/aggregate/*.csv` 但路径不在 `mainline/` 下的地方，都应明确标注为 legacy experiment，而不是当前 paper-facing 结果。
- 若后续需要把本审计再压缩成 review 清单，优先保留以下四列：`问题`、`正文是否承认`、`数据是否支持`、`证据路径`。
