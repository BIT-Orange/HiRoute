/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "hiroute-summary-entry.hpp"

#include <cstdlib>
#include <sstream>

namespace ns3 {
namespace ndn {
namespace hiroute {

namespace {

std::string
getString(const std::map<std::string, std::string>& row, const std::string& key)
{
  auto it = row.find(key);
  return it == row.end() ? std::string() : it->second;
}

uint32_t
getUint32(const std::map<std::string, std::string>& row, const std::string& key)
{
  const auto value = getString(row, key);
  return value.empty() ? 0u : static_cast<uint32_t>(std::strtoul(value.c_str(), nullptr, 10));
}

uint64_t
getUint64(const std::map<std::string, std::string>& row, const std::string& key)
{
  const auto value = getString(row, key);
  return value.empty() ? 0ull : static_cast<uint64_t>(std::strtoull(value.c_str(), nullptr, 10));
}

double
getDouble(const std::map<std::string, std::string>& row, const std::string& key)
{
  const auto value = getString(row, key);
  return value.empty() ? 0.0 : std::strtod(value.c_str(), nullptr);
}

std::set<std::string>
parseBitmap(const std::string& bitmap)
{
  std::set<std::string> values;
  if (bitmap.empty()) {
    return values;
  }

  std::stringstream input(bitmap);
  std::string token;
  while (std::getline(input, token, '|')) {
    if (!token.empty()) {
      values.insert(token);
    }
  }
  return values;
}

bool
matchesBitmap(const std::set<std::string>& values, const std::string& constraint)
{
  return constraint.empty() || values.empty() || values.count(constraint) > 0;
}

} // namespace

bool
HiRouteSummaryEntry::MatchesPredicate(const std::string& zoneConstraint,
                                      const std::string& zoneTypeConstraint,
                                      const std::string& serviceConstraint,
                                      const std::string& freshnessConstraint) const
{
  return matchesBitmap(zoneBitmap, zoneConstraint) &&
         matchesBitmap(zoneTypeBitmap, zoneTypeConstraint) &&
         matchesBitmap(serviceBitmap, serviceConstraint) &&
         matchesBitmap(freshnessBitmap, freshnessConstraint);
}

HiRouteSummaryEntry
HiRouteSummaryEntry::FromCsvRow(const std::map<std::string, std::string>& row)
{
  HiRouteSummaryEntry entry;
  entry.domainId = getString(row, "domain_id");
  entry.level = getUint32(row, "level");
  entry.cellId = getString(row, "cell_id");
  entry.parentId = getString(row, "parent_id");
  entry.zoneBitmap = parseBitmap(getString(row, "zone_bitmap"));
  entry.zoneTypeBitmap = parseBitmap(getString(row, "zone_type_bitmap"));
  entry.serviceBitmap = parseBitmap(getString(row, "service_bitmap"));
  entry.freshnessBitmap = parseBitmap(getString(row, "freshness_bitmap"));
  entry.semanticTagBitmap = parseBitmap(getString(row, "semantic_tag_bitmap"));
  entry.centroidRow = getUint32(row, "centroid_row");
  entry.radius = getDouble(row, "radius");
  entry.objectCount = getUint32(row, "object_count");
  entry.controllerPrefix = getString(row, "controller_prefix");
  entry.version = getString(row, "version");
  entry.ttlMs = getUint64(row, "ttl_ms");
  entry.exportBudget = getUint32(row, "export_budget");
  return entry;
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
