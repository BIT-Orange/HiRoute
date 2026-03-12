/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_HIROUTE_DISCOVERY_ENGINE_HPP
#define NDNSIM_HIROUTE_DISCOVERY_ENGINE_HPP

#include "ns3/ndnSIM/model/ndn-common.hpp"
#include "hiroute-reliability-cache.hpp"
#include "hiroute-summary-store.hpp"
#include "hiroute-tlv.hpp"

#include <map>
#include <vector>

namespace ns3 {
namespace ndn {
namespace hiroute {

class HiRouteDiscoveryEngine {
public:
  struct Weights {
    double alpha = 1.0;
    double beta = 0.75;
    double gamma = 0.5;
    double delta = 0.25;
  };

  struct Candidate {
    const HiRouteSummaryEntry* summary = nullptr;
    double semanticScore = 0.0;
    double predicateScore = 0.0;
    double reliabilityScore = 0.0;
    double costScore = 0.0;
    double totalScore = 0.0;
  };

  void
  SetWeights(const Weights& weights);

  std::vector<Candidate>
  SelectCandidates(const HiRouteSummaryStore& summaryStore, const HiRouteDiscoveryRequest& request,
                   const HiRouteReliabilityCache& reliabilityCache, size_t limit = 0) const;

private:
  double
  computeSemanticScore(const HiRouteSummaryEntry& entry,
                       const std::map<std::string, double>& semanticHints) const;

  double
  computePredicateScore(const HiRouteSummaryEntry& entry,
                        const HiRoutePredicateHeader& predicate) const;

  double
  computeCostScore(const HiRouteSummaryEntry& entry) const;

private:
  Weights m_weights;
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_DISCOVERY_ENGINE_HPP
