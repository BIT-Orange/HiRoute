/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_HIROUTE_SUMMARY_STORE_HPP
#define NDNSIM_HIROUTE_SUMMARY_STORE_HPP

#include "ns3/ndnSIM/model/ndn-common.hpp"
#include "hiroute-summary-entry.hpp"

#include <map>
#include <string>
#include <vector>

namespace ns3 {
namespace ndn {
namespace hiroute {

class HiRouteSummaryStore {
public:
  void
  LoadFromCsv(const std::string& path);

  const HiRouteSummaryEntry*
  Find(const std::string& cellId) const;

  std::vector<const HiRouteSummaryEntry*>
  GetChildren(const std::string& parentId) const;

  std::vector<const HiRouteSummaryEntry*>
  GetEntriesAtLevel(uint32_t level) const;

  std::vector<const HiRouteSummaryEntry*>
  FilterByPredicate(const std::string& zoneConstraint, const std::string& zoneTypeConstraint,
                    const std::string& serviceConstraint,
                    const std::string& freshnessConstraint) const;

  const std::vector<HiRouteSummaryEntry>&
  GetEntries() const;

private:
  void
  rebuildIndexes();

private:
  std::vector<HiRouteSummaryEntry> m_entries;
  std::map<std::string, size_t> m_cellIndex;
  std::map<std::string, std::vector<size_t>> m_children;
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_SUMMARY_STORE_HPP
