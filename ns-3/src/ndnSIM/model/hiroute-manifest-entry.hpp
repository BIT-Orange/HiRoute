/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_HIROUTE_MANIFEST_ENTRY_HPP
#define NDNSIM_HIROUTE_MANIFEST_ENTRY_HPP

#include "ns3/ndnSIM/model/ndn-common.hpp"

#include <string>

namespace ns3 {
namespace ndn {
namespace hiroute {

class HiRouteManifestEntry {
public:
  std::string canonicalName;
  double confidenceScore = 0.0;
  std::string domainId;
  std::string cellId;
  std::string objectId;
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_MANIFEST_ENTRY_HPP
