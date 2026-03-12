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

  std::string
  makeCellKey(const std::string& domainId, const std::string& cellId) const;

  std::string
  makeNegativeKey(const std::string& domainId, const std::string& cellId,
                  const HiRoutePredicateHeader& predicate) const;

private:
  double m_alpha = 0.2;
  std::map<std::string, ReliabilityState> m_reliability;
  mutable std::map<std::string, Time> m_negativeExpiry;
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_RELIABILITY_CACHE_HPP
