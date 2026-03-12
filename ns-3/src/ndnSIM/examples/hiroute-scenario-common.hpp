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
#include <map>
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
    output << values[i];
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
  cmd.AddValue("scheme", "exact, flood, flat_iroute, oracle, hiroute", config.scheme);
  cmd.AddValue("stopSeconds", "Simulation stop time", config.stopSeconds);
  cmd.AddValue("failureTime", "Failure injection time", config.failureTime);
  cmd.AddValue("recoveryTime", "Link recovery time", config.recoveryTime);
  cmd.AddValue("staleDropProbability", "Probability of dropping the best manifest entry after staleness",
               config.staleDropProbability);
  cmd.AddValue("manifestSize", "Discovery manifest size", config.manifestSize);
  cmd.AddValue("probeBudget", "Discovery probe budget", config.probeBudget);
  cmd.AddValue("queryLimitPerIngress", "Maximum queries scheduled on each ingress node",
               config.queryLimitPerIngress);
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

  std::map<std::string, Ptr<Node>> controllerByDomain;
  std::string firstControllerDomain;
  Ptr<Node> firstControllerNode;

  const auto stateLogPath = config.runDir + "/state_log.csv";
  const auto failureLogPath = config.runDir + "/failure_event_log.csv";
  ensureCsvHeader(failureLogPath,
                  {"timestamp_s", "event_type", "node_a", "node_b", "domain_id", "details"});

  std::vector<Ptr<Node>> ingressNodes;
  uint32_t controllerCount = 0;
  for (const auto& row : topologyRows) {
    if (GetFieldOrEmpty(row, "role") == "controller") {
      auto node = Names::Find<Node>(GetFieldOrEmpty(row, "node_id"));
      controllerByDomain[GetFieldOrEmpty(row, "domain_id")] = node;
      ++controllerCount;
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
      if (mode == HiRouteScenarioMode::Staleness) {
        controllerHelper.SetAttribute("StaleAfter",
                                      StringValue(std::to_string(config.failureTime) + "s"));
        controllerHelper.SetAttribute("StaleDropProbability",
                                      DoubleValue(config.staleDropProbability));
      }
      auto apps = controllerHelper.Install(node);
      apps.Start(Seconds(0.0));
      if (mode == HiRouteScenarioMode::DomainFailure &&
          GetFieldOrEmpty(row, "domain_id") == firstControllerDomain) {
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
    else if (GetFieldOrEmpty(row, "role") == "ingress") {
      ingressNodes.push_back(Names::Find<Node>(GetFieldOrEmpty(row, "node_id")));
    }
  }

  if (firstControllerNode == nullptr) {
    throw std::runtime_error("no controller nodes found in topology mapping");
  }

  AppHelper oracleHelper("ns3::ndn::OracleControllerApp");
  oracleHelper.SetAttribute("Prefix", StringValue(config.oraclePrefix));
  oracleHelper.SetAttribute("ObjectsCsvPath", StringValue(config.objectsCsv));
  oracleHelper.SetAttribute("ControllerLocalIndexCsvPath", StringValue(config.controllerLocalIndexCsv));
  oracleHelper.SetAttribute("ManifestSize", UintegerValue(config.manifestSize));
  auto oracleApps = oracleHelper.Install(firstControllerNode);
  oracleApps.Start(Seconds(0.0));
  oracleApps.Stop(Seconds(config.stopSeconds));
  routingHelper.AddOrigin(config.oraclePrefix, firstControllerNode);

  for (const auto& row : objectRows) {
    const auto domainIt = controllerByDomain.find(GetFieldOrEmpty(row, "domain_id"));
    if (domainIt == controllerByDomain.end()) {
      continue;
    }
    routingHelper.AddOrigin(GetFieldOrEmpty(row, "canonical_name"), domainIt->second);
  }

  uint32_t ingressCount = 0;
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
    else if (config.scheme == "hiroute" || config.scheme == "oracle") {
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
    ++ingressCount;
  }

  appendCsvRow(stateLogPath,
               {"scenario", "scheme", "topology_id", "node_count", "controller_count",
                "ingress_count", "summary_count", "object_count"},
               {toString(mode),
                config.scheme,
                config.topologyId,
                std::to_string(NodeList::GetNNodes()),
                std::to_string(controllerCount),
                std::to_string(ingressCount),
                std::to_string(summaryRows.size()),
                std::to_string(objectRows.size())});

  if (mode == HiRouteScenarioMode::LinkFailure) {
    const auto link = firstLinkPair(config.topologyPath);
    auto left = Names::Find<Node>(link.first);
    auto right = Names::Find<Node>(link.second);
    Simulator::Schedule(Seconds(config.failureTime), LinkControlHelper::FailLink, left, right);
    Simulator::Schedule(Seconds(config.recoveryTime), LinkControlHelper::UpLink, left, right);
    appendCsvRow(failureLogPath,
                 {"timestamp_s", "event_type", "node_a", "node_b", "domain_id", "details"},
                 {std::to_string(config.failureTime), "link_down", link.first, link.second, "",
                  "inter-domain link disabled"});
    appendCsvRow(failureLogPath,
                 {"timestamp_s", "event_type", "node_a", "node_b", "domain_id", "details"},
                 {std::to_string(config.recoveryTime), "link_up", link.first, link.second, "",
                  "inter-domain link restored"});
  }
  else if (mode == HiRouteScenarioMode::Staleness) {
    appendCsvRow(failureLogPath,
                 {"timestamp_s", "event_type", "node_a", "node_b", "domain_id", "details"},
                 {std::to_string(config.failureTime), "staleness_window", "", "", "",
                  "controller manifests drop top entry probabilistically"});
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
