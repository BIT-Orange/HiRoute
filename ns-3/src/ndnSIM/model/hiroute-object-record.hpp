/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_HIROUTE_OBJECT_RECORD_HPP
#define NDNSIM_HIROUTE_OBJECT_RECORD_HPP

#include "ns3/ndnSIM/model/ndn-common.hpp"

#include <map>
#include <string>

namespace ns3 {
namespace ndn {
namespace hiroute {

class HiRouteObjectRecord {
public:
  std::string objectId;
  std::string domainId;
  std::string zoneId;
  std::string zoneType;
  std::string serviceClass;
  std::string freshnessClass;
  std::string semanticFacet;
  std::string timeBucket;
  std::string vendorTemplateId;
  std::string canonicalName;
  std::string producerNodeId;
  std::string controllerNodeId;
  uint32_t payloadSizeBytes = 0;
  std::string unit;
  std::string valueType;
  uint64_t objectVersion = 0;
  std::string objectTextId;
  uint32_t embeddingIndex = 0;

  static HiRouteObjectRecord
  FromCsvRow(const std::map<std::string, std::string>& row);
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_OBJECT_RECORD_HPP
