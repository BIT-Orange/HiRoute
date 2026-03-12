/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "hiroute-controller-app.hpp"

#include "ns3/boolean.h"
#include "ns3/log.h"
#include "ns3/double.h"
#include "ns3/string.h"
#include "ns3/uinteger.h"

#include "ns3/ndnSIM/helper/ndn-fib-helper.hpp"
#include "ns3/ndnSIM/helper/ndn-stack-helper.hpp"

#include <algorithm>
#include <cstdlib>
#include <limits>
#include <map>
#include <set>

NS_LOG_COMPONENT_DEFINE("ndn.HiRouteControllerApp");

namespace ns3 {
namespace ndn {
namespace hiroute {

NS_OBJECT_ENSURE_REGISTERED(HiRouteControllerApp);

TypeId
HiRouteControllerApp::GetTypeId()
{
  static TypeId tid =
    TypeId("ns3::ndn::HiRouteControllerApp")
      .SetGroupName("Ndn")
      .SetParent<App>()
      .AddConstructor<HiRouteControllerApp>()
      .AddAttribute("Prefix", "Controller discovery prefix",
                    StringValue("/hiroute/domain/controller"),
                    MakeStringAccessor(&HiRouteControllerApp::m_prefix), MakeStringChecker())
      .AddAttribute("DomainId", "Logical domain identifier",
                    StringValue("domain-01"),
                    MakeStringAccessor(&HiRouteControllerApp::m_domainId), MakeStringChecker())
      .AddAttribute("ObjectsCsvPath", "Path to objects_master.csv",
                    StringValue("../data/processed/ndnsim/objects_master.csv"),
                    MakeStringAccessor(&HiRouteControllerApp::m_objectsCsvPath), MakeStringChecker())
      .AddAttribute("ControllerLocalIndexCsvPath", "Path to controller_local_index.csv",
                    StringValue("../data/processed/ndnsim/controller_local_index.csv"),
                    MakeStringAccessor(&HiRouteControllerApp::m_controllerLocalIndexCsvPath),
                    MakeStringChecker())
      .AddAttribute("ManifestSize", "Maximum number of canonical names returned per discovery",
                    UintegerValue(4),
                    MakeUintegerAccessor(&HiRouteControllerApp::m_manifestSize),
                    MakeUintegerChecker<uint32_t>())
      .AddAttribute("StaleAfter", "Time after which this controller starts serving stale manifests",
                    StringValue("0s"),
                    MakeTimeAccessor(&HiRouteControllerApp::m_staleAfter), MakeTimeChecker())
      .AddAttribute("StaleDropProbability", "Probability of dropping the top manifest entry after stale time",
                    DoubleValue(0.0),
                    MakeDoubleAccessor(&HiRouteControllerApp::m_staleDropProbability),
                    MakeDoubleChecker<double>(0.0, 1.0))
      .AddAttribute("OracleMode", "Return a manifest from all globally visible objects",
                    BooleanValue(false),
                    MakeBooleanAccessor(&HiRouteControllerApp::m_oracleMode), MakeBooleanChecker());
  return tid;
}

HiRouteControllerApp::HiRouteControllerApp()
  : m_rand(CreateObject<UniformRandomVariable>())
{
}

void
HiRouteControllerApp::StartApplication()
{
  App::StartApplication();
  loadInputs();
  FibHelper::AddRoute(GetNode(), m_prefix, m_face, 0);
  for (const auto& item : m_objectsByName) {
    FibHelper::AddRoute(GetNode(), item.first, m_face, 0);
  }
}

void
HiRouteControllerApp::StopApplication()
{
  App::StopApplication();
}

void
HiRouteControllerApp::SetOracleMode(bool enabled)
{
  m_oracleMode = enabled;
}

void
HiRouteControllerApp::SetPrefix(const std::string& prefix)
{
  m_prefix = prefix;
}

void
HiRouteControllerApp::OnInterest(shared_ptr<const Interest> interest)
{
  if (!m_active) {
    return;
  }
  App::OnInterest(interest);

  const auto interestName = interest->getName().toUri();
  auto objectIt = m_objectsByName.find(interestName);
  if (objectIt != m_objectsByName.end()) {
    sendObjectData(interest, objectIt->second);
    return;
  }

  if (!Name(m_prefix).isPrefixOf(interest->getName()) || !interest->hasApplicationParameters()) {
    return;
  }

  const auto request =
    HiRouteTlv::DecodeDiscoveryRequest(interest->getApplicationParameters().blockFromValue());
  HiRouteDiscoveryReply reply;
  reply.manifest = buildManifest(request);
  sendDiscoveryReply(interest, reply);
}

void
HiRouteControllerApp::loadInputs()
{
  m_objectsById.clear();
  m_objectsByName.clear();
  m_objectsByCell.clear();
  m_rankByCellObject.clear();

  for (const auto& row : HiRouteDatasetReader::ReadCsvRows(m_objectsCsvPath)) {
    const auto object = HiRouteObjectRecord::FromCsvRow(row);
    if (!m_oracleMode && object.domainId != m_domainId) {
      continue;
    }
    m_objectsById[object.objectId] = object;
    m_objectsByName[object.canonicalName] = object;
  }

  for (const auto& row : HiRouteDatasetReader::ReadCsvRows(m_controllerLocalIndexCsvPath)) {
    if (!m_oracleMode && GetFieldOrEmpty(row, "domain_id") != m_domainId) {
      continue;
    }
    const auto objectId = GetFieldOrEmpty(row, "object_id");
    if (m_objectsById.count(objectId) == 0) {
      continue;
    }
    const auto cellId = GetFieldOrEmpty(row, "cell_id");
    m_objectsByCell[cellId].push_back(objectId);
    const auto key = cellId + "::" + objectId;
    m_rankByCellObject[key] =
      static_cast<uint32_t>(std::strtoul(GetFieldOrEmpty(row, "local_rank_hint").c_str(), nullptr, 10));
  }
}

bool
HiRouteControllerApp::matchesPredicate(const HiRouteObjectRecord& object,
                                       const HiRoutePredicateHeader& predicate) const
{
  return (predicate.zoneConstraint.empty() || object.zoneId == predicate.zoneConstraint) &&
         (predicate.zoneTypeConstraint.empty() || object.zoneType == predicate.zoneTypeConstraint) &&
         (predicate.serviceConstraint.empty() || object.serviceClass == predicate.serviceConstraint) &&
         (predicate.freshnessConstraint.empty() ||
          object.freshnessClass == predicate.freshnessConstraint);
}

std::vector<HiRouteManifestEntry>
HiRouteControllerApp::buildManifest(const HiRouteDiscoveryRequest& request) const
{
  std::vector<RankedObject> ranked;
  std::vector<std::string> objectIds;
  std::map<std::string, uint32_t> bestRankByObjectId;

  auto cellIt = m_objectsByCell.find(request.frontierHintCellId);
  if (!request.frontierHintCellId.empty() && cellIt != m_objectsByCell.end()) {
    objectIds = cellIt->second;
    for (const auto& objectId : objectIds) {
      auto rankIt = m_rankByCellObject.find(request.frontierHintCellId + "::" + objectId);
      if (rankIt != m_rankByCellObject.end()) {
        bestRankByObjectId[objectId] = rankIt->second;
      }
    }
  }
  else if (!request.frontierHintCellId.empty()) {
    const auto descendantPrefix = request.frontierHintCellId + "-";
    std::set<std::string> dedup;
    for (const auto& item : m_objectsByCell) {
      if (item.first != request.frontierHintCellId &&
          item.first.rfind(descendantPrefix, 0) != 0) {
        continue;
      }
      for (const auto& objectId : item.second) {
        dedup.insert(objectId);
        auto rankIt = m_rankByCellObject.find(item.first + "::" + objectId);
        if (rankIt == m_rankByCellObject.end()) {
          continue;
        }
        auto bestIt = bestRankByObjectId.find(objectId);
        if (bestIt == bestRankByObjectId.end() || rankIt->second < bestIt->second) {
          bestRankByObjectId[objectId] = rankIt->second;
        }
      }
    }
    objectIds.assign(dedup.begin(), dedup.end());
    if (objectIds.empty()) {
      objectIds.reserve(m_objectsById.size());
      for (const auto& item : m_objectsById) {
        objectIds.push_back(item.first);
      }
    }
  }
  else {
    objectIds.reserve(m_objectsById.size());
    for (const auto& item : m_objectsById) {
      objectIds.push_back(item.first);
    }
  }

  for (const auto& objectId : objectIds) {
    auto objectIt = m_objectsById.find(objectId);
    if (objectIt == m_objectsById.end()) {
      continue;
    }
    const auto& object = objectIt->second;
    if (!matchesPredicate(object, request.predicate)) {
      continue;
    }

    double score = 1.0;
    auto rankIt = bestRankByObjectId.find(objectId);
    if (rankIt != bestRankByObjectId.end()) {
      score += 1.0 / (1.0 + static_cast<double>(rankIt->second));
    }
    if (object.serviceClass == request.predicate.serviceConstraint) {
      score += 0.5;
    }
    if (object.freshnessClass == request.predicate.freshnessConstraint) {
      score += 0.25;
    }
    if (object.zoneType == request.predicate.zoneTypeConstraint) {
      score += 0.25;
    }
    ranked.push_back({object, score});
  }

  std::sort(ranked.begin(), ranked.end(), [&] (const RankedObject& left, const RankedObject& right) {
    if (left.score != right.score) {
      return left.score > right.score;
    }
    return left.object.objectId < right.object.objectId;
  });

  const auto resultLimit = request.requestedManifestSize == 0 ?
    m_manifestSize :
    std::min<uint32_t>(m_manifestSize, request.requestedManifestSize);
  if (ranked.size() > resultLimit) {
    ranked.resize(resultLimit);
  }

  std::vector<HiRouteManifestEntry> manifest;
  manifest.reserve(ranked.size());
  for (const auto& item : ranked) {
    HiRouteManifestEntry entry;
    entry.canonicalName = item.object.canonicalName;
    entry.confidenceScore = item.score;
    entry.domainId = item.object.domainId;
    entry.cellId = request.frontierHintCellId;
    entry.objectId = item.object.objectId;
    manifest.push_back(entry);
  }

  if (m_staleAfter > Seconds(0) && Simulator::Now() >= m_staleAfter && !manifest.empty() &&
      m_rand->GetValue(0.0, 1.0) < m_staleDropProbability) {
    manifest.erase(manifest.begin());
  }
  return manifest;
}

void
HiRouteControllerApp::sendDiscoveryReply(shared_ptr<const Interest> interest,
                                         const HiRouteDiscoveryReply& reply)
{
  auto data = std::make_shared<Data>(interest->getName());
  data->setFreshnessPeriod(time::milliseconds(250));
  data->setContent(HiRouteTlv::EncodeDiscoveryReply(reply));
  StackHelper::getKeyChain().sign(*data);
  m_transmittedDatas(data, this, m_face);
  m_appLink->onReceiveData(*data);
}

void
HiRouteControllerApp::sendObjectData(shared_ptr<const Interest> interest,
                                     const HiRouteObjectRecord& object)
{
  auto data = std::make_shared<Data>(interest->getName());
  data->setFreshnessPeriod(time::milliseconds(500));
  auto payload = std::make_shared< ::ndn::Buffer>(std::max<uint32_t>(1u, object.payloadSizeBytes));
  data->setContent(payload);
  StackHelper::getKeyChain().sign(*data);
  m_transmittedDatas(data, this, m_face);
  m_appLink->onReceiveData(*data);
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
