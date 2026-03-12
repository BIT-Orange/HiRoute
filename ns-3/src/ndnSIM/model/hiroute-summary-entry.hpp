/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_HIROUTE_SUMMARY_ENTRY_HPP
#define NDNSIM_HIROUTE_SUMMARY_ENTRY_HPP

#include "ns3/ndnSIM/model/ndn-common.hpp"

#include <map>
#include <set>
#include <string>

namespace ns3 {
namespace ndn {
namespace hiroute {

class HiRouteSummaryEntry {
public:
  std::string domainId;
  uint32_t level = 0;
  std::string cellId;
  std::string parentId;
  std::set<std::string> zoneBitmap;
  std::set<std::string> zoneTypeBitmap;
  std::set<std::string> serviceBitmap;
  std::set<std::string> freshnessBitmap;
  uint32_t centroidRow = 0;
  double radius = 0.0;
  uint32_t objectCount = 0;
  std::string controllerPrefix;
  std::string version;
  uint64_t ttlMs = 0;
  uint32_t exportBudget = 0;

  bool
  MatchesPredicate(const std::string& zoneConstraint, const std::string& zoneTypeConstraint,
                   const std::string& serviceConstraint, const std::string& freshnessConstraint) const;

  static HiRouteSummaryEntry
  FromCsvRow(const std::map<std::string, std::string>& row);
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_SUMMARY_ENTRY_HPP
