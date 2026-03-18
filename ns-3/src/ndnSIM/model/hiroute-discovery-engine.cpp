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
HiRouteDiscoveryEngine::RankCandidates(const std::vector<const HiRouteSummaryEntry*>& pool,
                                       const HiRouteDiscoveryRequest& request,
                                       const HiRouteReliabilityCache& reliabilityCache,
                                       size_t limit) const
{
  const auto requestedLimit = limit == 0 ? static_cast<size_t>(request.refinementBudget) : limit;
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
    candidate.semanticScore = computeSemanticScore(*entry, request);
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
    if (left.totalScore != right.totalScore) {
      return left.totalScore > right.totalScore;
    }
    if (left.costScore != right.costScore) {
      return left.costScore < right.costScore;
    }
    const auto* leftSummary = left.summary;
    const auto* rightSummary = right.summary;
    if (leftSummary == nullptr || rightSummary == nullptr) {
      return leftSummary != nullptr;
    }
    if (leftSummary->domainId != rightSummary->domainId) {
      return leftSummary->domainId < rightSummary->domainId;
    }
    if (leftSummary->controllerPrefix != rightSummary->controllerPrefix) {
      return leftSummary->controllerPrefix < rightSummary->controllerPrefix;
    }
    return leftSummary->cellId < rightSummary->cellId;
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

  return RankCandidates(pool, request, reliabilityCache, limit);
}

double
HiRouteDiscoveryEngine::computeSemanticScore(const HiRouteSummaryEntry& entry,
                                             const HiRouteDiscoveryRequest& request) const
{
  double score = 0.0;

  if (!request.frontierHintCellId.empty()) {
    if (entry.cellId == request.frontierHintCellId) {
      score += 0.45;
    }
    else if (entry.parentId == request.frontierHintCellId) {
      score += 0.35;
    }
    else if (request.frontierHintCellId.rfind(entry.cellId + "-", 0) == 0) {
      score += 0.2;
    }
  }

  if (!request.intentFacet.empty()) {
    if (entry.semanticTagBitmap.count(request.intentFacet) > 0) {
      score += 0.45;
    }
    else if (entry.semanticTagBitmap.empty()) {
      score += 0.12;
    }
  }

  if (entry.radius <= 0.0) {
    score += 0.2;
  }
  else {
    score += 0.2 * (1.0 / (1.0 + entry.radius));
  }

  return std::min(1.0, score);
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
