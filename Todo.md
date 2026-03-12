可以。下面我给你一套能直接落地的完整方案，分成两大部分。

第一部分是“按新稿逐节对应的 ndnSIM 实现与实验任务表”。这里会把论文每一节映射到模块、类、输入输出 CSV、baseline 落地方式和图表产物。

第二部分是“数据生成脚本设计文档”。这里会把数据从哪里下载、为什么这么选、目录结构怎么搭、每个 CSV 的精确列名、每个 Python 脚本做什么、以及给 Codex 的逐文件实现 prompt 全部列清楚。

我先给一个总判断。你这篇新稿最稳的路线，不是去追求“现成 benchmark 直接开跑”，而是用 Smart Data Models 的官方 smart city data models 作为语义和属性来源，自己生成一个面向 NDN-IoT name resolution 的实验语料。Smart Data Models 是 FIWARE、TM Forum、IUDX、OASC 等共同推动的开放数据模型计划，覆盖 Smart Cities、Smart Environment、Urban Mobility、Parking、Streetlighting、Weather 等领域；它的 GitHub 组织、总仓库和 SmartCities 仓库都是官方公开入口。

------

# 一、总目录结构

先把项目目录固定，不然后面代码和实验会越来越乱。

```
hiroute/
  README.md
  docs/
    paper_mapping.md
    dataset_design.md
    experiment_matrix.md
  data/
    raw/
      smartdatamodels/
      seeds/
    interim/
      objects/
      queries/
      embeddings/
      hierarchy/
    processed/
      ndnsim/
      eval/
  scripts/
    download/
    preprocess/
    build_dataset/
    eval/
    plots/
  ndnsim/
    apps/
    model/
    helper/
    scenarios/
  configs/
    dataset/
    hierarchy/
    experiments/
    baselines/
  results/
    runs/
    aggregate/
    figures/
```

------

# 二、按论文逐节对应的 ndnSIM 实现与实验任务表

## 2.1 Introduction 与 Background 对应什么实现

这两节不是代码节，但它们决定你必须真的实现三件事。

第一件事是名字异构。也就是说，同一语义类对象必须来自不同命名模板，而不是全网同一种 canonical naming。

第二件事是硬约束。query 里必须显式有 zone、service class、freshness 这些字段，否则你论文里“constraint-guided”这条主线是空的。

第三件事是 object-level relevance。你不能只评 domain recall，必须评最终对象是否正确。

因此，从实现角度，这两节对应三份数据文件和两个最早必须做出来的脚本：

`objects_master.csv`
 `queries_master.csv`
 `qrels_object.csv`

以及：

`build_objects.py`
 `build_queries_and_qrels.py`

------

## 2.2 System Model and Design Rationale 对应什么实现

这一节对应的是“数据结构定义”。

你需要先把系统里的最小实体全定义出来。推荐直接按下面的类拆。

### 2.2.1 数据模型类

在 `ndnsim/model/` 下增加：

`hiroute-object-record.hpp/.cpp`
 类名：`HiRouteObjectRecord`

字段：

- objectId
- domainId
- zoneId
- zoneType
- serviceClass
- freshnessClass
- vendorTemplateId
- canonicalName
- embeddingIndex
- producerNodeId
- controllerNodeId
- payloadSize
- objectVersion

`hiroute-query-record.hpp/.cpp`
 类名：`HiRouteQueryRecord`

字段：

- queryId
- ingressNodeId
- startTimeMs
- zoneConstraint
- zoneTypeConstraint
- serviceConstraint
- freshnessConstraint
- ambiguityLevel
- semanticIntentText
- embeddingIndex
- groundTruthCount

`hiroute-manifest-entry.hpp/.cpp`
 类名：`HiRouteManifestEntry`

字段：

- canonicalName
- confidenceScore
- domainId
- cellId
- objectId

------

## 2.3 HiRoute Design 对应什么实现

这是主系统。

### 2.3.1 你要新增的核心模块

在 `ndnsim/apps/` 下新增：

`hiroute-ingress-app.hpp/.cpp`
 类名：`HiRouteIngressApp`

职责：

- 读取 query trace
- 构造 discovery Interest
- 执行 predicate filtering
- 本地 frontier 管理
- 处理 discovery reply
- 发起 manifest fetch
- 记录 end-to-end query log

`hiroute-controller-app.hpp/.cpp`
 类名：`HiRouteControllerApp`

职责：

- 加载本域 hierarchy 和 object index
- 接收 discovery query
- 按 predicate 先筛
- 在目标 cell 内做 local search
- 返回 top-r manifest

在 `ndnsim/model/` 下新增：

`hiroute-summary-store.hpp/.cpp`
 类名：`HiRouteSummaryStore`

职责：

- 保存全网收到的 HS-LSA
- 提供按 predicate 的 admissibility filter
- 提供按 parent/child 组织的 hierarchy lookup

`hiroute-summary-entry.hpp/.cpp`
 类名：`HiRouteSummaryEntry`

字段：

- domainId
- level
- cellId
- parentId
- zoneBitmap
- serviceBitmap
- freshnessBitmap
- centroidVector
- radius
- count
- controllerPrefix
- version
- ttl

`hiroute-discovery-engine.hpp/.cpp`
 类名：`HiRouteDiscoveryEngine`

职责：

- 对 admissible cells 打分
- best-first frontier refinement
- margin-based stopping
- budget control

`hiroute-reliability-cache.hpp/.cpp`
 类名：`HiRouteReliabilityCache`

职责：

- `(domainId, cellId)` 级别 EWMA success
- negative cache
- cooldown / retry window

`hiroute-tlv.hpp/.cpp`
 职责：

- 自定义 discovery payload 的 TLV 编解码
- manifest reply TLV 编解码

------

## 2.4 Protocol 部分怎么落地

### 2.4.1 Discovery Interest 的名字和参数

名字建议固定成：

```
/hiroute/discovery/<query-id>/<epoch>
```

真正的 query 信息不放在名字主体里，放在 `ApplicationParameters` 中，包括：

- queryId
- queryEmbeddingRow
- zoneConstraint
- zoneTypeConstraint
- serviceConstraint
- freshnessConstraint
- refinementBudget
- requestedManifestSize
- frontierHintCellId（可选）

这样做的原因是你论文主张“data plane unchanged”。标准 NDN 转发仍看 prefix，语义只在 discovery plane 内部解释。

### 2.4.2 HS-LSA 的加载方式

第一版不需要做全分布式动态注入。直接在 scenario 启动时由每个 ingress 预加载 `hslsa_export.csv`，再在 failure/staleness 实验里按时间更新即可。

也就是说你前期不必先把“LSA flooding protocol”写复杂。先把静态载入和按时间替换做出来。

------

## 2.5 ndnSIM Realization 章节对应什么 scenario

在 `ndnsim/scenarios/` 下至少准备五个 scenario：

`hiroute-main.cc`
 主实验，跑 success、latency、overhead。

`hiroute-state-scaling.cc`
 调 objects/domain 和 domains 数量。

`hiroute-staleness.cc`
 控制 summary refresh interval 和 drift ratio。

`hiroute-link-failure.cc`
 控制链路 down/up。

`hiroute-domain-failure.cc`
 控制 controller 或 domain disable。

------

## 2.6 Performance Evaluation 每张图要产什么 CSV

下面这部分最重要。你以后画图就照着这些 CSV 字段聚合，不要临时补日志。

### Figure 1：系统架构图

这是手工图，不靠 CSV。

推荐图名：
 `fig_architecture_overview.pdf`

------

### Figure 2：query decomposition 与 hierarchy refinement

也是手工图。

推荐图名：
 `fig_query_pipeline.pdf`

------

### Figure 3：packet / HS-LSA format

也是手工图。

推荐图名：
 `fig_packet_formats.pdf`

------

### Figure 4：主结果，ServiceSuccess vs Discovery Overhead

输入 CSV：
 `results/runs/<exp>/query_log.csv`

精确列名：

- query_id
- scheme
- seed
- topology_id
- dataset_id
- start_time_ms
- end_time_ms
- latency_ms
- success_at_1
- manifest_hit_at_3
- manifest_hit_at_5
- ndcg_at_5
- final_object_id
- final_domain_id
- final_cell_id
- num_remote_probes
- discovery_tx_bytes
- discovery_rx_bytes
- fetch_tx_bytes
- fetch_rx_bytes
- failure_type

聚合方式：
 按 `scheme` 和 `budget` 聚合：

- mean(success_at_1)
- mean(manifest_hit_at_5)
- mean(ndcg_at_5)
- mean(num_remote_probes)
- mean(discovery_tx_bytes + discovery_rx_bytes)

输出图：
 `fig_main_success_overhead.pdf`

------

### Figure 5：failure decomposition

还是用 `query_log.csv`。

`failure_type` 必须统一枚举：

- predicate_miss
- wrong_domain
- wrong_object
- fetch_timeout
- no_reply
- success

输出图：
 `fig_failure_waterfall.pdf`

------

### Figure 6：candidate shrinkage

需要单独日志：

```
results/runs/<exp>/search_trace.csv
```

列名：

- query_id
- scheme
- stage
- candidate_count
- selected_count
- frontier_size
- timestamp_ms

其中 `stage` 枚举：

- all_domains
- predicate_filtered_domains
- level0_cells
- level1_cells
- refined_cells
- probed_cells
- manifest_candidates

输出图：
 `fig_candidate_shrinkage.pdf`

------

### Figure 7：deadline-sensitive latency

输入还是 `query_log.csv`。

额外聚合生成：

```
results/aggregate/deadline_summary.csv
```

列名：

- scheme
- deadline_ms
- success_within_deadline
- mean_latency_success_only
- p50_latency_success_only
- p95_latency_success_only

输出图：
 `fig_deadline_latency.pdf`

------

### Figure 8：state scaling

输入：

```
results/runs/<exp>/state_log.csv
```

列名：

- timestamp_ms
- scheme
- domain_id
- num_exported_summaries
- exported_summary_bytes
- summary_updates_sent
- objects_in_domain
- domains_total
- budget

输出图：
 `fig_state_scaling.pdf`

------

### Figure 9：robustness

输入：

`failure_event_log.csv` 和 `query_log.csv`

`failure_event_log.csv` 列名：

- event_id
- scheme
- event_type
- target_type
- target_id
- inject_time_ms
- recover_time_ms

`event_type` 枚举：

- link_down
- controller_down
- summary_stale
- summary_refresh

输出图：
 `fig_robustness.pdf`

------

### Figure 10：ablation

输入：
 多组 `query_log.csv` 合并后的 summary。

新增 `ablation_scheme`：

- predicates_only
- flat_semantic_only
- predicates_plus_flat
- full_hiroute

输出图：
 `fig_ablation.pdf`

------

# 三、baseline 该怎么落地

## 3.1 Exact-NDN

这个 baseline 不是 interoperability baseline，而是 retrieval 下界。

实现方式：
 consumer trace 里额外给一列 `oracle_canonical_name`。
 consumer 直接对这个名字发标准 Interest。
 不经过 discovery。

代码层面：
 `ExactFetchConsumerApp`

你甚至可以不单独写类，直接复用现有 consumer app。

------

## 3.2 Flood

实现方式：
 ingress 接到 query 后，把 discovery Interest 发给所有 domain controller，或者限制在区域范围内的所有 controller。

推荐单独写：

```
flood-discovery-app.hpp/.cpp
```

它不做 hierarchy 和 predicate filtering，只做：

- 广播或 fan-out
- 收 controller reply
- 合并最优 manifest

为了公平，必须给：

- max_probe_budget
- max_reply_wait_ms

------

## 3.3 Flat iRoute

这是你最重要的 baseline。

实现方式：

- 每个 domain 只导出 flat domain summaries
- 不做 hierarchy
- 可以做 top-k domain selection
- controller 只返回 single answer 或 top-r manifest，二选一
- 更建议保持旧 iRoute 风格，single answer，更能体现新系统进步

类：
 `flat-semantic-summary-store.hpp/.cpp`
 `flat-semantic-ingress-app.hpp/.cpp`

------

## 3.4 Central Oracle

实现方式：
 单一 `OracleControllerApp` 持有全局 object index 和 qrels-compatible ranking。

收到 query 后直接返回 top-r manifest。

注意：

- 不要把它作为现实系统
- 它只是上界

------

## 3.5 Tag baseline

如果你已有 tag route 代码，就保留。
 如果没有，不建议现在临时再发明一个全新 tag 系统。
 在论文里保留四个 baseline 已经足够。

------

# 四、数据生成脚本设计文档

下面是完整的数据管线。核心思想是：用 Smart Data Models 的官方 smart city data models 作为 schema 和语义原型，然后生成适合 NDN-IoT resolution 的对象、query 和 qrels。Smart Data Models 官方说明其模型公开可用，且 SmartCities 仓库包含 Parking、Streetlighting、Transportation、UrbanMobility、Weather 等主题，非常适合作为你的 service classes 来源。

## 4.1 下载什么数据

你不需要依赖一个单一“现成带 query 的数据集”。
 你需要下载的是“官方数据模型和示例”，再用它们生成你的实验对象库。

### 4.1.1 官方下载源

推荐两个源：

1. Smart Data Models GitHub 组织
2. SmartCities 仓库 和 umbrella `data-models` 仓库

下载命令：

```
mkdir -p data/raw/smartdatamodels
cd data/raw/smartdatamodels

git clone https://github.com/smart-data-models/SmartCities.git
git clone https://github.com/smart-data-models/data-models.git
```

这些仓库分别提供 Smart Cities 主题模型和总目录/官方模型列表。

### 4.1.2 你要优先使用的主题

从 SmartCities 中抽取这些 subject：

- Weather
- Parking
- UrbanMobility
- Transportation
- Streetlighting
- ParksAndGardens 或 PointOfInterest 只做 zone/POI 辅助

为什么这样选。因为它们能自然映射到：

- temperature / humidity / rainfall
- parking availability
- bus arrival / traffic mobility
- street light status

而且这些都属于 Smart Cities 公开主题。

------

## 4.2 数据处理总流程

### 阶段 A：下载与扫描

脚本：
 `scripts/download/download_smartdatamodels.sh`

职责：

- 克隆上述仓库
- 记录 commit hash
- 生成 `raw_manifest.json`

------

### 阶段 B：提取 schema 和 examples

脚本：
 `scripts/preprocess/extract_sdm_subjects.py`

输入：

- `data/raw/smartdatamodels/SmartCities`
- `data/raw/smartdatamodels/data-models`

输出：

- `data/interim/objects/sdm_subject_catalog.csv`
- `data/interim/objects/sdm_examples_normalized.jsonl`

`sdm_subject_catalog.csv` 列名：

- source_repo
- subject_name
- schema_path
- example_path
- entity_type
- domain_group

------

### 阶段 C：生成 service ontology

脚本：
 `scripts/preprocess/build_service_ontology.py`

作用：
 把官方 subject 和 example property 映射成你的论文 service classes。

输出：
 `data/interim/objects/service_ontology.csv`

列名：

- service_class
- source_subject
- entity_type
- primary_property
- unit
- value_type
- template_group

示例：

- temperature ← Weather
- parking_availability ← Parking
- bus_arrival ← UrbanMobility / Transportation
- street_light_state ← Streetlighting

------

### 阶段 D：生成对象库

脚本：
 `scripts/build_dataset/build_objects.py`

输入：

- `service_ontology.csv`
- `configs/dataset/object_generation.yaml`

输出：

- `data/processed/ndnsim/objects_master.csv`
- `data/processed/ndnsim/object_texts.jsonl`

`objects_master.csv` 精确列名：

- object_id
- domain_id
- zone_id
- zone_type
- service_class
- freshness_class
- time_bucket
- vendor_template_id
- canonical_name
- producer_node_id
- controller_node_id
- payload_size_bytes
- unit
- value_type
- object_version
- object_text_id

`object_texts.jsonl` 字段：

- object_text_id
- object_id
- description_text
- keywords
- metadata_summary

------

### 阶段 E：生成 query 与 qrels

脚本：
 `scripts/build_dataset/build_queries_and_qrels.py`

输入：

- `objects_master.csv`
- `object_texts.jsonl`
- `configs/dataset/query_generation.yaml`

输出：

- `data/processed/ndnsim/queries_master.csv`
- `data/processed/eval/qrels_object.csv`
- `data/processed/eval/qrels_domain.csv`

`queries_master.csv` 精确列名：

- query_id
- split
- ingress_node_id
- start_time_ms
- query_text
- zone_constraint
- zone_type_constraint
- service_constraint
- freshness_constraint
- ambiguity_level
- difficulty
- intended_domain_count
- query_text_id

`qrels_object.csv` 列名：

- query_id
- object_id
- relevance

`qrels_domain.csv` 列名：

- query_id
- domain_id
- is_relevant_domain

------

### 阶段 F：做 embedding

脚本：
 `scripts/build_dataset/embed_texts.py`

输入：

- `object_texts.jsonl`
- `queries_master.csv`

输出：

- `data/processed/ndnsim/object_embeddings.npy`
- `data/processed/ndnsim/query_embeddings.npy`
- `data/processed/ndnsim/object_embedding_index.csv`
- `data/processed/ndnsim/query_embedding_index.csv`

`object_embedding_index.csv`：

- object_id
- embedding_row

`query_embedding_index.csv`：

- query_id
- embedding_row

------

### 阶段 G：构建 hierarchy 和 HS-LSA

脚本：
 `scripts/build_dataset/build_hierarchy_and_hslsa.py`

输入：

- `objects_master.csv`
- `object_embeddings.npy`
- `configs/hierarchy/hiroute_hierarchy.yaml`

输出：

- `data/processed/ndnsim/hslsa_export.csv`
- `data/processed/ndnsim/controller_local_index.csv`
- `data/processed/ndnsim/cell_membership.csv`

`hslsa_export.csv` 精确列名：

- domain_id
- level
- cell_id
- parent_id
- zone_bitmap
- zone_type_bitmap
- service_bitmap
- freshness_bitmap
- centroid_row
- radius
- object_count
- controller_prefix
- version
- ttl_ms
- export_budget

`controller_local_index.csv` 列名：

- domain_id
- cell_id
- object_id
- local_rank_hint

`cell_membership.csv` 列名：

- object_id
- domain_id
- level0_cell
- level1_cell
- level2_cell

------

### 阶段 H：映射到 ndnSIM topology

脚本：
 `scripts/build_dataset/build_topology_mapping.py`

输出：

- `data/processed/ndnsim/topology_mapping.csv`

列名：

- node_id
- role
- domain_id
- zone_id
- controller_prefix
- producer_count

------

# 五、推荐配置文件

## 5.1 `configs/dataset/object_generation.yaml`

```
seed: 42
domains_total: 16
zones_per_domain: 4
objects_per_service_per_zone: 20
service_classes:
  - temperature
  - humidity
  - rainfall
  - air_quality_pm25
  - air_quality_co2
  - traffic_speed
  - parking_availability
  - bus_arrival
  - street_light_state
  - noise_level
zone_types:
  - school_area
  - residential
  - downtown
  - industrial
  - transport_hub
  - stadium_area
freshness_classes:
  realtime: 5000
  recent: 60000
  archival: 600000
naming_templates_per_domain: 4
```

## 5.2 `configs/dataset/query_generation.yaml`

```
seed: 43
queries_total: 3000
template_ratio: 0.4
paraphrase_ratio: 0.4
ambiguous_ratio: 0.2
max_relevance_grade_2: 3
max_relevance_grade_1: 8
splits:
  dev: 0.2
  test: 0.8
```

## 5.3 `configs/hierarchy/hiroute_hierarchy.yaml`

```
seed: 44
level0: domain
level1_partition:
  keys:
    - zone_id
    - service_class
    - freshness_class
semantic_microclusters_per_predicate_cell: 6
export_budgets:
  - 8
  - 16
  - 32
  - 64
radius_metric: cosine
```

------

# 六、每个脚本该干什么

## 6.1 `download_smartdatamodels.sh`

职责：

- clone 两个仓库
- 写 commit id
- 生成下载清单

## 6.2 `extract_sdm_subjects.py`

职责：

- 扫描 SmartCities subject 目录
- 找 schema.json、README、examples
- 建索引

## 6.3 `build_service_ontology.py`

职责：

- 把官方 subject/property 转成你的 service_class 词表
- 定义每类对象的 unit/value_type/template_group

## 6.4 `build_objects.py`

职责：

- 按域、zone、service class 生成对象
- 随机选择 naming template
- 生成 canonical_name
- 生成 object_text

## 6.5 `build_queries_and_qrels.py`

职责：

- 生成三类 query
- 自动打 object-level qrels
- 自动打 domain-level qrels

## 6.6 `embed_texts.py`

职责：

- object 和 query 文本嵌入
- 写 numpy 和 index CSV

## 6.7 `build_hierarchy_and_hslsa.py`

职责：

- predicate cell 分桶
- 每桶做 balanced k-means
- 导出 HS-LSA
- 导出 controller local index

## 6.8 `build_topology_mapping.py`

职责：

- 按 domain 给 topology 分配 node role
- 指定 ingress / controller / producer

## 6.9 `aggregate_query_metrics.py`

职责：

- 聚合 query_log
- 输出 main figure summary

## 6.10 `plot_main_figures.py`

职责：

- 从 aggregate CSV 出图

------

# 七、给 Codex 的逐文件实现 prompt

下面这些 prompt 你可以逐个丢给 Codex。它们是按依赖顺序排的。

## Prompt 1：下载与索引官方 smart city models

```
You are working in the hiroute repository.

Task:
Create the dataset download and indexing pipeline for official Smart Data Models sources.

Requirements:
1. Add a shell script at scripts/download/download_smartdatamodels.sh.
2. The script must:
   - create data/raw/smartdatamodels
   - clone https://github.com/smart-data-models/SmartCities.git if missing
   - clone https://github.com/smart-data-models/data-models.git if missing
   - record git commit hashes into data/raw/smartdatamodels/raw_manifest.json
3. Add a Python script at scripts/preprocess/extract_sdm_subjects.py.
4. The script must:
   - scan the cloned repos
   - identify subject folders relevant to Smart Cities
   - detect schema.json, README and example-like files where available
   - write data/interim/objects/sdm_subject_catalog.csv with columns:
     source_repo,subject_name,schema_path,example_path,entity_type,domain_group
5. Make the script robust to missing example files.
6. Add argparse, logging, and docstrings.
7. Add a short README section in docs/dataset_design.md explaining how to run the downloader and extractor.
8. Do not use notebooks.

Return:
- all created files
- exact run commands
- a short summary of assumptions
```

## Prompt 2：service ontology 映射

```
You are working in the hiroute repository.

Task:
Implement the service ontology builder that maps Smart Data Models subjects into HiRoute service classes.

Files to add:
- scripts/preprocess/build_service_ontology.py
- configs/dataset/service_ontology_rules.yaml

Requirements:
1. Read data/interim/objects/sdm_subject_catalog.csv.
2. Map official smart-city subjects into these service classes:
   temperature, humidity, rainfall, air_quality_pm25, air_quality_co2,
   traffic_speed, parking_availability, bus_arrival, street_light_state, noise_level
3. Output data/interim/objects/service_ontology.csv with columns:
   service_class,source_subject,entity_type,primary_property,unit,value_type,template_group
4. The YAML rules file must make the mapping editable without changing code.
5. Add validation to ensure every configured service class appears at least once.
6. Add logging and docstrings.
7. Update docs/dataset_design.md with the ontology-generation step.
```

## Prompt 3：对象库生成器

```
You are working in the hiroute repository.

Task:
Implement the synthetic smart-city object generator for HiRoute.

Files to add:
- scripts/build_dataset/build_objects.py
- configs/dataset/object_generation.yaml

Requirements:
1. Read service_ontology.csv.
2. Generate objects_master.csv at data/processed/ndnsim/objects_master.csv with columns:
   object_id,domain_id,zone_id,zone_type,service_class,freshness_class,time_bucket,
   vendor_template_id,canonical_name,producer_node_id,controller_node_id,
   payload_size_bytes,unit,value_type,object_version,object_text_id
3. Generate object_texts.jsonl at data/processed/ndnsim/object_texts.jsonl with fields:
   object_text_id,object_id,description_text,keywords,metadata_summary
4. Support multiple naming templates per domain to create naming heterogeneity.
5. Support domain semantic bias and zone-type bias from YAML config.
6. Use deterministic randomness from a seed.
7. Add data validation and a --preview mode.
8. Write clean modular code, no notebooks.
```

## Prompt 4：query 与 qrels 生成器

```
You are working in the hiroute repository.

Task:
Implement query generation and qrels generation for HiRoute.

Files to add:
- scripts/build_dataset/build_queries_and_qrels.py
- configs/dataset/query_generation.yaml

Requirements:
1. Read objects_master.csv and object_texts.jsonl.
2. Generate queries_master.csv with columns:
   query_id,split,ingress_node_id,start_time_ms,query_text,
   zone_constraint,zone_type_constraint,service_constraint,
   freshness_constraint,ambiguity_level,difficulty,intended_domain_count,query_text_id
3. Generate qrels_object.csv with columns:
   query_id,object_id,relevance
4. Generate qrels_domain.csv with columns:
   query_id,domain_id,is_relevant_domain
5. Support three query families:
   - precise template queries
   - paraphrase queries
   - ambiguous queries
6. Relevance must be object-level and use grades 0,1,2.
7. Domain qrels must be derived from the relevant objects.
8. Add stats output summarizing query distribution and relevance density.
```

## Prompt 5：embedding 管线

```
You are working in the hiroute repository.

Task:
Implement offline embedding generation for objects and queries.

Files to add:
- scripts/build_dataset/embed_texts.py

Requirements:
1. Read object_texts.jsonl and queries_master.csv.
2. Output:
   - data/processed/ndnsim/object_embeddings.npy
   - data/processed/ndnsim/query_embeddings.npy
   - data/processed/ndnsim/object_embedding_index.csv
   - data/processed/ndnsim/query_embedding_index.csv
3. Support a pluggable sentence-transformers model name from CLI.
4. Use batching and deterministic ordering.
5. Save float32 arrays.
6. Add validation to ensure every object_id and query_id has exactly one embedding row.
7. Update docs/dataset_design.md with run instructions.
```

## Prompt 6：层次目录与 HS-LSA

```
You are working in the hiroute repository.

Task:
Implement constrained hierarchy construction and HS-LSA export.

Files to add:
- scripts/build_dataset/build_hierarchy_and_hslsa.py
- configs/hierarchy/hiroute_hierarchy.yaml

Requirements:
1. Read objects_master.csv and object_embeddings.npy.
2. Build a 3-level hierarchy:
   - level 0: domain
   - level 1: predicate cells partitioned by zone_id, service_class, freshness_class
   - level 2: semantic microclusters inside each predicate cell
3. Export hslsa_export.csv with columns:
   domain_id,level,cell_id,parent_id,zone_bitmap,zone_type_bitmap,
   service_bitmap,freshness_bitmap,centroid_row,radius,object_count,
   controller_prefix,version,ttl_ms,export_budget
4. Export controller_local_index.csv with columns:
   domain_id,cell_id,object_id,local_rank_hint
5. Export cell_membership.csv with columns:
   object_id,domain_id,level0_cell,level1_cell,level2_cell
6. Support export budgets 8,16,32,64.
7. Use balanced clustering where possible and document fallback behavior.
8. Add validation so no object is dropped.
```

## Prompt 7：topology mapping

```
You are working in the hiroute repository.

Task:
Implement topology-to-domain mapping for ndnSIM scenarios.

Files to add:
- scripts/build_dataset/build_topology_mapping.py

Requirements:
1. Read a simple topology inventory file or config.
2. Assign roles:
   ingress, controller, producer, relay
3. Output topology_mapping.csv with columns:
   node_id,role,domain_id,zone_id,controller_prefix,producer_count
4. Ensure each domain has exactly one controller and at least one producer.
5. Ensure ingress nodes are distributed across domains or access regions.
6. Add a validation report.
```

## Prompt 8：HiRoute C++ 数据模型与 TLV

```
You are working in the hiroute repository ndnSIM codebase.

Task:
Add the core C++ data model and TLV support for HiRoute.

Files to add:
- ndnsim/model/hiroute-object-record.hpp/.cpp
- ndnsim/model/hiroute-query-record.hpp/.cpp
- ndnsim/model/hiroute-manifest-entry.hpp/.cpp
- ndnsim/model/hiroute-summary-entry.hpp/.cpp
- ndnsim/model/hiroute-tlv.hpp/.cpp

Requirements:
1. Implement plain data classes with getters/setters and serialization helpers where appropriate.
2. Implement TLV encode/decode helpers for:
   - predicate header
   - embedding row reference or vector payload
   - manifest entries
   - refinement budget
3. Keep the implementation simple and ndn-cxx compatible.
4. Add comments documenting wire fields clearly.
5. Provide a small unit-test-like demo if a test framework is available; otherwise provide a compile-only sanity helper.
```

## Prompt 9：SummaryStore 和 DiscoveryEngine

```
You are working in the hiroute repository ndnSIM codebase.

Task:
Implement the HiRoute summary store and discovery engine.

Files to add:
- ndnsim/model/hiroute-summary-store.hpp/.cpp
- ndnsim/model/hiroute-discovery-engine.hpp/.cpp
- ndnsim/model/hiroute-reliability-cache.hpp/.cpp

Requirements:
1. SummaryStore must load hslsa_export.csv and provide:
   - lookup by domain
   - lookup by parent cell
   - predicate admissibility filtering
2. DiscoveryEngine must:
   - compute score = alpha*semantic + beta*predicate + gamma*reliability - delta*cost
   - manage a best-first frontier
   - stop on budget or margin threshold
3. ReliabilityCache must:
   - store EWMA success by (domain_id, cell_id)
   - store negative cache entries with TTL
4. Expose logs needed for search_trace.csv.
5. Make all weights configurable from scenario parameters.
```

## Prompt 10：Ingress 与 Controller App

```
You are working in the hiroute repository ndnSIM codebase.

Task:
Implement the main HiRoute apps.

Files to add:
- ndnsim/apps/hiroute-ingress-app.hpp/.cpp
- ndnsim/apps/hiroute-controller-app.hpp/.cpp

Requirements:
1. HiRouteIngressApp must:
   - read queries_master.csv and query_embedding_index.csv
   - build discovery Interests under /hiroute/discovery/<query-id>/<epoch>
   - run predicate filtering and hierarchical refinement using DiscoveryEngine
   - send controller probes
   - receive manifests
   - fetch the first canonical name, optionally fallback to later manifest entries
   - write query_log.csv and probe_log.csv
2. HiRouteControllerApp must:
   - load controller_local_index.csv and object embedding references
   - answer discovery Interests by ranking local objects inside the targeted cell or neighboring cells
   - return top-r manifest entries
3. Keep the data plane standard for final fetches.
4. Add clear logging and config options.
```

## Prompt 11：baselines

```
You are working in the hiroute repository ndnSIM codebase.

Task:
Implement the main baselines for HiRoute evaluation.

Files to add:
- ndnsim/apps/flood-discovery-app.hpp/.cpp
- ndnsim/apps/flat-semantic-ingress-app.hpp/.cpp
- ndnsim/apps/oracle-controller-app.hpp/.cpp

Requirements:
1. Flood baseline:
   - fan out discovery to all controllers or all admissible region controllers
   - bounded by max_probe_budget and max_reply_wait_ms
2. Flat semantic baseline:
   - use one-level domain summaries only
   - no hierarchy
   - top-k domain probing
3. Oracle baseline:
   - hold a global object index
   - return top-r manifest directly
4. Reuse logging schema so all baselines emit compatible query_log.csv and probe_log.csv.
5. Do not change the final fetch path.
```

## Prompt 12：scenarios 与聚合脚本

```
You are working in the hiroute repository.

Task:
Add scenarios and evaluation scripts for the HiRoute paper figures.

Files to add:
- ndnsim/scenarios/hiroute-main.cc
- ndnsim/scenarios/hiroute-state-scaling.cc
- ndnsim/scenarios/hiroute-staleness.cc
- ndnsim/scenarios/hiroute-link-failure.cc
- ndnsim/scenarios/hiroute-domain-failure.cc
- scripts/eval/aggregate_query_metrics.py
- scripts/eval/build_deadline_summary.py
- scripts/plots/plot_main_figures.py

Requirements:
1. Scenarios must emit:
   - query_log.csv
   - probe_log.csv
   - search_trace.csv
   - state_log.csv
   - failure_event_log.csv where relevant
2. Aggregation scripts must build:
   - main_success_overhead.csv
   - deadline_summary.csv
   - state_scaling_summary.csv
   - failure_breakdown.csv
   - ablation_summary.csv
3. Plotting script must generate:
   - fig_main_success_overhead.pdf
   - fig_failure_waterfall.pdf
   - fig_candidate_shrinkage.pdf
   - fig_deadline_latency.pdf
   - fig_state_scaling.pdf
   - fig_robustness.pdf
   - fig_ablation.pdf
4. Use consistent CLI arguments and output directories.
```

------

# 八、实施顺序

最稳的顺序只有一个。

先把数据管线跑通。
 再把 Exact-NDN 和 Oracle 跑通。
 再做 Flat iRoute。
 最后做 HiRoute。

也就是：

第 1 周，Prompt 1 到 Prompt 6。
 第 2 周，Prompt 7 到 Prompt 9。
 第 3 周，Prompt 10 到 Prompt 12。
 第 4 周，先跑 Exact / Oracle / Flat。
 第 5 周，跑 HiRoute 主实验。
 第 6 周，跑 staleness / failure / ablation。

这样你最早在第 4 周就能知道论文有没有戏，而不是把所有复杂模块都写完才发现数据或评估有问题。