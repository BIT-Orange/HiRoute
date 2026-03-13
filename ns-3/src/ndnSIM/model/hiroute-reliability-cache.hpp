/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_HIROUTE_RELIABILITY_CACHE_HPP
#define NDNSIM_HIROUTE_RELIABILITY_CACHE_HPP

#include "ns3/ndnSIM/model/ndn-common.hpp"
#include "hiroute-tlv.hpp"

#include <map>
#include <string>

namespace ns3 {
namespace ndn {
namespace hiroute {

class HiRouteReliabilityCache {
public:
  void
  SetAlpha(double alpha);

  double
  GetReliability(const std::string& domainId, const std::string& cellId) const;

  void
  ObserveResult(const std::string& domainId, const std::string& cellId, bool success);

  void
  MarkNegative(const std::string& domainId, const std::string& cellId,
               const HiRoutePredicateHeader& predicate, Time ttl);

  bool
  IsSuppressed(const std::string& domainId, const std::string& cellId,
               const HiRoutePredicateHeader& predicate) const;

  static std::string
  MakePredicateKey(const HiRoutePredicateHeader& predicate);

private:
  struct ReliabilityState {
    double score = 0.5;
    bool initialized = false;
  };

  double
  getStateScore(const std::map<std::string, ReliabilityState>& table, const std::string& key) const;

  void
  observeState(std::map<std::string, ReliabilityState>& table, const std::string& key, bool success);

  std::string
  makeCellKey(const std::string& domainId, const std::string& cellId) const;

  std::string
  makeDomainKey(const std::string& domainId) const;

  std::string
  makeNegativeKey(const std::string& domainId, const std::string& cellId,
                  const HiRoutePredicateHeader& predicate) const;

  std::string
  makeDomainNegativeKey(const std::string& domainId, const HiRoutePredicateHeader& predicate) const;

private:
  double m_alpha = 0.2;
  std::map<std::string, ReliabilityState> m_cellReliability;
  std::map<std::string, ReliabilityState> m_domainReliability;
  mutable std::map<std::string, Time> m_cellNegativeExpiry;
  mutable std::map<std::string, Time> m_domainNegativeExpiry;
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_RELIABILITY_CACHE_HPP
