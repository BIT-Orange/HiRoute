/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_HIROUTE_QUERY_RECORD_HPP
#define NDNSIM_HIROUTE_QUERY_RECORD_HPP

#include "ns3/ndnSIM/model/ndn-common.hpp"

#include <map>
#include <string>

namespace ns3 {
namespace ndn {
namespace hiroute {

class HiRouteQueryRecord {
public:
  std::string queryId;
  std::string ingressNodeId;
  uint64_t startTimeMs = 0;
  std::string zoneConstraint;
  std::string zoneTypeConstraint;
  std::string serviceConstraint;
  std::string freshnessConstraint;
  std::string ambiguityLevel;
  std::string semanticIntentText;
  uint32_t embeddingIndex = 0;
  uint32_t groundTruthCount = 0;
  uint32_t intendedDomainCount = 0;
  std::string difficulty;
  std::string split;
  std::string queryTextId;

  static HiRouteQueryRecord
  FromCsvRow(const std::map<std::string, std::string>& row);
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_QUERY_RECORD_HPP
