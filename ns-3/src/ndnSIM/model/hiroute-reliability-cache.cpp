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
HiRouteReliabilityCache::GetReliability(const std::string& domainId, const std::string& cellId) const
{
  auto it = m_reliability.find(makeCellKey(domainId, cellId));
  return it == m_reliability.end() ? 0.5 : it->second.score;
}

void
HiRouteReliabilityCache::ObserveResult(const std::string& domainId, const std::string& cellId,
                                       bool success)
{
  auto& state = m_reliability[makeCellKey(domainId, cellId)];
  if (!state.initialized) {
    state.score = success ? 1.0 : 0.0;
    state.initialized = true;
    return;
  }

  const double target = success ? 1.0 : 0.0;
  state.score = (1.0 - m_alpha) * state.score + m_alpha * target;
}

void
HiRouteReliabilityCache::MarkNegative(const std::string& domainId, const std::string& cellId,
                                      const HiRoutePredicateHeader& predicate, Time ttl)
{
  m_negativeExpiry[makeNegativeKey(domainId, cellId, predicate)] = Simulator::Now() + ttl;
}

bool
HiRouteReliabilityCache::IsSuppressed(const std::string& domainId, const std::string& cellId,
                                      const HiRoutePredicateHeader& predicate) const
{
  const auto key = makeNegativeKey(domainId, cellId, predicate);
  auto it = m_negativeExpiry.find(key);
  if (it == m_negativeExpiry.end()) {
    return false;
  }

  if (it->second <= Simulator::Now()) {
    m_negativeExpiry.erase(it);
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
         << predicate.freshnessConstraint;
  return output.str();
}

std::string
HiRouteReliabilityCache::makeCellKey(const std::string& domainId, const std::string& cellId) const
{
  return domainId + "::" + cellId;
}

std::string
HiRouteReliabilityCache::makeNegativeKey(const std::string& domainId, const std::string& cellId,
                                         const HiRoutePredicateHeader& predicate) const
{
  return makeCellKey(domainId, cellId) + "::" + MakePredicateKey(predicate);
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
