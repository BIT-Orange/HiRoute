/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "hiroute-ingress-app.hpp"

#include "ns3/log.h"
#include "ns3/nstime.h"
#include "ns3/string.h"
#include "ns3/uinteger.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <stdexcept>

NS_LOG_COMPONENT_DEFINE("ndn.HiRouteIngressApp");

namespace ns3 {
namespace ndn {
namespace hiroute {

NS_OBJECT_ENSURE_REGISTERED(HiRouteIngressApp);

namespace {

bool
fileNeedsHeader(const std::string& path)
{
  std::ifstream input(path.c_str());
  return !input.good() || input.peek() == std::ifstream::traits_type::eof();
}

std::string
escapeCsv(std::string value)
{
  bool needsQuotes = false;
  for (char ch : value) {
    if (ch == ',' || ch == '"' || ch == '\n' || ch == '\r') {
      needsQuotes = true;
      break;
    }
  }
  if (!needsQuotes) {
    return value;
  }

  std::string escaped;
  escaped.reserve(value.size() + 4);
  escaped.push_back('"');
  for (char ch : value) {
    if (ch == '"') {
      escaped.push_back('"');
    }
    escaped.push_back(ch);
  }
  escaped.push_back('"');
  return escaped;
}

} // namespace

TypeId
HiRouteIngressApp::GetTypeId()
{
  static TypeId tid =
    TypeId("ns3::ndn::HiRouteIngressApp")
      .SetGroupName("Ndn")
      .SetParent<App>()
      .AddConstructor<HiRouteIngressApp>()
      .AddAttribute("QueryCsvPath", "Path to queries_master.csv",
                    StringValue("../data/processed/ndnsim/queries_master.csv"),
                    MakeStringAccessor(&HiRouteIngressApp::m_queryCsvPath), MakeStringChecker())
      .AddAttribute("QueryEmbeddingIndexCsvPath", "Path to query_embedding_index.csv",
                    StringValue("../data/processed/ndnsim/query_embedding_index.csv"),
                    MakeStringAccessor(&HiRouteIngressApp::m_queryEmbeddingIndexCsvPath),
                    MakeStringChecker())
      .AddAttribute("QrelsObjectCsvPath", "Path to qrels_object.csv",
                    StringValue("../data/processed/eval/qrels_object.csv"),
                    MakeStringAccessor(&HiRouteIngressApp::m_qrelsObjectCsvPath),
                    MakeStringChecker())
      .AddAttribute("ObjectsCsvPath", "Path to objects_master.csv",
                    StringValue("../data/processed/ndnsim/objects_master.csv"),
                    MakeStringAccessor(&HiRouteIngressApp::m_objectsCsvPath), MakeStringChecker())
      .AddAttribute("SummaryCsvPath", "Path to hslsa_export.csv",
                    StringValue("../data/processed/ndnsim/hslsa_export.csv"),
                    MakeStringAccessor(&HiRouteIngressApp::m_summaryCsvPath), MakeStringChecker())
      .AddAttribute("RunDirectory", "Directory where query/probe/search logs are written",
                    StringValue("../runs/pending/ingress-smoke"),
                    MakeStringAccessor(&HiRouteIngressApp::m_runDirectory), MakeStringChecker())
      .AddAttribute("IngressNodeFilter", "Only schedule queries whose ingress_node_id matches this value",
                    StringValue(""),
                    MakeStringAccessor(&HiRouteIngressApp::m_ingressNodeFilter),
                    MakeStringChecker())
      .AddAttribute("StrategyMode",
                    "exact, flood, flat, hiroute, oracle, inf_tag_forwarding, predicates_only, flat_semantic_only, predicates_plus_flat, or full_hiroute",
                    StringValue("hiroute"),
                    MakeStringAccessor(&HiRouteIngressApp::m_strategyMode), MakeStringChecker())
      .AddAttribute("OraclePrefix", "Discovery prefix used by the oracle baseline",
                    StringValue("/hiroute/oracle/controller"),
                    MakeStringAccessor(&HiRouteIngressApp::m_oraclePrefix), MakeStringChecker())
      .AddAttribute("MaxProbeBudget", "Maximum number of remote controller probes per query",
                    UintegerValue(4),
                    MakeUintegerAccessor(&HiRouteIngressApp::m_maxProbeBudget),
                    MakeUintegerChecker<uint32_t>())
      .AddAttribute("RequestedManifestSize", "Maximum manifest size requested from controllers",
                    UintegerValue(4),
                    MakeUintegerAccessor(&HiRouteIngressApp::m_requestedManifestSize),
                    MakeUintegerChecker<uint32_t>())
      .AddAttribute("QueryLimit", "Limit the number of scheduled queries (0 means all)",
                    UintegerValue(0),
                    MakeUintegerAccessor(&HiRouteIngressApp::m_queryLimit),
                    MakeUintegerChecker<uint32_t>())
      .AddAttribute("QueryStartDelay", "Delay before scheduling the first query",
                    StringValue("100ms"),
                    MakeTimeAccessor(&HiRouteIngressApp::m_queryStartDelay), MakeTimeChecker())
      .AddAttribute("ReplyTimeout", "Timeout for discovery or fetch reply",
                    StringValue("200ms"),
                    MakeTimeAccessor(&HiRouteIngressApp::m_replyTimeout), MakeTimeChecker());
  return tid;
}

HiRouteIngressApp::HiRouteIngressApp()
  : m_rand(CreateObject<UniformRandomVariable>())
{
}

void
HiRouteIngressApp::StartApplication()
{
  App::StartApplication();
  loadInputs();
  openLogs();
  scheduleNextQuery(m_queryStartDelay);
}

void
HiRouteIngressApp::StopApplication()
{
  if (m_activeQuery.timeoutEvent.IsRunning()) {
    m_activeQuery.timeoutEvent.Cancel();
  }
  if (m_queryLog.is_open()) {
    m_queryLog.close();
  }
  if (m_probeLog.is_open()) {
    m_probeLog.close();
  }
  if (m_searchTraceLog.is_open()) {
    m_searchTraceLog.close();
  }
  App::StopApplication();
}

void
HiRouteIngressApp::SetStrategyMode(const std::string& strategyMode)
{
  m_strategyMode = strategyMode;
}

void
HiRouteIngressApp::OnData(shared_ptr<const Data> data)
{
  if (!m_active || !m_activeQuery.active) {
    return;
  }

  App::OnData(data);
  const auto name = data->getName().toUri();
  if (name.find("/discovery/") != std::string::npos) {
    handleDiscoveryReply(data);
  }
  else {
    handleFetchReply(data);
  }
}

void
HiRouteIngressApp::OnNack(shared_ptr<const lp::Nack> nack)
{
  App::OnNack(nack);
  onPhaseTimeout();
}

void
HiRouteIngressApp::loadInputs()
{
  m_summaryStore.LoadFromCsv(m_summaryCsvPath);

  std::map<std::string, uint32_t> queryEmbeddingRows;
  for (const auto& row : HiRouteDatasetReader::ReadCsvRows(m_queryEmbeddingIndexCsvPath)) {
    queryEmbeddingRows[GetFieldOrEmpty(row, "query_id")] =
      static_cast<uint32_t>(std::strtoul(GetFieldOrEmpty(row, "embedding_row").c_str(), nullptr, 10));
  }

  m_queries.clear();
  for (const auto& row : HiRouteDatasetReader::ReadCsvRows(m_queryCsvPath)) {
    auto query = HiRouteQueryRecord::FromCsvRow(row);
    if (!m_ingressNodeFilter.empty() && query.ingressNodeId != m_ingressNodeFilter) {
      continue;
    }
    auto it = queryEmbeddingRows.find(query.queryId);
    if (it != queryEmbeddingRows.end()) {
      query.embeddingIndex = it->second;
    }
    m_queries.push_back(query);
    if (m_queryLimit != 0 && m_queries.size() >= m_queryLimit) {
      break;
    }
  }
  std::sort(m_queries.begin(), m_queries.end(), [] (const HiRouteQueryRecord& left,
                                                     const HiRouteQueryRecord& right) {
    return left.startTimeMs < right.startTimeMs;
  });

  m_rankedQrels.clear();
  for (const auto& row : HiRouteDatasetReader::ReadCsvRows(m_qrelsObjectCsvPath)) {
    const auto relevance = static_cast<uint32_t>(std::strtoul(GetFieldOrEmpty(row, "relevance").c_str(), nullptr, 10));
    m_rankedQrels[GetFieldOrEmpty(row, "query_id")].push_back({GetFieldOrEmpty(row, "object_id"), relevance});
  }
  for (auto& item : m_rankedQrels) {
    std::sort(item.second.begin(), item.second.end(), [] (const auto& left, const auto& right) {
      if (left.second != right.second) {
        return left.second > right.second;
      }
      return left.first < right.first;
    });
  }

  m_canonicalByObjectId.clear();
  m_objectIdByCanonicalName.clear();
  for (const auto& row : HiRouteDatasetReader::ReadCsvRows(m_objectsCsvPath)) {
    const auto object = HiRouteObjectRecord::FromCsvRow(row);
    m_canonicalByObjectId[object.objectId] = object.canonicalName;
    m_objectIdByCanonicalName[object.canonicalName] = object.objectId;
  }
}

void
HiRouteIngressApp::openLogs()
{
  const auto queryPath = m_runDirectory + "/query_log.csv";
  const auto probePath = m_runDirectory + "/probe_log.csv";
  const auto searchPath = m_runDirectory + "/search_trace.csv";

  const bool queryNeedsHeader = fileNeedsHeader(queryPath);
  const bool probeNeedsHeader = fileNeedsHeader(probePath);
  const bool searchNeedsHeader = fileNeedsHeader(searchPath);

  m_queryLog.open(queryPath.c_str(), std::ios::out | std::ios::app);
  m_probeLog.open(probePath.c_str(), std::ios::out | std::ios::app);
  m_searchTraceLog.open(searchPath.c_str(), std::ios::out | std::ios::app);

  if (!m_queryLog.good() || !m_probeLog.good() || !m_searchTraceLog.good()) {
    throw std::runtime_error("failed to open HiRoute ingress logs under " + m_runDirectory);
  }

  if (queryNeedsHeader) {
    appendRow(m_queryLog, {"query_id", "scheme", "ingress_node_id", "start_time_ms", "remote_probes",
                           "discovery_bytes", "candidate_shrinkage_ratio", "latency_ms",
                           "success_at_1", "manifest_hit_at_r", "ndcg_at_r", "failure_type",
                           "fetched_object_id"});
  }
  if (probeNeedsHeader) {
    appendRow(m_probeLog, {"query_id", "scheme", "probe_index", "controller_prefix", "cell_id",
                           "reply_entries", "selected_object_id", "success"});
  }
  if (searchNeedsHeader) {
    appendRow(m_searchTraceLog, {"query_id", "scheme", "stage", "candidate_count",
                                 "selected_count", "frontier_size", "timestamp_ms"});
  }
}

void
HiRouteIngressApp::scheduleNextQuery(Time delay)
{
  if (!m_active || m_nextQueryIndex >= m_queries.size()) {
    return;
  }
  Simulator::Schedule(delay, &HiRouteIngressApp::dispatchNextQuery, this);
}

void
HiRouteIngressApp::dispatchNextQuery()
{
  if (!m_active || m_activeQuery.active || m_nextQueryIndex >= m_queries.size()) {
    return;
  }

  m_activeQuery = ActiveQueryState();
  m_activeQuery.active = true;
  m_activeQuery.query = m_queries[m_nextQueryIndex++];
  m_activeQuery.startedAt = Simulator::Now();

  if (m_strategyMode == "exact") {
    const auto objectId = topRelevantObject(m_activeQuery.query.queryId);
    if (objectId.empty()) {
      m_activeQuery.failureType = "predicate_miss";
      finishActiveQuery(false, "");
      return;
    }
    HiRouteManifestEntry entry;
    entry.objectId = objectId;
    entry.canonicalName = m_canonicalByObjectId[objectId];
    m_activeQuery.manifest = {entry};
    m_activeQuery.manifestHit = true;
    sendFetchInterest(entry);
    return;
  }

  m_activeQuery.plan = buildProbePlan(m_activeQuery.query);
  if (m_activeQuery.plan.probes.empty()) {
    m_activeQuery.failureType = "predicate_miss";
    finishActiveQuery(false, "");
    return;
  }
  sendDiscoveryProbe();
}

HiRouteIngressApp::ProbePlan
HiRouteIngressApp::buildProbePlan(const HiRouteQueryRecord& query,
                                  const std::set<std::string>& excludedProbeKeys)
{
  ProbePlan plan;
  HiRouteDiscoveryRequest request;
  request.queryId = query.queryId;
  request.queryEmbeddingRow = query.embeddingIndex;
  request.predicate.zoneConstraint = query.zoneConstraint;
  request.predicate.zoneTypeConstraint = query.zoneTypeConstraint;
  request.predicate.serviceConstraint = query.serviceConstraint;
  request.predicate.freshnessConstraint = query.freshnessConstraint;
  request.predicate.intentFacet = query.intentFacet;
  request.refinementBudget = m_maxProbeBudget;
  request.requestedManifestSize = m_requestedManifestSize;
  request.intentFacet = query.intentFacet;

  auto filterMatches = [&] (const std::vector<const HiRouteSummaryEntry*>& entries) {
    std::vector<const HiRouteSummaryEntry*> matched;
    matched.reserve(entries.size());
    for (const auto* entry : entries) {
      if (entry != nullptr &&
          entry->MatchesPredicate(query.zoneConstraint, query.zoneTypeConstraint,
                                  query.serviceConstraint, query.freshnessConstraint)) {
        matched.push_back(entry);
      }
    }
    return matched;
  };

  auto dedupeByCell = [&] (const std::vector<const HiRouteSummaryEntry*>& entries) {
    std::map<std::string, const HiRouteSummaryEntry*> unique;
    for (const auto* entry : entries) {
      if (entry == nullptr) {
        continue;
      }
      unique[entry->cellId] = entry;
    }
    std::vector<const HiRouteSummaryEntry*> deduped;
    deduped.reserve(unique.size());
    for (const auto& item : unique) {
      deduped.push_back(item.second);
    }
    return deduped;
  };

  auto maybeAppendProbe = [&] (std::vector<ProbeTarget>& probes, const ProbeTarget& target) {
    if (target.domainId.empty()) {
      return;
    }
    if (excludedProbeKeys.count(makeProbeKey(target)) != 0) {
      return;
    }
    auto duplicate = std::find_if(probes.begin(), probes.end(), [&] (const ProbeTarget& existing) {
      return makeProbeKey(existing) == makeProbeKey(target);
    });
    if (duplicate != probes.end()) {
      return;
    }
    probes.push_back(target);
  };

  const auto allLevel0Entries = m_summaryStore.GetEntriesAtLevel(0);
  const auto predicateMatches = filterMatches(allLevel0Entries);
  plan.allDomainCount = allLevel0Entries.size();
  plan.predicateCandidateCount = predicateMatches.size();
  plan.predicateFilteredDomainCount = predicateMatches.size();
  plan.level0CellCount = predicateMatches.size();

  auto rankedLevel0Targets = [&] (std::vector<const HiRouteSummaryEntry*> entries,
                                  bool usePredicate,
                                  double extraTagWeight) {
    HiRouteDiscoveryRequest rankingRequest = request;
    if (!usePredicate) {
      rankingRequest.predicate = HiRoutePredicateHeader{};
    }
    auto ranked =
      m_discoveryEngine.RankCandidates(entries, rankingRequest, m_reliabilityCache, entries.size());

    std::map<std::string, ProbeTarget> bestByController;
    for (const auto& candidate : ranked) {
      if (candidate.summary == nullptr || candidate.summary->level != 0) {
        continue;
      }
      double score = candidate.totalScore;
      if (!query.intentFacet.empty() &&
          candidate.summary->semanticTagBitmap.count(query.intentFacet) > 0) {
        score += extraTagWeight;
      }
      ProbeTarget target{candidate.summary->domainId, candidate.summary->controllerPrefix,
                         candidate.summary->cellId, score};
      auto existing = bestByController.find(target.controllerPrefix);
      if (existing == bestByController.end() || target.score > existing->second.score) {
        bestByController[target.controllerPrefix] = target;
      }
    }

    std::vector<ProbeTarget> targets;
    targets.reserve(bestByController.size());
    for (const auto& item : bestByController) {
      targets.push_back(item.second);
    }
    std::sort(targets.begin(), targets.end(), [] (const ProbeTarget& left, const ProbeTarget& right) {
      if (left.score == right.score) {
        return left.controllerPrefix < right.controllerPrefix;
      }
      return left.score > right.score;
    });
    if (targets.size() > m_maxProbeBudget) {
      targets.resize(m_maxProbeBudget);
    }
    return targets;
  };

  auto predicateOnlyTargets = [&] (const std::vector<const HiRouteSummaryEntry*>& entries) {
    std::vector<ProbeTarget> targets;
    for (const auto* entry : entries) {
      if (entry == nullptr || entry->level != 0) {
        continue;
      }
      targets.push_back({entry->domainId, entry->controllerPrefix, entry->cellId, 1.0});
    }
    std::sort(targets.begin(), targets.end(), [] (const ProbeTarget& left, const ProbeTarget& right) {
      if (left.domainId == right.domainId) {
        return left.controllerPrefix < right.controllerPrefix;
      }
      return left.domainId < right.domainId;
    });
    if (targets.size() > m_maxProbeBudget) {
      targets.resize(m_maxProbeBudget);
    }
    return targets;
  };

  if (m_strategyMode == "oracle") {
    maybeAppendProbe(plan.probes, {"oracle", m_oraclePrefix, "", 1.0});
    plan.level1CellCount = plan.level0CellCount;
    plan.refinedCellCount = 1;
  }
  else if (m_strategyMode == "flood") {
    std::vector<ProbeTarget> targets;
    for (const auto* entry : predicateMatches) {
      if (entry == nullptr || entry->level != 0) {
        continue;
      }
      targets.push_back({entry->domainId, entry->controllerPrefix, "", 0.0});
    }
    std::sort(targets.begin(), targets.end(), [] (const ProbeTarget& left, const ProbeTarget& right) {
      if (left.domainId == right.domainId) {
        return left.controllerPrefix < right.controllerPrefix;
      }
      return left.domainId < right.domainId;
    });
    if (targets.size() > m_maxProbeBudget) {
      targets.resize(m_maxProbeBudget);
    }
    for (const auto& target : targets) {
      maybeAppendProbe(plan.probes, target);
    }
    plan.level1CellCount = plan.level0CellCount;
    plan.refinedCellCount = plan.probes.size();
  }
  else if (m_strategyMode == "flat") {
    for (const auto& target : rankedLevel0Targets(predicateMatches, true, 0.0)) {
      maybeAppendProbe(plan.probes, target);
    }
    plan.level1CellCount = plan.level0CellCount;
    plan.refinedCellCount = plan.probes.size();
  }
  else if (m_strategyMode == "predicates_only") {
    plan.probes = predicateOnlyTargets(predicateMatches);
    plan.level1CellCount = plan.level0CellCount;
    plan.refinedCellCount = plan.probes.size();
  }
  else if (m_strategyMode == "flat_semantic_only") {
    std::vector<const HiRouteSummaryEntry*> allEntries;
    allEntries.reserve(allLevel0Entries.size());
    for (const auto* entry : allLevel0Entries) {
      allEntries.push_back(entry);
    }
    plan.predicateCandidateCount = allEntries.size();
    plan.predicateFilteredDomainCount = allEntries.size();
    plan.level0CellCount = allEntries.size();
    plan.probes = rankedLevel0Targets(allEntries, false, 0.25);
    plan.level1CellCount = plan.level0CellCount;
    plan.refinedCellCount = plan.probes.size();
  }
  else if (m_strategyMode == "predicates_plus_flat" || m_strategyMode == "inf_tag_forwarding") {
    const double extraTagWeight = m_strategyMode == "inf_tag_forwarding" ? 0.45 : 0.2;
    plan.probes = rankedLevel0Targets(predicateMatches, true, extraTagWeight);
    plan.level1CellCount = plan.level0CellCount;
    plan.refinedCellCount = plan.probes.size();
  }
  else {
    const auto level0Ranked = m_discoveryEngine.RankCandidates(
      predicateMatches, request, m_reliabilityCache, 0);
    const auto rootExpansionCount =
      std::min(level0Ranked.size(), static_cast<size_t>(std::max<uint32_t>(1, m_maxProbeBudget)));

    std::vector<const HiRouteSummaryEntry*> level1Pool;
    for (size_t index = 0; index < rootExpansionCount; ++index) {
      const auto children = filterMatches(m_summaryStore.GetChildren(level0Ranked[index].summary->cellId));
      level1Pool.insert(level1Pool.end(), children.begin(), children.end());
    }
    level1Pool = dedupeByCell(level1Pool);
    if (level1Pool.empty()) {
      level1Pool = predicateMatches;
    }
    plan.level1CellCount = level1Pool.size();

    const auto level1Ranked = m_discoveryEngine.RankCandidates(
      level1Pool, request, m_reliabilityCache, 0);
    const auto refinementCount =
      std::min(level1Ranked.size(), static_cast<size_t>(std::max<uint32_t>(1, m_maxProbeBudget)));

    std::vector<const HiRouteSummaryEntry*> refinedPool;
    for (size_t index = 0; index < refinementCount; ++index) {
      const auto* summary = level1Ranked[index].summary;
      if (summary == nullptr) {
        continue;
      }
      const auto children = filterMatches(m_summaryStore.GetChildren(summary->cellId));
      if (children.empty()) {
        refinedPool.push_back(summary);
        continue;
      }
      refinedPool.insert(refinedPool.end(), children.begin(), children.end());
    }
    refinedPool = dedupeByCell(refinedPool);
    if (refinedPool.empty()) {
      refinedPool = level1Pool;
    }
    plan.refinedCellCount = refinedPool.size();

    const auto candidates =
      m_discoveryEngine.RankCandidates(refinedPool, request, m_reliabilityCache, m_maxProbeBudget);
    for (const auto& candidate : candidates) {
      if (candidate.summary == nullptr) {
        continue;
      }
      std::string frontierCellId = candidate.summary->cellId;
      if ((m_strategyMode == "hiroute" || m_strategyMode == "full_hiroute") &&
          candidate.summary->level > 1 && !candidate.summary->parentId.empty()) {
        // Probe the level-1 parent cell so the controller can search the target neighborhood
        // instead of only a single microcluster.
        frontierCellId = candidate.summary->parentId;
      }
      maybeAppendProbe(
        plan.probes,
        {candidate.summary->domainId, candidate.summary->controllerPrefix,
         frontierCellId, candidate.totalScore});
    }
  }

  plan.probeTargetCount = plan.probes.size();
  const int64_t startTimestamp = static_cast<int64_t>(query.startTimeMs);
  logSearchStage(query.queryId, "all_domains", plan.allDomainCount,
                 plan.predicateFilteredDomainCount, plan.allDomainCount, startTimestamp);
  logSearchStage(query.queryId, "predicate_filtered_domains", plan.predicateFilteredDomainCount,
                 plan.level0CellCount, plan.predicateFilteredDomainCount, startTimestamp + 1);
  logSearchStage(query.queryId, "level0_cells", plan.level0CellCount,
                 plan.level1CellCount, plan.level0CellCount, startTimestamp + 2);
  logSearchStage(query.queryId, "level1_cells", plan.level1CellCount,
                 plan.refinedCellCount, plan.level1CellCount, startTimestamp + 3);
  logSearchStage(query.queryId, "refined_cells", plan.refinedCellCount,
                 plan.probeTargetCount, plan.refinedCellCount, startTimestamp + 4);
  logSearchStage(query.queryId, "probed_cells", plan.probeTargetCount,
                 plan.probeTargetCount, plan.probeTargetCount, startTimestamp + 5);
  return plan;
}

void
HiRouteIngressApp::sendDiscoveryProbe()
{
  if (m_activeQuery.remoteProbes >= m_maxProbeBudget ||
      m_activeQuery.probeIndex >= m_activeQuery.plan.probes.size()) {
    m_activeQuery.failureType = "wrong_domain";
    finishActiveQuery(false, "");
    return;
  }

  const auto& target = m_activeQuery.plan.probes[m_activeQuery.probeIndex];
  HiRouteDiscoveryRequest request;
  request.queryId = m_activeQuery.query.queryId;
  request.queryEmbeddingRow = m_activeQuery.query.embeddingIndex;
  request.predicate.zoneConstraint = m_activeQuery.query.zoneConstraint;
  request.predicate.zoneTypeConstraint = m_activeQuery.query.zoneTypeConstraint;
  request.predicate.serviceConstraint = m_activeQuery.query.serviceConstraint;
  request.predicate.freshnessConstraint = m_activeQuery.query.freshnessConstraint;
  request.predicate.intentFacet = m_activeQuery.query.intentFacet;
  request.refinementBudget = m_maxProbeBudget;
  request.requestedManifestSize = m_requestedManifestSize;
  request.frontierHintCellId = target.cellId;
  request.intentFacet = m_activeQuery.query.intentFacet;

  const auto parameters = HiRouteTlv::EncodeDiscoveryRequest(request);
  auto interest = std::make_shared<Interest>(
    target.controllerPrefix + "/discovery/" + m_activeQuery.query.queryId + "/" +
    std::to_string(m_activeQuery.probeIndex));
  interest->setNonce(m_rand->GetValue(0, std::numeric_limits<uint32_t>::max()));
  interest->setInterestLifetime(time::milliseconds(m_replyTimeout.GetMilliSeconds()));
  interest->setApplicationParameters(parameters);

  m_activeQuery.phase = Phase::WaitingDiscovery;
  ++m_activeQuery.remoteProbes;
  m_activeQuery.discoveryBytes += parameters.size();
  m_transmittedInterests(interest, this, m_face);
  m_appLink->onReceiveInterest(*interest);
  m_activeQuery.timeoutEvent =
    Simulator::Schedule(m_replyTimeout, &HiRouteIngressApp::onPhaseTimeout, this);
}

void
HiRouteIngressApp::sendFetchInterest(const HiRouteManifestEntry& entry)
{
  auto interest = std::make_shared<Interest>(entry.canonicalName);
  interest->setNonce(m_rand->GetValue(0, std::numeric_limits<uint32_t>::max()));
  interest->setInterestLifetime(time::milliseconds(m_replyTimeout.GetMilliSeconds()));
  m_activeQuery.phase = Phase::WaitingFetch;
  m_transmittedInterests(interest, this, m_face);
  m_appLink->onReceiveInterest(*interest);
  m_activeQuery.timeoutEvent =
    Simulator::Schedule(m_replyTimeout, &HiRouteIngressApp::onPhaseTimeout, this);
}

bool
HiRouteIngressApp::advanceToNextProbe(const std::string& terminalFailureType)
{
  if (!usesAdaptiveReliability()) {
    return false;
  }

  if (!m_activeQuery.plan.probes.empty() && m_activeQuery.probeIndex < m_activeQuery.plan.probes.size()) {
    const auto& probe = m_activeQuery.plan.probes[m_activeQuery.probeIndex];
    m_activeQuery.attemptedProbeKeys.insert(makeProbeKey(probe));
    m_reliabilityCache.ObserveResult(probe.domainId, probe.cellId, false);
    m_reliabilityCache.MarkNegative(
      probe.domainId, probe.cellId,
      HiRoutePredicateHeader{m_activeQuery.query.zoneConstraint,
                             m_activeQuery.query.zoneTypeConstraint,
                             m_activeQuery.query.serviceConstraint,
                             m_activeQuery.query.freshnessConstraint,
                             m_activeQuery.query.intentFacet},
      MilliSeconds(900));
  }

  m_activeQuery.manifest.clear();
  m_activeQuery.manifestFetchIndex = 0;
  m_activeQuery.manifestHit = false;
  ++m_activeQuery.replanCount;
  if (m_activeQuery.remoteProbes < m_maxProbeBudget) {
    m_activeQuery.plan = buildProbePlan(m_activeQuery.query, m_activeQuery.attemptedProbeKeys);
    m_activeQuery.probeIndex = 0;
  }
  if (!m_activeQuery.plan.probes.empty() && m_activeQuery.remoteProbes < m_maxProbeBudget) {
    sendDiscoveryProbe();
    return true;
  }

  m_activeQuery.failureType = terminalFailureType;
  return false;
}

bool
HiRouteIngressApp::advanceToNextStaticProbe(const std::string& terminalFailureType)
{
  if (!usesStaticProbeFallback()) {
    return false;
  }

  m_activeQuery.manifest.clear();
  m_activeQuery.manifestFetchIndex = 0;
  m_activeQuery.manifestHit = false;
  if (m_activeQuery.probeIndex + 1 >= m_activeQuery.plan.probes.size() ||
      m_activeQuery.remoteProbes >= m_maxProbeBudget) {
    m_activeQuery.failureType = terminalFailureType;
    return false;
  }

  ++m_activeQuery.probeIndex;
  sendDiscoveryProbe();
  return true;
}

void
HiRouteIngressApp::onPhaseTimeout()
{
  if (!m_activeQuery.active) {
    return;
  }

  if (m_activeQuery.phase == Phase::WaitingDiscovery) {
    if (usesAdaptiveReliability()) {
      if (advanceToNextProbe("no_reply")) {
        return;
      }
      m_activeQuery.failureType = "no_reply";
      finishActiveQuery(false, "");
      return;
    }
    if (advanceToNextStaticProbe("no_reply")) {
      return;
    }
    m_activeQuery.failureType = "no_reply";
    finishActiveQuery(false, "");
    return;
  }

  if (usesSequentialManifestFallback() &&
      m_activeQuery.manifestFetchIndex + 1 < m_activeQuery.manifest.size()) {
    ++m_activeQuery.manifestFetchIndex;
    sendFetchInterest(m_activeQuery.manifest[m_activeQuery.manifestFetchIndex]);
    return;
  }

  if (advanceToNextProbe("fetch_timeout")) {
    return;
  }

  m_activeQuery.failureType = "fetch_timeout";
  finishActiveQuery(false, "");
}

void
HiRouteIngressApp::handleDiscoveryReply(shared_ptr<const Data> data)
{
  if (m_activeQuery.timeoutEvent.IsRunning()) {
    m_activeQuery.timeoutEvent.Cancel();
  }

  const auto reply = HiRouteTlv::DecodeDiscoveryReply(data->getContent().blockFromValue());
  m_activeQuery.manifest = reply.manifest;
  m_activeQuery.manifestFetchIndex = 0;
  m_activeQuery.manifestHit = false;
  for (const auto& entry : reply.manifest) {
    if (isRelevantObject(m_activeQuery.query.queryId, entry.objectId)) {
      m_activeQuery.manifestHit = true;
      break;
    }
  }

  appendRow(m_probeLog,
            {m_activeQuery.query.queryId,
             m_strategyMode,
             std::to_string(m_activeQuery.probeIndex),
             m_activeQuery.plan.probes[m_activeQuery.probeIndex].controllerPrefix,
             m_activeQuery.plan.probes[m_activeQuery.probeIndex].cellId,
             std::to_string(reply.manifest.size()),
             reply.manifest.empty() ? std::string() : reply.manifest.front().objectId,
             reply.manifest.empty() ? "0" : "1"});
  logSearchStage(m_activeQuery.query.queryId, "manifest_candidates", reply.manifest.size(),
                 reply.manifest.empty() ? 0u : 1u, reply.manifest.size(),
                 Simulator::Now().GetMilliSeconds());

  if (reply.manifest.empty()) {
    if (usesAdaptiveReliability()) {
      if (advanceToNextProbe("wrong_domain")) {
        return;
      }
      m_activeQuery.failureType = "wrong_domain";
      finishActiveQuery(false, "");
      return;
    }
    if (advanceToNextStaticProbe("wrong_domain")) {
      return;
    }
    m_activeQuery.failureType = "wrong_domain";
    finishActiveQuery(false, "");
    return;
  }

  sendFetchInterest(reply.manifest.front());
}

void
HiRouteIngressApp::handleFetchReply(shared_ptr<const Data> data)
{
  if (m_activeQuery.timeoutEvent.IsRunning()) {
    m_activeQuery.timeoutEvent.Cancel();
  }

  const auto name = data->getName().toUri();
  auto objectIt = m_objectIdByCanonicalName.find(name);
  const auto objectId = objectIt == m_objectIdByCanonicalName.end() ? std::string() : objectIt->second;
  if (usesAdaptiveReliability() && m_activeQuery.probeIndex < m_activeQuery.plan.probes.size()) {
    const auto& probe = m_activeQuery.plan.probes[m_activeQuery.probeIndex];
    m_reliabilityCache.ObserveResult(probe.domainId, probe.cellId,
                                     isRelevantObject(m_activeQuery.query.queryId, objectId));
  }
  if (!isRelevantObject(m_activeQuery.query.queryId, objectId) &&
      usesSequentialManifestFallback() &&
      m_activeQuery.manifestFetchIndex + 1 < m_activeQuery.manifest.size()) {
    ++m_activeQuery.manifestFetchIndex;
    sendFetchInterest(m_activeQuery.manifest[m_activeQuery.manifestFetchIndex]);
    return;
  }

  if (!isRelevantObject(m_activeQuery.query.queryId, objectId) && advanceToNextProbe("wrong_object")) {
    return;
  }
  if (!isRelevantObject(m_activeQuery.query.queryId, objectId) &&
      advanceToNextStaticProbe("wrong_object")) {
    return;
  }
  finishActiveQuery(isRelevantObject(m_activeQuery.query.queryId, objectId), objectId);
}

void
HiRouteIngressApp::finishActiveQuery(bool success, const std::string& fetchedObjectId)
{
  const auto latencyMs = (Simulator::Now() - m_activeQuery.startedAt).GetMilliSeconds();
  const double denominator = m_summaryStore.GetEntries().empty() ? 1.0 :
                             static_cast<double>(m_summaryStore.GetEntries().size());
  const double candidateShrinkage =
    static_cast<double>(m_activeQuery.plan.refinedCellCount == 0
                          ? m_activeQuery.plan.predicateCandidateCount
                          : m_activeQuery.plan.refinedCellCount) / denominator;

  if (m_activeQuery.failureType.empty()) {
    m_activeQuery.failureType = success ? "none" : "wrong_object";
  }
  if (!success && !m_activeQuery.plan.probes.empty() && usesAdaptiveReliability()) {
    const auto& probe = m_activeQuery.plan.probes[m_activeQuery.probeIndex];
    m_reliabilityCache.MarkNegative(probe.domainId, probe.cellId,
                                    HiRoutePredicateHeader{m_activeQuery.query.zoneConstraint,
                                                           m_activeQuery.query.zoneTypeConstraint,
                                                           m_activeQuery.query.serviceConstraint,
                                                           m_activeQuery.query.freshnessConstraint,
                                                           m_activeQuery.query.intentFacet},
                                    MilliSeconds(900));
  }

  appendRow(m_queryLog,
            {m_activeQuery.query.queryId,
             m_strategyMode,
             m_activeQuery.query.ingressNodeId,
             std::to_string(m_activeQuery.query.startTimeMs),
             std::to_string(m_activeQuery.remoteProbes),
             std::to_string(m_activeQuery.discoveryBytes),
             std::to_string(candidateShrinkage),
             std::to_string(latencyMs),
             success ? "1" : "0",
             m_activeQuery.manifestHit ? "1" : "0",
             std::to_string(computeNdcgAtR(m_activeQuery.query.queryId, m_activeQuery.manifest)),
             m_activeQuery.failureType,
             fetchedObjectId});

  m_activeQuery = ActiveQueryState();
  scheduleNextQuery(MilliSeconds(1));
}

void
HiRouteIngressApp::appendRow(std::ofstream& stream, const std::vector<std::string>& values)
{
  for (size_t index = 0; index < values.size(); ++index) {
    if (index != 0) {
      stream << ',';
    }
    stream << escapeCsv(values[index]);
  }
  stream << '\n';
  stream.flush();
}

void
HiRouteIngressApp::logSearchStage(const std::string& queryId, const std::string& stage,
                                  size_t candidateCount, size_t selectedCount,
                                  size_t frontierSize, int64_t timestampMs)
{
  appendRow(m_searchTraceLog,
            {queryId,
             m_strategyMode,
             stage,
             std::to_string(candidateCount),
             std::to_string(selectedCount),
             std::to_string(frontierSize),
             std::to_string(timestampMs)});
}

bool
HiRouteIngressApp::isRelevantObject(const std::string& queryId, const std::string& objectId) const
{
  auto it = m_rankedQrels.find(queryId);
  if (it == m_rankedQrels.end()) {
    return false;
  }
  return std::any_of(it->second.begin(), it->second.end(), [&] (const auto& item) {
    return item.first == objectId && item.second > 0;
  });
}

std::string
HiRouteIngressApp::topRelevantObject(const std::string& queryId) const
{
  auto it = m_rankedQrels.find(queryId);
  if (it == m_rankedQrels.end() || it->second.empty()) {
    return {};
  }
  return it->second.front().first;
}

double
HiRouteIngressApp::computeNdcgAtR(const std::string& queryId,
                                  const std::vector<HiRouteManifestEntry>& manifest) const
{
  auto it = m_rankedQrels.find(queryId);
  if (it == m_rankedQrels.end() || manifest.empty()) {
    return 0.0;
  }

  std::map<std::string, uint32_t> relevanceByObject;
  std::vector<uint32_t> ideal;
  for (const auto& item : it->second) {
    relevanceByObject[item.first] = item.second;
    ideal.push_back(item.second);
  }
  std::sort(ideal.begin(), ideal.end(), std::greater<uint32_t>());

  double dcg = 0.0;
  for (size_t index = 0; index < manifest.size(); ++index) {
    const auto rel = relevanceByObject[manifest[index].objectId];
    dcg += (std::pow(2.0, static_cast<double>(rel)) - 1.0) / std::log2(static_cast<double>(index) + 2.0);
  }

  double idcg = 0.0;
  for (size_t index = 0; index < manifest.size() && index < ideal.size(); ++index) {
    idcg += (std::pow(2.0, static_cast<double>(ideal[index])) - 1.0) /
            std::log2(static_cast<double>(index) + 2.0);
  }
  return idcg == 0.0 ? 0.0 : dcg / idcg;
}

bool
HiRouteIngressApp::usesAdaptiveReliability() const
{
  return m_strategyMode == "hiroute" || m_strategyMode == "full_hiroute";
}

bool
HiRouteIngressApp::usesSequentialManifestFallback() const
{
  return m_strategyMode != "exact";
}

bool
HiRouteIngressApp::usesStaticProbeFallback() const
{
  return !usesAdaptiveReliability() && m_strategyMode != "exact" && m_strategyMode != "oracle";
}

std::string
HiRouteIngressApp::makeProbeKey(const ProbeTarget& target) const
{
  return target.domainId + "::" + target.cellId + "::" + target.controllerPrefix;
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
