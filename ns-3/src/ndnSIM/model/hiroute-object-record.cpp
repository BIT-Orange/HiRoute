/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "hiroute-object-record.hpp"

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

HiRouteObjectRecord
HiRouteObjectRecord::FromCsvRow(const std::map<std::string, std::string>& row)
{
  HiRouteObjectRecord record;
  record.objectId = getString(row, "object_id");
  record.domainId = getString(row, "domain_id");
  record.zoneId = getString(row, "zone_id");
  record.zoneType = getString(row, "zone_type");
  record.serviceClass = getString(row, "service_class");
  record.freshnessClass = getString(row, "freshness_class");
  record.timeBucket = getString(row, "time_bucket");
  record.vendorTemplateId = getString(row, "vendor_template_id");
  record.canonicalName = getString(row, "canonical_name");
  record.producerNodeId = getString(row, "producer_node_id");
  record.controllerNodeId = getString(row, "controller_node_id");
  record.payloadSizeBytes = getUint32(row, "payload_size_bytes");
  record.unit = getString(row, "unit");
  record.valueType = getString(row, "value_type");
  record.objectVersion = getUint64(row, "object_version");
  record.objectTextId = getString(row, "object_text_id");
  record.embeddingIndex = getUint32(row, "embedding_index");
  return record;
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
