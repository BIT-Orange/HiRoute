/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_HIROUTE_TLV_HPP
#define NDNSIM_HIROUTE_TLV_HPP

#include "ns3/ndnSIM/model/ndn-common.hpp"
#include "hiroute-manifest-entry.hpp"

#include <string>
#include <vector>

namespace ns3 {
namespace ndn {
namespace hiroute {

namespace tlv {
enum : uint32_t {
  HiRouteDiscoveryRequest = 800,
  HiRouteDiscoveryReply = 801,
  QueryId = 802,
  QueryEmbeddingRow = 803,
  ZoneConstraint = 804,
  ZoneTypeConstraint = 805,
  ServiceConstraint = 806,
  FreshnessConstraint = 807,
  RefinementBudget = 808,
  RequestedManifestSize = 809,
  FrontierHintCellId = 810,
  ResidualVector = 811,
  ManifestEntry = 812,
  CanonicalName = 813,
  ConfidenceScore = 814,
  DomainId = 815,
  CellId = 816,
  ObjectId = 817,
  PredicateHeader = 818,
  IntentFacet = 819
};
} // namespace tlv

struct HiRoutePredicateHeader {
  std::string zoneConstraint;
  std::string zoneTypeConstraint;
  std::string serviceConstraint;
  std::string freshnessConstraint;
  std::string intentFacet;
};

struct HiRouteDiscoveryRequest {
  std::string queryId;
  uint32_t queryEmbeddingRow = 0;
  HiRoutePredicateHeader predicate;
  uint32_t refinementBudget = 0;
  uint32_t requestedManifestSize = 0;
  std::string frontierHintCellId;
  std::string intentFacet;
  std::vector<float> residualVector;
};

struct HiRouteDiscoveryReply {
  std::vector<HiRouteManifestEntry> manifest;
};

class HiRouteTlv {
public:
  static Block
  EncodeDiscoveryRequest(const HiRouteDiscoveryRequest& request);

  static HiRouteDiscoveryRequest
  DecodeDiscoveryRequest(const Block& block);

  static Block
  EncodeDiscoveryReply(const HiRouteDiscoveryReply& reply);

  static HiRouteDiscoveryReply
  DecodeDiscoveryReply(const Block& block);
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_TLV_HPP
