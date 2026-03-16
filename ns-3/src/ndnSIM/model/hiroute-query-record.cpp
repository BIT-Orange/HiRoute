/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "hiroute-query-record.hpp"

#include <cstdlib>

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

} // namespace

HiRouteQueryRecord
HiRouteQueryRecord::FromCsvRow(const std::map<std::string, std::string>& row)
{
  HiRouteQueryRecord record;
  record.queryId = getString(row, "query_id");
  record.ingressNodeId = getString(row, "ingress_node_id");
  record.startTimeMs = getUint64(row, "start_time_ms");
  record.zoneConstraint = getString(row, "zone_constraint");
  record.zoneTypeConstraint = getString(row, "zone_type_constraint");
  record.serviceConstraint = getString(row, "service_constraint");
  record.freshnessConstraint = getString(row, "freshness_constraint");
  record.ambiguityLevel = getString(row, "ambiguity_level");
  record.semanticIntentText = getString(row, "query_text");
  record.queryFamily = getString(row, "query_family");
  record.workloadTier = getString(row, "workload_tier");
  record.intentFacet = getString(row, "intent_facet");
  record.embeddingIndex = getUint32(row, "embedding_index");
  record.groundTruthCount = getUint32(row, "ground_truth_count");
  record.intendedDomainCount = getUint32(row, "intended_domain_count");
  record.difficulty = getString(row, "difficulty");
  record.split = getString(row, "split");
  record.queryTextId = getString(row, "query_text_id");
  if (record.groundTruthCount == 0) {
    record.groundTruthCount = record.intendedDomainCount;
  }
  return record;
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
