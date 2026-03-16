/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "hiroute-reliability-cache.hpp"

#include <algorithm>
#include <sstream>

namespace ns3 {
namespace ndn {
namespace hiroute {

void
HiRouteReliabilityCache::SetAlpha(double alpha)
{
  m_alpha = std::max(0.0, std::min(1.0, alpha));
}

double
HiRouteReliabilityCache::getStateScore(const std::map<std::string, ReliabilityState>& table,
                                       const std::string& key) const
{
  auto it = table.find(key);
  return it == table.end() ? 0.5 : it->second.score;
}

void
HiRouteReliabilityCache::observeState(std::map<std::string, ReliabilityState>& table,
                                      const std::string& key, bool success)
{
  auto& state = table[key];
  if (!state.initialized) {
    state.score = success ? 1.0 : 0.0;
    state.initialized = true;
    return;
  }

  const double target = success ? 1.0 : 0.0;
  state.score = (1.0 - m_alpha) * state.score + m_alpha * target;
}

double
HiRouteReliabilityCache::GetReliability(const std::string& domainId, const std::string& cellId) const
{
  const auto cellScore = getStateScore(m_cellReliability, makeCellKey(domainId, cellId));
  const auto domainScore = getStateScore(m_domainReliability, makeDomainKey(domainId));
  return 0.7 * cellScore + 0.3 * domainScore;
}

void
HiRouteReliabilityCache::ObserveResult(const std::string& domainId, const std::string& cellId,
                                       bool success)
{
  observeState(m_cellReliability, makeCellKey(domainId, cellId), success);
  observeState(m_domainReliability, makeDomainKey(domainId), success);
}

void
HiRouteReliabilityCache::MarkNegative(const std::string& domainId, const std::string& cellId,
                                      const HiRoutePredicateHeader& predicate, Time ttl)
{
  const auto expiry = Simulator::Now() + ttl;
  m_cellNegativeExpiry[makeNegativeKey(domainId, cellId, predicate)] = expiry;
  m_domainNegativeExpiry[makeDomainNegativeKey(domainId, predicate)] = expiry;
}

bool
HiRouteReliabilityCache::IsSuppressed(const std::string& domainId, const std::string& cellId,
                                      const HiRoutePredicateHeader& predicate) const
{
  const auto now = Simulator::Now();
  const auto cellKey = makeNegativeKey(domainId, cellId, predicate);
  auto cellIt = m_cellNegativeExpiry.find(cellKey);
  if (cellIt != m_cellNegativeExpiry.end()) {
    if (cellIt->second > now) {
      return true;
    }
    m_cellNegativeExpiry.erase(cellIt);
  }

  const auto domainKey = makeDomainNegativeKey(domainId, predicate);
  auto domainIt = m_domainNegativeExpiry.find(domainKey);
  if (domainIt == m_domainNegativeExpiry.end()) {
    return false;
  }
  if (domainIt->second <= now) {
    m_domainNegativeExpiry.erase(domainIt);
    return false;
  }
  return true;
}

std::string
HiRouteReliabilityCache::MakePredicateKey(const HiRoutePredicateHeader& predicate)
{
  std::ostringstream output;
  output << predicate.zoneConstraint << '|'
         << predicate.zoneTypeConstraint << '|'
         << predicate.serviceConstraint << '|'
         << predicate.freshnessConstraint << '|'
         << predicate.intentFacet;
  return output.str();
}

std::string
HiRouteReliabilityCache::makeCellKey(const std::string& domainId, const std::string& cellId) const
{
  return domainId + "::" + cellId;
}

std::string
HiRouteReliabilityCache::makeDomainKey(const std::string& domainId) const
{
  return domainId;
}

std::string
HiRouteReliabilityCache::makeNegativeKey(const std::string& domainId, const std::string& cellId,
                                         const HiRoutePredicateHeader& predicate) const
{
  return makeCellKey(domainId, cellId) + "::" + MakePredicateKey(predicate);
}

std::string
HiRouteReliabilityCache::makeDomainNegativeKey(const std::string& domainId,
                                               const HiRoutePredicateHeader& predicate) const
{
  return makeDomainKey(domainId) + "::" + MakePredicateKey(predicate);
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
