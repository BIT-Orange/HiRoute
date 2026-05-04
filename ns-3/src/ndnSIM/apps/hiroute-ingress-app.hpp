/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_HIROUTE_INGRESS_APP_HPP
#define NDNSIM_HIROUTE_INGRESS_APP_HPP

#include "ndn-app.hpp"

#include "ns3/event-id.h"
#include "ns3/nstime.h"
#include "ns3/random-variable-stream.h"

#include "ns3/ndnSIM/model/hiroute-dataset-reader.hpp"
#include "ns3/ndnSIM/model/hiroute-discovery-engine.hpp"
#include "ns3/ndnSIM/model/hiroute-embedding-store.hpp"
#include "ns3/ndnSIM/model/hiroute-object-record.hpp"
#include "ns3/ndnSIM/model/hiroute-query-record.hpp"
#include "ns3/ndnSIM/model/hiroute-reliability-cache.hpp"
#include "ns3/ndnSIM/model/hiroute-summary-store.hpp"
#include "ns3/ndnSIM/model/hiroute-tlv.hpp"

#include <fstream>
#include <map>
#include <queue>
#include <set>
#include <string>
#include <vector>

namespace ns3 {
namespace ndn {
namespace hiroute {

class HiRouteIngressApp : public App {
public:
  static TypeId
  GetTypeId();

  HiRouteIngressApp();
  ~HiRouteIngressApp() override = default;

  void
  OnData(shared_ptr<const Data> data) override;

  void
  OnNack(shared_ptr<const lp::Nack> nack) override;

protected:
  void
  StartApplication() override;

  void
  StopApplication() override;

  void
  SetStrategyMode(const std::string& strategyMode);

private:
  struct ProbeTarget {
    std::string domainId;
    std::string controllerPrefix;
    std::string cellId;
    double score = 0.0;
  };

  struct ProbePlan {
    std::vector<ProbeTarget> probes;
    std::vector<std::string> allDomainIds;
    std::vector<std::string> predicateFilteredDomainIds;
    std::vector<std::string> level0CellIds;
    std::vector<std::string> level1CellIds;
    std::vector<std::string> refinedCellIds;
    size_t allDomainCount = 0;
    size_t predicateCandidateCount = 0;
    size_t predicateFilteredDomainCount = 0;
    size_t level0CellCount = 0;
    size_t level1CellCount = 0;
    size_t refinedCellCount = 0;
    size_t probeTargetCount = 0;
  };

  enum class Phase { Idle, WaitingDiscovery, WaitingFetch };

  struct ActiveQueryState {
    bool active = false;
    HiRouteQueryRecord query;
    ProbePlan plan;
    size_t probeIndex = 0;
    Time startedAt = Seconds(0);
    Phase phase = Phase::Idle;
    std::vector<HiRouteManifestEntry> manifest;
    size_t manifestFetchIndex = 0;
    size_t cumulativeManifestFetches = 0;
    bool firstFetchRelevant = false;
    bool firstFetchLooseRelevant = false;
    bool firstFetchRecorded = false;
    bool everReceivedManifest = false;
    bool everFetchedObject = false;
    bool everFetchedLooseRelevant = false;
    uint32_t remoteProbes = 0;
    uint64_t discoveryBytes = 0;
    bool manifestHit = false;
    uint32_t replanCount = 0;
    HiRouteDiscoveryStatus lastDiscoveryStatus = HiRouteDiscoveryStatus::Ok;
    std::string lastDiscoveryReason;
    std::string lastDiscoverySelectedCellId;
    double lastDiscoveryLocalConfidence = 0.0;
    std::string failureType;
    std::string fetchedObjectId;
    std::vector<std::string> probedDomainIds;
    std::set<std::string> attemptedProbeKeys;
    EventId timeoutEvent;
  };

  void
  loadInputs();

  void
  loadTopologyMapping();

  void
  openLogs();

  void
  scheduleNextQuery(Time delay);

  void
  dispatchNextQuery();

  ProbePlan
  buildProbePlan(const HiRouteQueryRecord& query,
                 const std::set<std::string>& excludedProbeKeys = {});

  void
  sendDiscoveryProbe();

  void
  sendFetchInterest(const HiRouteManifestEntry& entry);

  void
  onPhaseTimeout();

  bool
  advanceToNextProbe(const std::string& terminalFailureType);

  bool
  advanceToNextStaticProbe(const std::string& terminalFailureType);

  std::string
  makeProbeKey(const ProbeTarget& target) const;

  void
  handleDiscoveryReply(shared_ptr<const Data> data);

  void
  handleFetchReply(shared_ptr<const Data> data);

  void
  finishActiveQuery(bool success, const std::string& fetchedObjectId);

  void
  appendRow(std::ofstream& stream, const std::vector<std::string>& values);

  void
  logSearchStage(const std::string& queryId, const std::string& stage, size_t candidateCount,
                 size_t selectedCount, size_t frontierSize, int64_t timestampMs);

  void
  logProbePlanDebug(const HiRouteQueryRecord& query, const ProbePlan& plan);

  bool
  isRelevantObject(const std::string& queryId, const std::string& objectId) const;

  bool
  isStrongRelevantObject(const std::string& queryId, const std::string& objectId) const;

  uint32_t
  objectRelevanceGrade(const std::string& queryId, const std::string& objectId) const;

  std::string
  topRelevantObject(const std::string& queryId) const;

  double
  computeNdcgAtR(const std::string& queryId, const std::vector<HiRouteManifestEntry>& manifest) const;

  bool
  usesAdaptiveReliability() const;

  bool
  usesSequentialManifestFallback() const;

  bool
  usesStaticProbeFallback() const;

  uint32_t
  controllerHopCost(const std::string& controllerPrefix) const;

  uint32_t
  firstRelevantProbeRank(const std::string& queryId) const;

  std::string
  classifyFailureStage(bool success) const;

private:
  std::string m_queryCsvPath;
  std::string m_queryEmbeddingsCsvPath;
  std::string m_queryEmbeddingIndexCsvPath;
  std::string m_qrelsObjectCsvPath;
  std::string m_qrelsDomainCsvPath;
  std::string m_objectsCsvPath;
  std::string m_summaryCsvPath;
  std::string m_summaryEmbeddingsCsvPath;
  std::string m_topologyMappingCsvPath;
  std::string m_runDirectory;
  std::string m_probePlanDebugCsvPath;
  std::string m_strategyMode;
  std::string m_oraclePrefix;
  std::string m_ingressNodeFilter;
  uint32_t m_maxProbeBudget = 4;
  uint32_t m_requestedManifestSize = 4;
  uint32_t m_queryLimit = 0;
  uint32_t m_runSeed = 1;
  Time m_queryStartDelay = MilliSeconds(100);
  Time m_replyTimeout = MilliSeconds(200);

  Ptr<UniformRandomVariable> m_rand;
  HiRouteSummaryStore m_summaryStore;
  HiRouteDiscoveryEngine m_discoveryEngine;
  HiRouteReliabilityCache m_reliabilityCache;
  HiRouteEmbeddingStore m_queryEmbeddings;
  HiRouteEmbeddingStore m_summaryEmbeddings;
  std::vector<HiRouteQueryRecord> m_queries;
  size_t m_nextQueryIndex = 0;
  std::map<std::string, std::vector<std::pair<std::string, uint32_t>>> m_rankedQrels;
  std::map<std::string, std::set<std::string>> m_relevantDomainsByQuery;
  std::map<std::string, uint32_t> m_confuserDomainCountByQuery;
  std::map<std::string, uint32_t> m_confuserObjectCountByQuery;
  std::map<std::string, std::string> m_canonicalByObjectId;
  std::map<std::string, std::string> m_objectIdByCanonicalName;
  std::map<std::string, std::string> m_controllerNodeIdByPrefix;
  mutable std::map<std::string, uint32_t> m_controllerHopCostCache;
  ActiveQueryState m_activeQuery;

  std::ofstream m_queryLog;
  std::ofstream m_probeLog;
  std::ofstream m_searchTraceLog;
  std::ofstream m_probePlanDebugLog;
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_INGRESS_APP_HPP
