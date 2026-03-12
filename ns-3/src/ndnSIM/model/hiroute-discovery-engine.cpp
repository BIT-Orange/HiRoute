/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "hiroute-discovery-engine.hpp"

#include <algorithm>
#include <cmath>

namespace ns3 {
namespace ndn {
namespace hiroute {

void
HiRouteDiscoveryEngine::SetWeights(const Weights& weights)
{
  m_weights = weights;
}

std::vector<HiRouteDiscoveryEngine::Candidate>
HiRouteDiscoveryEngine::SelectCandidates(const HiRouteSummaryStore& summaryStore,
                                         const HiRouteDiscoveryRequest& request,
                                         const HiRouteReliabilityCache& reliabilityCache,
                                         size_t limit) const
{
  std::vector<const HiRouteSummaryEntry*> pool;
  if (!request.frontierHintCellId.empty()) {
    pool = summaryStore.GetChildren(request.frontierHintCellId);
    if (pool.empty()) {
      if (const auto* cell = summaryStore.Find(request.frontierHintCellId)) {
        pool.push_back(cell);
      }
    }
  }

  if (pool.empty()) {
    pool = summaryStore.FilterByPredicate(request.predicate.zoneConstraint,
                                          request.predicate.zoneTypeConstraint,
                                          request.predicate.serviceConstraint,
                                          request.predicate.freshnessConstraint);
  }

  const auto requestedLimit = limit == 0 ? static_cast<size_t>(request.refinementBudget) : limit;
  const auto predicateKey = HiRouteReliabilityCache::MakePredicateKey(request.predicate);
  std::map<std::string, double> semanticHints;
  if (!request.frontierHintCellId.empty()) {
    semanticHints[request.frontierHintCellId] = 1.0;
  }

  std::vector<Candidate> candidates;
  candidates.reserve(pool.size());
  for (const auto* entry : pool) {
    if (entry == nullptr) {
      continue;
    }
    if (!entry->MatchesPredicate(request.predicate.zoneConstraint, request.predicate.zoneTypeConstraint,
                                 request.predicate.serviceConstraint,
                                 request.predicate.freshnessConstraint)) {
      continue;
    }
    if (reliabilityCache.IsSuppressed(entry->domainId, entry->cellId, request.predicate)) {
      continue;
    }

    Candidate candidate;
    candidate.summary = entry;
    candidate.semanticScore = computeSemanticScore(*entry, semanticHints);
    candidate.predicateScore = computePredicateScore(*entry, request.predicate);
    candidate.reliabilityScore = reliabilityCache.GetReliability(entry->domainId, entry->cellId);
    candidate.costScore = computeCostScore(*entry);
    candidate.totalScore = m_weights.alpha * candidate.semanticScore +
                           m_weights.beta * candidate.predicateScore +
                           m_weights.gamma * candidate.reliabilityScore -
                           m_weights.delta * candidate.costScore;
    candidates.push_back(candidate);
  }

  std::sort(candidates.begin(), candidates.end(), [] (const Candidate& left, const Candidate& right) {
    return left.totalScore > right.totalScore;
  });

  size_t maxCandidates = requestedLimit;
  if (maxCandidates == 0) {
    maxCandidates = candidates.size();
  }
  if (candidates.size() > maxCandidates) {
    candidates.resize(maxCandidates);
  }
  return candidates;
}

double
HiRouteDiscoveryEngine::computeSemanticScore(const HiRouteSummaryEntry& entry,
                                             const std::map<std::string, double>& semanticHints) const
{
  auto it = semanticHints.find(entry.cellId);
  if (it != semanticHints.end()) {
    return it->second;
  }

  if (entry.radius <= 0.0) {
    return 1.0;
  }
  return 1.0 / (1.0 + entry.radius);
}

double
HiRouteDiscoveryEngine::computePredicateScore(const HiRouteSummaryEntry& entry,
                                              const HiRoutePredicateHeader& predicate) const
{
  uint32_t matched = 0;
  uint32_t constrained = 0;

  if (!predicate.zoneConstraint.empty()) {
    ++constrained;
    matched += entry.zoneBitmap.count(predicate.zoneConstraint) > 0 ? 1u : 0u;
  }
  if (!predicate.zoneTypeConstraint.empty()) {
    ++constrained;
    matched += entry.zoneTypeBitmap.count(predicate.zoneTypeConstraint) > 0 ? 1u : 0u;
  }
  if (!predicate.serviceConstraint.empty()) {
    ++constrained;
    matched += entry.serviceBitmap.count(predicate.serviceConstraint) > 0 ? 1u : 0u;
  }
  if (!predicate.freshnessConstraint.empty()) {
    ++constrained;
    matched += entry.freshnessBitmap.count(predicate.freshnessConstraint) > 0 ? 1u : 0u;
  }

  return constrained == 0 ? 1.0 : static_cast<double>(matched) / constrained;
}

double
HiRouteDiscoveryEngine::computeCostScore(const HiRouteSummaryEntry& entry) const
{
  return 0.15 * static_cast<double>(entry.level) +
         std::min(1.0, std::log1p(static_cast<double>(entry.objectCount)) / 8.0);
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
