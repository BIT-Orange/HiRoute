/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_HIROUTE_SCENARIO_COMMON_HPP
#define NDNSIM_HIROUTE_SCENARIO_COMMON_HPP

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/ndnSIM-module.h"
#include "ns3/ndnSIM/helper/ndn-link-control-helper.hpp"
#include "ns3/names.h"

#include "ns3/ndnSIM/model/hiroute-dataset-reader.hpp"

#include <filesystem>
#include <fstream>
#include <cmath>
#include <cstdint>
#include <map>
#include <sstream>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace ns3 {
namespace ndn {
namespace hiroute {

enum class HiRouteScenarioMode { Main, StateScaling, Staleness, LinkFailure, DomainFailure };

struct HiRouteScenarioConfig {
  std::string topologyPath = "../data/interim/topologies/rf_3967_exodus.annotated.txt";
  std::string topologyMappingCsv = "../data/processed/ndnsim/topology_mapping_rf_3967_exodus.csv";
  std::string objectsCsv = "../data/processed/ndnsim/objects_master.csv";
  std::string queryCsv = "../data/processed/ndnsim/queries_master.csv";
  std::string queryEmbeddingIndexCsv = "../data/processed/ndnsim/query_embedding_index.csv";
  std::string qrelsObjectCsv = "../data/processed/eval/qrels_object.csv";
  std::string summaryCsv = "../data/processed/ndnsim/hslsa_export.csv";
  std::string controllerLocalIndexCsv = "../data/processed/ndnsim/controller_local_index.csv";
  std::string runDir = "../runs/pending/ndnsim-smoke";
  std::string topologyId = "rf_3967_exodus";
  std::string scheme = "hiroute";
  std::string oraclePrefix = "/hiroute/oracle/controller";
  double stopSeconds = 8.0;
  double failureTime = 2.0;
  double recoveryTime = 3.5;
  double staleDropProbability = 0.6;
  uint32_t manifestSize = 4;
  uint32_t probeBudget = 4;
  uint32_t queryLimitPerIngress = 5;
  uint32_t exportBudget = 16;
  std::string objectScales = "0.25,0.5,0.75,1.0";
  std::string objectsPerDomainSweep = "";
  std::string domainSweepCounts = "";
};

inline const char*
toString(HiRouteScenarioMode mode)
{
  switch (mode) {
    case HiRouteScenarioMode::Main:
      return "main";
    case HiRouteScenarioMode::StateScaling:
      return "state-scaling";
    case HiRouteScenarioMode::Staleness:
      return "staleness";
    case HiRouteScenarioMode::LinkFailure:
      return "link-failure";
    case HiRouteScenarioMode::DomainFailure:
      return "domain-failure";
  }
  return "unknown";
}

inline bool
needsHeader(const std::string& path)
{
  std::ifstream input(path.c_str());
  return !input.good() || input.peek() == std::ifstream::traits_type::eof();
}

inline void
appendCsvRow(const std::string& path, const std::vector<std::string>& header,
             const std::vector<std::string>& values)
{
  const bool writeHeader = needsHeader(path);
  std::ofstream output(path.c_str(), std::ios::out | std::ios::app);
  if (!output.good()) {
    throw std::runtime_error("failed to open csv path: " + path);
  }
  if (writeHeader) {
    for (size_t i = 0; i < header.size(); ++i) {
      if (i != 0) {
        output << ',';
      }
      output << header[i];
    }
    output << '\n';
  }
  for (size_t i = 0; i < values.size(); ++i) {
    if (i != 0) {
      output << ',';
    }
    const auto& value = values[i];
    const bool needsQuotes =
      value.find(',') != std::string::npos || value.find('"') != std::string::npos ||
      value.find('\n') != std::string::npos || value.find('\r') != std::string::npos;
    if (!needsQuotes) {
      output << value;
      continue;
    }
    output << '"';
    for (char ch : value) {
      if (ch == '"') {
        output << '"';
      }
      output << ch;
    }
    output << '"';
  }
  output << '\n';
}

inline void
ensureCsvHeader(const std::string& path, const std::vector<std::string>& header)
{
  if (!needsHeader(path)) {
    return;
  }
  std::ofstream output(path.c_str(), std::ios::out | std::ios::app);
  for (size_t i = 0; i < header.size(); ++i) {
    if (i != 0) {
      output << ',';
    }
    output << header[i];
  }
  output << '\n';
}

inline std::string
summaryControllerPrefix(const std::string& domainId)
{
  return "/hiroute/" + domainId + "/controller";
}

inline std::pair<std::string, std::string>
firstLinkPair(const std::string& topologyPath)
{
  std::ifstream input(topologyPath.c_str());
  if (!input.good()) {
    throw std::runtime_error("failed to open topology file: " + topologyPath);
  }

  bool inLinkSection = false;
  std::string line;
  while (std::getline(input, line)) {
    if (line.empty() || line[0] == '#') {
      continue;
    }
    if (line == "link") {
      inLinkSection = true;
      continue;
    }
    if (!inLinkSection) {
      continue;
    }

    std::stringstream parser(line);
    std::string left;
    std::string right;
    parser >> left >> right;
    if (!left.empty() && !right.empty()) {
      return {left, right};
    }
  }
  throw std::runtime_error("failed to find a link pair in topology file");
}

inline std::string
dominantQueryDomain(const std::string& objectsCsv, const std::string& qrelsObjectCsv)
{
  std::map<std::string, std::string> objectDomain;
  for (const auto& row : HiRouteDatasetReader::ReadCsvRows(objectsCsv)) {
    objectDomain[GetFieldOrEmpty(row, "object_id")] = GetFieldOrEmpty(row, "domain_id");
  }

  std::map<std::string, uint32_t> demandByDomain;
  for (const auto& row : HiRouteDatasetReader::ReadCsvRows(qrelsObjectCsv)) {
    if (std::strtoul(GetFieldOrEmpty(row, "relevance").c_str(), nullptr, 10) == 0) {
      continue;
    }
    auto objectIt = objectDomain.find(GetFieldOrEmpty(row, "object_id"));
    if (objectIt == objectDomain.end()) {
      continue;
    }
    ++demandByDomain[objectIt->second];
  }

  std::string bestDomain;
  uint32_t bestDemand = 0;
  for (const auto& item : demandByDomain) {
    if (item.second > bestDemand || (item.second == bestDemand && item.first < bestDomain)) {
      bestDomain = item.first;
      bestDemand = item.second;
    }
  }
  return bestDomain;
}

inline std::vector<std::string>
adjacentNodes(const std::string& topologyPath, const std::string& nodeId)
{
  std::ifstream input(topologyPath.c_str());
  if (!input.good()) {
    throw std::runtime_error("failed to open topology file: " + topologyPath);
  }

  bool inLinkSection = false;
  std::string line;
  std::set<std::string> neighbors;
  while (std::getline(input, line)) {
    if (line.empty() || line[0] == '#') {
      continue;
    }
    if (line == "link") {
      inLinkSection = true;
      continue;
    }
    if (!inLinkSection) {
      continue;
    }

    std::stringstream parser(line);
    std::string left;
    std::string right;
    parser >> left >> right;
    if (left == nodeId && !right.empty()) {
      neighbors.insert(right);
    }
    else if (right == nodeId && !left.empty()) {
      neighbors.insert(left);
    }
  }
  return {neighbors.begin(), neighbors.end()};
}

inline std::vector<double>
parseDoubleList(const std::string& encoded)
{
  std::vector<double> values;
  if (encoded.empty()) {
    return values;
  }

  std::stringstream parser(encoded);
  std::string token;
  while (std::getline(parser, token, ',')) {
    if (token.empty()) {
      continue;
    }
    values.push_back(std::strtod(token.c_str(), nullptr));
  }
  return values;
}

inline std::vector<uint32_t>
parseUintList(const std::string& encoded)
{
  std::vector<uint32_t> values;
  if (encoded.empty()) {
    return values;
  }

  std::stringstream parser(encoded);
  std::string token;
  while (std::getline(parser, token, ',')) {
    if (token.empty()) {
      continue;
    }
    values.push_back(static_cast<uint32_t>(std::strtoul(token.c_str(), nullptr, 10)));
  }
  return values;
}

inline std::vector<uint32_t>
defaultDomainSweepCounts(uint32_t totalDomains)
{
  std::set<uint32_t> counts;
  if (totalDomains == 0) {
    return {};
  }
  counts.insert(std::max(1u, totalDomains / 4));
  counts.insert(std::max(1u, totalDomains / 2));
  counts.insert(std::max(1u, (3 * totalDomains) / 4));
  counts.insert(totalDomains);
  return {counts.begin(), counts.end()};
}

inline uint32_t
stableSlotFromToken(const std::string& token, uint32_t modulo)
{
  if (modulo == 0) {
    return 0;
  }
  uint32_t hash = 2166136261u;
  for (unsigned char ch : token) {
    hash ^= static_cast<uint32_t>(ch);
    hash *= 16777619u;
  }
  return hash % modulo;
}

inline uint32_t
estimateSummaryBytes(const std::map<std::string, std::string>& row)
{
  return static_cast<uint32_t>(
    96 + GetFieldOrEmpty(row, "cell_id").size() + GetFieldOrEmpty(row, "parent_id").size() +
    GetFieldOrEmpty(row, "zone_bitmap").size() + GetFieldOrEmpty(row, "zone_type_bitmap").size() +
    GetFieldOrEmpty(row, "service_bitmap").size() + GetFieldOrEmpty(row, "freshness_bitmap").size() +
    GetFieldOrEmpty(row, "controller_prefix").size());
}

inline int
RunHiRouteScenario(int argc, char* argv[], HiRouteScenarioMode mode)
{
  HiRouteScenarioConfig config;
  CommandLine cmd;
  cmd.AddValue("topology", "Annotated topology path", config.topologyPath);
  cmd.AddValue("topologyMapping", "Topology mapping csv", config.topologyMappingCsv);
  cmd.AddValue("objectsCsv", "objects_master.csv path", config.objectsCsv);
  cmd.AddValue("queryCsv", "queries_master.csv path", config.queryCsv);
  cmd.AddValue("queryEmbeddingIndexCsv", "query embedding index path", config.queryEmbeddingIndexCsv);
  cmd.AddValue("qrelsObjectCsv", "qrels_object.csv path", config.qrelsObjectCsv);
  cmd.AddValue("summaryCsv", "hslsa_export.csv path", config.summaryCsv);
  cmd.AddValue("controllerLocalIndexCsv", "controller_local_index.csv path",
               config.controllerLocalIndexCsv);
  cmd.AddValue("runDir", "Output run directory", config.runDir);
  cmd.AddValue("topologyId", "Topology identifier", config.topologyId);
  cmd.AddValue("scheme",
               "exact, flood, flat_iroute, oracle, hiroute, inf_tag_forwarding",
               config.scheme);
  cmd.AddValue("stopSeconds", "Simulation stop time", config.stopSeconds);
  cmd.AddValue("failureTime", "Failure injection time", config.failureTime);
  cmd.AddValue("recoveryTime", "Link recovery time", config.recoveryTime);
  cmd.AddValue("staleDropProbability", "Probability of dropping the best manifest entry after staleness",
               config.staleDropProbability);
  cmd.AddValue("manifestSize", "Discovery manifest size", config.manifestSize);
  cmd.AddValue("probeBudget", "Discovery probe budget", config.probeBudget);
  cmd.AddValue("queryLimitPerIngress", "Maximum queries scheduled on each ingress node",
               config.queryLimitPerIngress);
  cmd.AddValue("exportBudget", "Per-domain export budget used in scaling summaries",
               config.exportBudget);
  cmd.AddValue("objectScales", "Comma-separated object scaling factors", config.objectScales);
  cmd.AddValue("objectsPerDomainSweep", "Comma-separated explicit objects-per-domain targets",
               config.objectsPerDomainSweep);
  cmd.AddValue("domainSweepCounts", "Comma-separated active domain counts",
               config.domainSweepCounts);
  cmd.Parse(argc, argv);

  std::filesystem::create_directories(config.runDir);

  AnnotatedTopologyReader topologyReader("", 25);
  topologyReader.SetFileName(config.topologyPath);
  topologyReader.Read();

  StackHelper ndnHelper;
  ndnHelper.InstallAll();

  GlobalRoutingHelper routingHelper;
  routingHelper.InstallAll();

  const auto topologyRows = HiRouteDatasetReader::ReadCsvRows(config.topologyMappingCsv);
  const auto objectRows = HiRouteDatasetReader::ReadCsvRows(config.objectsCsv);
  const auto summaryRows = HiRouteDatasetReader::ReadCsvRows(config.summaryCsv);
  const auto targetFailureDomain = dominantQueryDomain(config.objectsCsv, config.qrelsObjectCsv);

  std::map<std::string, Ptr<Node>> controllerByDomain;
  std::map<std::string, std::string> controllerNodeIdByDomain;
  std::map<std::string, std::vector<Ptr<Node>>> producerNodesByDomain;
  std::string firstControllerDomain;
  Ptr<Node> firstControllerNode;

  const auto stateLogPath = config.runDir + "/state_log.csv";
  const auto failureLogPath = config.runDir + "/failure_event_log.csv";
  ensureCsvHeader(failureLogPath,
                  {"timestamp_s", "event_type", "node_a", "node_b", "domain_id", "details"});

  std::vector<Ptr<Node>> ingressNodes;
  for (const auto& row : topologyRows) {
    if (GetFieldOrEmpty(row, "role") == "controller") {
      auto node = Names::Find<Node>(GetFieldOrEmpty(row, "node_id"));
      controllerByDomain[GetFieldOrEmpty(row, "domain_id")] = node;
      controllerNodeIdByDomain[GetFieldOrEmpty(row, "domain_id")] = GetFieldOrEmpty(row, "node_id");
      if (firstControllerNode == nullptr) {
        firstControllerNode = node;
        firstControllerDomain = GetFieldOrEmpty(row, "domain_id");
      }

      AppHelper controllerHelper("ns3::ndn::HiRouteControllerApp");
      controllerHelper.SetAttribute("Prefix", StringValue(summaryControllerPrefix(GetFieldOrEmpty(row, "domain_id"))));
      controllerHelper.SetAttribute("DomainId", StringValue(GetFieldOrEmpty(row, "domain_id")));
      controllerHelper.SetAttribute("ObjectsCsvPath", StringValue(config.objectsCsv));
      controllerHelper.SetAttribute("ControllerLocalIndexCsvPath",
                                    StringValue(config.controllerLocalIndexCsv));
      controllerHelper.SetAttribute("ManifestSize", UintegerValue(config.manifestSize));
      controllerHelper.SetAttribute("ServeDiscovery", BooleanValue(true));
      controllerHelper.SetAttribute("ServeObjects", BooleanValue(false));
      controllerHelper.SetAttribute("AdvertiseObjects", BooleanValue(false));
      if (mode == HiRouteScenarioMode::Staleness &&
          GetFieldOrEmpty(row, "domain_id") ==
            (targetFailureDomain.empty() ? firstControllerDomain : targetFailureDomain)) {
        controllerHelper.SetAttribute("StaleAfter",
                                      StringValue(std::to_string(config.failureTime) + "s"));
        controllerHelper.SetAttribute("StaleDropProbability",
                                      DoubleValue(config.staleDropProbability));
      }
      auto apps = controllerHelper.Install(node);
      apps.Start(Seconds(0.0));
      if (mode == HiRouteScenarioMode::DomainFailure &&
          GetFieldOrEmpty(row, "domain_id") ==
            (targetFailureDomain.empty() ? firstControllerDomain : targetFailureDomain)) {
        apps.Stop(Seconds(config.failureTime));
        appendCsvRow(failureLogPath,
                     {"timestamp_s", "event_type", "node_a", "node_b", "domain_id", "details"},
                     {std::to_string(config.failureTime), "domain_failure",
                      GetFieldOrEmpty(row, "node_id"), "", GetFieldOrEmpty(row, "domain_id"),
                      "controller stopped"});
      }
      else {
        apps.Stop(Seconds(config.stopSeconds));
      }

      routingHelper.AddOrigin(summaryControllerPrefix(GetFieldOrEmpty(row, "domain_id")), node);
    }
    else if (GetFieldOrEmpty(row, "role") == "producer") {
      producerNodesByDomain[GetFieldOrEmpty(row, "domain_id")].push_back(
        Names::Find<Node>(GetFieldOrEmpty(row, "node_id")));
    }
    else if (GetFieldOrEmpty(row, "role") == "ingress") {
      ingressNodes.push_back(Names::Find<Node>(GetFieldOrEmpty(row, "node_id")));
    }
  }

  if (firstControllerNode == nullptr) {
    throw std::runtime_error("no controller nodes found in topology mapping");
  }

  AppHelper oracleHelper("ns3::ndn::OracleControllerApp");
  oracleHelper.SetAttribute("Prefix", StringValue(config.oraclePrefix));
  oracleHelper.SetAttribute("OracleMode", BooleanValue(true));
  oracleHelper.SetAttribute("ObjectsCsvPath", StringValue(config.objectsCsv));
  oracleHelper.SetAttribute("ControllerLocalIndexCsvPath", StringValue(config.controllerLocalIndexCsv));
  oracleHelper.SetAttribute("QrelsObjectCsvPath", StringValue(config.qrelsObjectCsv));
  oracleHelper.SetAttribute("ManifestSize", UintegerValue(config.manifestSize));
  auto oracleApps = oracleHelper.Install(firstControllerNode);
  oracleApps.Start(Seconds(0.0));
  oracleApps.Stop(Seconds(config.stopSeconds));
  routingHelper.AddOrigin(config.oraclePrefix, firstControllerNode);

  for (auto& item : producerNodesByDomain) {
    auto& producerNodes = item.second;
    std::sort(producerNodes.begin(), producerNodes.end(),
              [] (const Ptr<Node>& left, const Ptr<Node>& right) {
                return Names::FindName(left) < Names::FindName(right);
              });
    for (size_t index = 0; index < producerNodes.size(); ++index) {
      AppHelper producerHelper("ns3::ndn::HiRouteControllerApp");
      producerHelper.SetAttribute("Prefix", StringValue(summaryControllerPrefix(item.first)));
      producerHelper.SetAttribute("DomainId", StringValue(item.first));
      producerHelper.SetAttribute("ObjectsCsvPath", StringValue(config.objectsCsv));
      producerHelper.SetAttribute("ControllerLocalIndexCsvPath",
                                  StringValue(config.controllerLocalIndexCsv));
      producerHelper.SetAttribute("ManifestSize", UintegerValue(config.manifestSize));
      producerHelper.SetAttribute("ServeDiscovery", BooleanValue(false));
      producerHelper.SetAttribute("ServeObjects", BooleanValue(true));
      producerHelper.SetAttribute("AdvertiseObjects", BooleanValue(true));
      producerHelper.SetAttribute("ObjectShardModulo", UintegerValue(static_cast<uint32_t>(producerNodes.size())));
      producerHelper.SetAttribute("ObjectShardIndex", UintegerValue(static_cast<uint32_t>(index)));
      auto apps = producerHelper.Install(producerNodes[index]);
      apps.Start(Seconds(0.0));
      apps.Stop(Seconds(config.stopSeconds));
    }
  }

  for (const auto& row : objectRows) {
    const auto domainId = GetFieldOrEmpty(row, "domain_id");
    const auto domainIt = controllerByDomain.find(domainId);
    if (domainIt == controllerByDomain.end()) {
      continue;
    }
    Ptr<Node> originNode = domainIt->second;
    auto producerIt = producerNodesByDomain.find(domainId);
    if (producerIt != producerNodesByDomain.end() && !producerIt->second.empty()) {
      const auto slot = stableSlotFromToken(
        GetFieldOrEmpty(row, "object_id"), static_cast<uint32_t>(producerIt->second.size()));
      originNode = producerIt->second[slot];
    }
    routingHelper.AddOrigin(GetFieldOrEmpty(row, "canonical_name"), originNode);
  }

  for (const auto& row : topologyRows) {
    if (GetFieldOrEmpty(row, "role") != "ingress") {
      continue;
    }

    std::string strategyMode = config.scheme;
    std::string ingressType = "ns3::ndn::HiRouteIngressApp";
    if (config.scheme == "exact") {
      ingressType = "ns3::ndn::ExactNameIngressApp";
    }
    else if (config.scheme == "flood") {
      ingressType = "ns3::ndn::FloodDiscoveryApp";
    }
    else if (config.scheme == "flat_iroute" || config.scheme == "flat") {
      ingressType = "ns3::ndn::FlatSemanticIngressApp";
      strategyMode = "flat";
    }
    else if (config.scheme == "inf_tag_forwarding") {
      ingressType = "ns3::ndn::InfTagForwardingApp";
      strategyMode = "inf_tag_forwarding";
    }
    else if (config.scheme == "predicates_only" || config.scheme == "flat_semantic_only" ||
             config.scheme == "predicates_plus_flat" || config.scheme == "full_hiroute" ||
             config.scheme == "hiroute" || config.scheme == "oracle") {
      strategyMode = config.scheme;
    }

    AppHelper ingressHelper(ingressType);
    ingressHelper.SetAttribute("QueryCsvPath", StringValue(config.queryCsv));
    ingressHelper.SetAttribute("QueryEmbeddingIndexCsvPath",
                               StringValue(config.queryEmbeddingIndexCsv));
    ingressHelper.SetAttribute("QrelsObjectCsvPath", StringValue(config.qrelsObjectCsv));
    ingressHelper.SetAttribute("ObjectsCsvPath", StringValue(config.objectsCsv));
    ingressHelper.SetAttribute("SummaryCsvPath", StringValue(config.summaryCsv));
    ingressHelper.SetAttribute("RunDirectory", StringValue(config.runDir));
    ingressHelper.SetAttribute("IngressNodeFilter", StringValue(GetFieldOrEmpty(row, "node_id")));
    ingressHelper.SetAttribute("OraclePrefix", StringValue(config.oraclePrefix));
    ingressHelper.SetAttribute("RequestedManifestSize", UintegerValue(config.manifestSize));
    ingressHelper.SetAttribute("MaxProbeBudget", UintegerValue(config.probeBudget));
    ingressHelper.SetAttribute("QueryLimit", UintegerValue(config.queryLimitPerIngress));
    ingressHelper.SetAttribute("ReplyTimeout", StringValue("300ms"));
    ingressHelper.SetAttribute("StrategyMode", StringValue(strategyMode));
    auto apps = ingressHelper.Install(Names::Find<Node>(GetFieldOrEmpty(row, "node_id")));
    apps.Start(Seconds(0.0));
    apps.Stop(Seconds(config.stopSeconds));
  }

  std::map<std::string, uint32_t> objectsByDomain;
  std::map<std::string, uint32_t> summariesByDomain;
  std::map<std::string, uint32_t> summaryBytesByDomain;
  std::set<std::string> domainIds;
  for (const auto& row : objectRows) {
    const auto domainId = GetFieldOrEmpty(row, "domain_id");
    ++objectsByDomain[domainId];
    if (!domainId.empty()) {
      domainIds.insert(domainId);
    }
  }
  for (const auto& row : summaryRows) {
    const auto domainId = GetFieldOrEmpty(row, "domain_id");
    ++summariesByDomain[domainId];
    summaryBytesByDomain[domainId] += estimateSummaryBytes(row);
    if (!domainId.empty()) {
      domainIds.insert(domainId);
    }
  }
  if (domainIds.empty()) {
    for (const auto& row : topologyRows) {
      if (!GetFieldOrEmpty(row, "domain_id").empty()) {
        domainIds.insert(GetFieldOrEmpty(row, "domain_id"));
      }
    }
  }

  const std::vector<std::string> orderedDomains(domainIds.begin(), domainIds.end());
  const auto stateHeader =
    std::vector<std::string>{"timestamp_ms", "scheme", "domain_id", "num_exported_summaries",
                             "exported_summary_bytes", "summary_updates_sent",
                             "objects_in_domain", "domains_total", "budget",
                             "topology_id", "scaling_axis", "scaling_value"};
  auto appendStateRow = [&] (const std::string& domainId, uint32_t exportedSummaries,
                             uint32_t exportedBytes, uint32_t summaryUpdatesSent,
                             uint32_t objectsInDomain, uint32_t domainsTotal,
                             const std::string& scalingAxis, uint32_t scalingValue) {
    appendCsvRow(stateLogPath, stateHeader,
                 {"0", config.scheme, domainId, std::to_string(exportedSummaries),
                  std::to_string(exportedBytes), std::to_string(summaryUpdatesSent),
                  std::to_string(objectsInDomain), std::to_string(domainsTotal),
                  std::to_string(config.exportBudget), config.topologyId, scalingAxis,
                  std::to_string(scalingValue)});
  };

  if (mode == HiRouteScenarioMode::StateScaling) {
    auto objectsPerDomainSweep = parseUintList(config.objectsPerDomainSweep);
    auto objectScales = parseDoubleList(config.objectScales);
    if (objectScales.empty() && objectsPerDomainSweep.empty()) {
      objectScales = {0.25, 0.5, 0.75, 1.0};
    }
    auto domainSweepCounts = parseUintList(config.domainSweepCounts);
    if (domainSweepCounts.empty()) {
      domainSweepCounts = defaultDomainSweepCounts(static_cast<uint32_t>(orderedDomains.size()));
    }

    if (!objectsPerDomainSweep.empty()) {
      for (uint32_t objectsPerDomain : objectsPerDomainSweep) {
        for (const auto& domainId : orderedDomains) {
          const auto availableSummaries = summariesByDomain[domainId];
          const auto availableBytes = summaryBytesByDomain[domainId];
          const auto exportedSummaries = std::min(availableSummaries, config.exportBudget);
          const auto exportedBytes = availableSummaries == 0 ? 0 :
            static_cast<uint32_t>(std::llround(
              (static_cast<double>(availableBytes) / availableSummaries) * exportedSummaries));
          appendStateRow(domainId, exportedSummaries, exportedBytes, exportedSummaries,
                         objectsPerDomain, static_cast<uint32_t>(orderedDomains.size()),
                         "objects_per_domain", objectsPerDomain);
        }
      }
    }
    else {
      for (double scale : objectScales) {
        const auto scaledMeanObjects = orderedDomains.empty() ? 0u : static_cast<uint32_t>(std::llround(
          (static_cast<double>(objectRows.size()) / orderedDomains.size()) * scale));
        for (const auto& domainId : orderedDomains) {
          const auto availableSummaries = summariesByDomain[domainId];
          const auto availableBytes = summaryBytesByDomain[domainId];
          const auto exportedSummaries = std::min(availableSummaries, config.exportBudget);
          const auto exportedBytes = availableSummaries == 0 ? 0 :
            static_cast<uint32_t>(std::llround(
              (static_cast<double>(availableBytes) / availableSummaries) * exportedSummaries));
          const auto scaledObjects = std::max(1u, static_cast<uint32_t>(
            std::llround(objectsByDomain[domainId] * scale)));
          appendStateRow(domainId, exportedSummaries, exportedBytes, exportedSummaries,
                         scaledObjects, static_cast<uint32_t>(orderedDomains.size()),
                         "objects_per_domain", std::max(1u, scaledMeanObjects));
        }
      }
    }

    for (uint32_t activeDomains : domainSweepCounts) {
      const auto clampedDomains =
        std::min(activeDomains, static_cast<uint32_t>(orderedDomains.size()));
      for (size_t index = 0; index < orderedDomains.size() && index < clampedDomains; ++index) {
        const auto& domainId = orderedDomains[index];
        const auto availableSummaries = summariesByDomain[domainId];
        const auto availableBytes = summaryBytesByDomain[domainId];
        const auto exportedSummaries = std::min(availableSummaries, config.exportBudget);
        const auto exportedBytes = availableSummaries == 0 ? 0 :
          static_cast<uint32_t>(std::llround(
            (static_cast<double>(availableBytes) / availableSummaries) * exportedSummaries));
        appendStateRow(domainId, exportedSummaries, exportedBytes, exportedSummaries,
                       objectsByDomain[domainId], clampedDomains,
                       "domain_count", clampedDomains);
      }
    }

    ensureCsvHeader(config.runDir + "/query_log.csv",
                    {"query_id", "scheme", "ingress_node_id", "start_time_ms", "remote_probes",
                     "discovery_bytes", "candidate_shrinkage_ratio", "latency_ms",
                     "success_at_1", "manifest_hit_at_r", "ndcg_at_r", "failure_type",
                     "fetched_object_id"});
    ensureCsvHeader(config.runDir + "/probe_log.csv",
                    {"query_id", "scheme", "probe_index", "controller_prefix", "cell_id",
                     "reply_entries", "selected_object_id", "success"});
    ensureCsvHeader(config.runDir + "/search_trace.csv",
                    {"query_id", "scheme", "stage", "candidate_count", "selected_count",
                     "frontier_size", "timestamp_ms"});
    Simulator::Destroy();
    return 0;
  }
  else {
    for (const auto& domainId : orderedDomains) {
      appendStateRow(domainId, summariesByDomain[domainId], summaryBytesByDomain[domainId],
                     summariesByDomain[domainId], objectsByDomain[domainId],
                     static_cast<uint32_t>(orderedDomains.size()), "snapshot",
                     objectsByDomain[domainId]);
    }
  }

  if (mode == HiRouteScenarioMode::LinkFailure) {
    const auto selectedDomain =
      targetFailureDomain.empty() ? firstControllerDomain : targetFailureDomain;
    const auto nodeIdIt = controllerNodeIdByDomain.find(selectedDomain);
    std::vector<std::string> neighbors;
    if (nodeIdIt != controllerNodeIdByDomain.end()) {
      neighbors = adjacentNodes(config.topologyPath, nodeIdIt->second);
    }

    if (neighbors.empty()) {
      const auto link = firstLinkPair(config.topologyPath);
      auto left = Names::Find<Node>(link.first);
      auto right = Names::Find<Node>(link.second);
      Simulator::Schedule(Seconds(config.failureTime), LinkControlHelper::FailLink, left, right);
      Simulator::Schedule(Seconds(config.recoveryTime), LinkControlHelper::UpLink, left, right);
      appendCsvRow(failureLogPath,
                   {"timestamp_s", "event_type", "node_a", "node_b", "domain_id", "details"},
                   {std::to_string(config.failureTime), "link_down", link.first, link.second,
                    selectedDomain, "fallback topology link disabled"});
      appendCsvRow(failureLogPath,
                   {"timestamp_s", "event_type", "node_a", "node_b", "domain_id", "details"},
                   {std::to_string(config.recoveryTime), "link_up", link.first, link.second,
                    selectedDomain, "fallback topology link restored"});
    }
    else {
      const auto controllerNodeId = nodeIdIt->second;
      auto controllerNode = Names::Find<Node>(controllerNodeId);
      for (const auto& neighborId : neighbors) {
        auto neighborNode = Names::Find<Node>(neighborId);
        Simulator::Schedule(Seconds(config.failureTime), LinkControlHelper::FailLink,
                            controllerNode, neighborNode);
        Simulator::Schedule(Seconds(config.recoveryTime), LinkControlHelper::UpLink,
                            controllerNode, neighborNode);
        appendCsvRow(failureLogPath,
                     {"timestamp_s", "event_type", "node_a", "node_b", "domain_id", "details"},
                     {std::to_string(config.failureTime), "link_down", controllerNodeId, neighborId,
                      selectedDomain, "target controller adjacency disabled"});
        appendCsvRow(failureLogPath,
                     {"timestamp_s", "event_type", "node_a", "node_b", "domain_id", "details"},
                     {std::to_string(config.recoveryTime), "link_up", controllerNodeId, neighborId,
                      selectedDomain, "target controller adjacency restored"});
      }
    }
  }
  else if (mode == HiRouteScenarioMode::Staleness) {
    appendCsvRow(failureLogPath,
                 {"timestamp_s", "event_type", "node_a", "node_b", "domain_id", "details"},
                 {std::to_string(config.failureTime), "staleness_window", "", "",
                  targetFailureDomain.empty() ? firstControllerDomain : targetFailureDomain,
                  "target domain controller manifests drop top entry probabilistically"});
  }

  GlobalRoutingHelper::CalculateRoutes();

  Simulator::Stop(Seconds(config.stopSeconds));
  Simulator::Run();
  Simulator::Destroy();
  return 0;
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_SCENARIO_COMMON_HPP
