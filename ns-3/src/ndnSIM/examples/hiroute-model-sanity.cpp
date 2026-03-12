/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "ns3/command-line.h"
#include "ns3/nstime.h"
#include "ns3/ndnSIM/model/hiroute-discovery-engine.hpp"
#include "ns3/ndnSIM/model/hiroute-manifest-entry.hpp"
#include "ns3/ndnSIM/model/hiroute-reliability-cache.hpp"
#include "ns3/ndnSIM/model/hiroute-summary-store.hpp"
#include "ns3/ndnSIM/model/hiroute-tlv.hpp"

#include <iostream>
#include <string>

namespace ndn_hiroute = ns3::ndn::hiroute;

int
main(int argc, char* argv[])
{
  std::string summaryCsv = "../data/processed/ndnsim/hslsa_export.csv";
  std::string zoneConstraint = "domain-01-zone-01";
  std::string zoneTypeConstraint = "school_area";
  std::string serviceConstraint = "air_quality_co2";
  std::string freshnessConstraint = "realtime";
  uint32_t refinementBudget = 4;

  ns3::CommandLine cmd;
  cmd.AddValue("summaryCsv", "Path to hslsa_export.csv", summaryCsv);
  cmd.AddValue("zoneConstraint", "Zone constraint", zoneConstraint);
  cmd.AddValue("zoneTypeConstraint", "Zone type constraint", zoneTypeConstraint);
  cmd.AddValue("serviceConstraint", "Service constraint", serviceConstraint);
  cmd.AddValue("freshnessConstraint", "Freshness constraint", freshnessConstraint);
  cmd.AddValue("refinementBudget", "Candidate refinement budget", refinementBudget);
  cmd.Parse(argc, argv);

  ndn_hiroute::HiRouteSummaryStore summaryStore;
  summaryStore.LoadFromCsv(summaryCsv);

  ndn_hiroute::HiRouteDiscoveryRequest request;
  request.queryId = "sanity-query";
  request.queryEmbeddingRow = 0;
  request.predicate.zoneConstraint = zoneConstraint;
  request.predicate.zoneTypeConstraint = zoneTypeConstraint;
  request.predicate.serviceConstraint = serviceConstraint;
  request.predicate.freshnessConstraint = freshnessConstraint;
  request.refinementBudget = refinementBudget;
  request.requestedManifestSize = 3;

  const auto encodedRequest = ndn_hiroute::HiRouteTlv::EncodeDiscoveryRequest(request);
  const auto decodedRequest = ndn_hiroute::HiRouteTlv::DecodeDiscoveryRequest(encodedRequest);

  ndn_hiroute::HiRouteReliabilityCache reliabilityCache;
  reliabilityCache.ObserveResult("domain-01", "domain-01-root", true);

  ndn_hiroute::HiRouteDiscoveryEngine engine;
  const auto candidates =
    engine.SelectCandidates(summaryStore, decodedRequest, reliabilityCache, refinementBudget);

  ndn_hiroute::HiRouteDiscoveryReply reply;
  for (size_t i = 0; i < candidates.size() && i < 3; ++i) {
    ndn_hiroute::HiRouteManifestEntry entry;
    entry.canonicalName = candidates[i].summary->controllerPrefix + "/candidate/" +
                          candidates[i].summary->cellId;
    entry.confidenceScore = candidates[i].totalScore;
    entry.domainId = candidates[i].summary->domainId;
    entry.cellId = candidates[i].summary->cellId;
    entry.objectId = "synthetic-object-" + std::to_string(i + 1);
    reply.manifest.push_back(entry);
  }

  const auto encodedReply = ndn_hiroute::HiRouteTlv::EncodeDiscoveryReply(reply);
  const auto decodedReply = ndn_hiroute::HiRouteTlv::DecodeDiscoveryReply(encodedReply);

  std::cout << "summaries=" << summaryStore.GetEntries().size() << '\n';
  std::cout << "candidates=" << candidates.size() << '\n';
  if (!candidates.empty()) {
    std::cout << "top-cell=" << candidates.front().summary->cellId << '\n';
    std::cout << "top-score=" << candidates.front().totalScore << '\n';
  }
  std::cout << "manifest=" << decodedReply.manifest.size() << '\n';
  return 0;
}
