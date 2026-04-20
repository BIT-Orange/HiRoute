/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_HIROUTE_CONTROLLER_APP_HPP
#define NDNSIM_HIROUTE_CONTROLLER_APP_HPP

#include "ndn-app.hpp"

#include "ns3/event-id.h"
#include "ns3/nstime.h"
#include "ns3/random-variable-stream.h"

#include "ns3/ndnSIM/model/hiroute-dataset-reader.hpp"
#include "ns3/ndnSIM/model/hiroute-embedding-store.hpp"
#include "ns3/ndnSIM/model/hiroute-manifest-entry.hpp"
#include "ns3/ndnSIM/model/hiroute-object-record.hpp"
#include "ns3/ndnSIM/model/hiroute-tlv.hpp"

#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace ns3 {
namespace ndn {
namespace hiroute {

class HiRouteControllerApp : public App {
public:
  static TypeId
  GetTypeId();

  HiRouteControllerApp();
  ~HiRouteControllerApp() override = default;

  void
  OnInterest(shared_ptr<const Interest> interest) override;

protected:
  void
  StartApplication() override;

  void
  StopApplication() override;

  void
  SetOracleMode(bool enabled);

  void
  SetPrefix(const std::string& prefix);

private:
  struct RankedObject {
    HiRouteObjectRecord object;
    double score = 0.0;
  };

  struct CandidateLookup {
    std::vector<std::string> objectIds;
    std::vector<std::string> localCandidateObjectIds;
    std::map<std::string, uint32_t> bestRankByObjectId;
    bool exactCellExists = false;
    size_t descendantCellCount = 0;
  };

  struct CandidateEvaluation {
    std::vector<RankedObject> ranked;
    size_t candidateObjectCountPreFilter = 0;
    size_t candidateObjectCountPostFilter = 0;
    std::string zeroReason;
  };

  void
  loadInputs();

  bool
  matchesPredicate(const HiRouteObjectRecord& object, const HiRoutePredicateHeader& predicate) const;

  double
  semanticFacetScore(const HiRouteObjectRecord& object, const HiRouteDiscoveryRequest& request) const;

  double
  semanticVectorScore(const HiRouteObjectRecord& object, const HiRouteDiscoveryRequest& request) const;

  double
  localRankScore(const std::string& objectId,
                 const std::map<std::string, uint32_t>& bestRankByObjectId) const;

  CandidateLookup
  resolveCandidateLookup(const std::string& frontierHintCellId) const;

  CandidateEvaluation
  evaluateCandidates(const HiRouteDiscoveryRequest& request, const std::string& frontierHintCellId,
                     const CandidateLookup& lookup) const;

  void
  appendManifestDebugRow(const HiRouteDiscoveryRequest& request, const std::string& frontierHintCellId,
                         const CandidateLookup& lookup, const CandidateEvaluation& evaluation) const;

  std::vector<HiRouteManifestEntry>
  buildManifest(const HiRouteDiscoveryRequest& request) const;

  std::vector<HiRouteManifestEntry>
  buildOracleManifest(const HiRouteDiscoveryRequest& request) const;

  void
  sendDiscoveryReply(shared_ptr<const Interest> interest, const HiRouteDiscoveryReply& reply);

  void
  sendObjectData(shared_ptr<const Interest> interest, const HiRouteObjectRecord& object);

private:
  std::string m_prefix;
  std::string m_domainId;
  std::string m_objectsCsvPath;
  std::string m_objectEmbeddingsCsvPath;
  std::string m_queryEmbeddingsCsvPath;
  std::string m_controllerLocalIndexCsvPath;
  std::string m_qrelsObjectCsvPath;
  std::string m_manifestDebugCsvPath;
  uint32_t m_manifestSize = 4;
  bool m_oracleMode = false;
  bool m_serveDiscovery = true;
  bool m_serveObjects = true;
  bool m_advertiseObjects = true;
  uint32_t m_objectShardModulo = 0;
  uint32_t m_objectShardIndex = 0;
  Time m_staleAfter = Seconds(0);
  double m_staleDropProbability = 0.0;
  Ptr<UniformRandomVariable> m_rand;
  HiRouteEmbeddingStore m_objectEmbeddings;
  HiRouteEmbeddingStore m_queryEmbeddings;

  std::map<std::string, HiRouteObjectRecord> m_objectsById;
  std::map<std::string, HiRouteObjectRecord> m_objectsByName;
  std::map<std::string, std::vector<std::string>> m_objectsByCell;
  std::map<std::string, std::vector<std::string>> m_objectsByFrontierHint;
  std::map<std::string, std::set<std::string>> m_concreteCellsByFrontierHint;
  std::map<std::string, std::vector<std::pair<std::string, uint32_t>>> m_oracleRankedQrels;
  std::map<std::string, uint32_t> m_rankByCellObject;
  std::map<std::string, uint32_t> m_rankByFrontierObject;
  bool m_hasExplicitAncestorFrontierIndex = false;
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_CONTROLLER_APP_HPP
