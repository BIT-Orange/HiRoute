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
#include <cstdint>
#include <fstream>
#include <limits>
#include <map>
#include <sstream>
#include <set>
#include <stdexcept>

NS_LOG_COMPONENT_DEFINE("ndn.HiRouteControllerApp");

namespace ns3 {
namespace ndn {
namespace hiroute {

namespace {

uint32_t
StableSlotForToken(const std::string& token, uint32_t modulo)
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

std::string
CanonicalZoneToken(const std::string& zoneId)
{
  const auto marker = zoneId.rfind("-zone-");
  if (marker == std::string::npos) {
    return zoneId;
  }
  return zoneId.substr(marker + 1);
}

bool
MatchesZoneConstraint(const std::string& objectZoneId, const std::string& constraint)
{
  if (constraint.empty()) {
    return true;
  }

  const auto canonical = CanonicalZoneToken(objectZoneId);
  std::stringstream input(constraint);
  std::string token;
  while (std::getline(input, token, ';')) {
    if (!token.empty() && (token == objectZoneId || token == canonical)) {
      return true;
    }
  }
  return false;
}

bool
FileNeedsHeader(const std::string& path)
{
  std::ifstream input(path.c_str());
  return !input.good() || input.peek() == std::ifstream::traits_type::eof();
}

std::string
EscapeCsv(std::string value)
{
  bool needsQuotes = false;
  for (char ch : value) {
    if (ch == ',' || ch == '"' || ch == '\n' || ch == '\r') {
      needsQuotes = true;
      break;
    }
  }
  if (!needsQuotes) {
    return value;
  }

  std::string escaped;
  escaped.reserve(value.size() + 4);
  escaped.push_back('"');
  for (char ch : value) {
    if (ch == '"') {
      escaped.push_back('"');
    }
    escaped.push_back(ch);
  }
  escaped.push_back('"');
  return escaped;
}

void
AppendCsvRow(const std::string& path, const std::vector<std::string>& header,
             const std::vector<std::string>& values)
{
  const bool writeHeader = FileNeedsHeader(path);
  std::ofstream output(path.c_str(), std::ios::out | std::ios::app);
  if (!output.good()) {
    throw std::runtime_error("failed to open controller debug csv: " + path);
  }
  if (writeHeader) {
    for (size_t index = 0; index < header.size(); ++index) {
      if (index != 0) {
        output << ',';
      }
      output << header[index];
    }
    output << '\n';
  }
  for (size_t index = 0; index < values.size(); ++index) {
    if (index != 0) {
      output << ',';
    }
    output << EscapeCsv(values[index]);
  }
  output << '\n';
}

std::vector<std::string>
SplitSemicolonTokens(const std::string& value)
{
  std::vector<std::string> tokens;
  std::stringstream input(value);
  std::string token;
  while (std::getline(input, token, ';')) {
    if (!token.empty()) {
      tokens.push_back(token);
    }
  }
  return tokens;
}

std::string
DomainRootForCellId(const std::string& cellId)
{
  const auto firstDash = cellId.find('-');
  if (firstDash == std::string::npos) {
    return std::string();
  }
  const auto secondDash = cellId.find('-', firstDash + 1);
  if (secondDash == std::string::npos) {
    return std::string();
  }
  return cellId.substr(0, secondDash) + "-root";
}

} // namespace

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
      .AddAttribute("QrelsObjectCsvPath", "Path to qrels_object.csv used by the centralized oracle",
                    StringValue("../data/processed/eval/qrels_object.csv"),
                    MakeStringAccessor(&HiRouteControllerApp::m_qrelsObjectCsvPath),
                    MakeStringChecker())
      .AddAttribute("ManifestDebugCsvPath", "Optional csv path for controller manifest debug rows",
                    StringValue(""),
                    MakeStringAccessor(&HiRouteControllerApp::m_manifestDebugCsvPath),
                    MakeStringChecker())
      .AddAttribute("ManifestSize", "Maximum number of canonical names returned per discovery",
                    UintegerValue(4),
                    MakeUintegerAccessor(&HiRouteControllerApp::m_manifestSize),
                    MakeUintegerChecker<uint32_t>())
      .AddAttribute("ServeDiscovery", "Whether this app answers discovery Interests",
                    BooleanValue(true),
                    MakeBooleanAccessor(&HiRouteControllerApp::m_serveDiscovery),
                    MakeBooleanChecker())
      .AddAttribute("ServeObjects", "Whether this app answers canonical object Interests",
                    BooleanValue(true),
                    MakeBooleanAccessor(&HiRouteControllerApp::m_serveObjects),
                    MakeBooleanChecker())
      .AddAttribute("AdvertiseObjects", "Whether this app advertises object name origins",
                    BooleanValue(true),
                    MakeBooleanAccessor(&HiRouteControllerApp::m_advertiseObjects),
                    MakeBooleanChecker())
      .AddAttribute("ObjectShardModulo", "Shard modulo used to co-locate objects on producer hosts",
                    UintegerValue(0),
                    MakeUintegerAccessor(&HiRouteControllerApp::m_objectShardModulo),
                    MakeUintegerChecker<uint32_t>())
      .AddAttribute("ObjectShardIndex", "Shard index used to co-locate objects on producer hosts",
                    UintegerValue(0),
                    MakeUintegerAccessor(&HiRouteControllerApp::m_objectShardIndex),
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
  if (m_serveDiscovery) {
    FibHelper::AddRoute(GetNode(), m_prefix, m_face, 0);
  }
  if (m_advertiseObjects) {
    for (const auto& item : m_objectsByName) {
      FibHelper::AddRoute(GetNode(), item.first, m_face, 0);
    }
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
  if (m_serveObjects && objectIt != m_objectsByName.end()) {
    sendObjectData(interest, objectIt->second);
    return;
  }

  if (!m_serveDiscovery || !Name(m_prefix).isPrefixOf(interest->getName()) ||
      !interest->hasApplicationParameters()) {
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
  const bool oracleController = m_oracleMode || m_prefix.find("/oracle/") != std::string::npos;
  m_objectsById.clear();
  m_objectsByName.clear();
  m_objectsByCell.clear();
  m_objectsByFrontierHint.clear();
  m_concreteCellsByFrontierHint.clear();
  m_oracleRankedQrels.clear();
  m_rankByCellObject.clear();
  m_rankByFrontierObject.clear();
  m_hasExplicitAncestorFrontierIndex = false;

  for (const auto& row : HiRouteDatasetReader::ReadCsvRows(m_objectsCsvPath)) {
    const auto object = HiRouteObjectRecord::FromCsvRow(row);
    if (!oracleController && object.domainId != m_domainId) {
      continue;
    }
    if (m_objectShardModulo > 0 &&
        StableSlotForToken(object.objectId, m_objectShardModulo) != m_objectShardIndex) {
      continue;
    }
    m_objectsById[object.objectId] = object;
    m_objectsByName[object.canonicalName] = object;
  }

  std::map<std::string, std::set<std::string>> seenObjectsByFrontierHint;
  for (const auto& row : HiRouteDatasetReader::ReadCsvRows(m_controllerLocalIndexCsvPath)) {
    if (!oracleController && GetFieldOrEmpty(row, "domain_id") != m_domainId) {
      continue;
    }
    const auto objectId = GetFieldOrEmpty(row, "object_id");
    if (m_objectsById.count(objectId) == 0) {
      continue;
    }
    const auto cellId = GetFieldOrEmpty(row, "cell_id");
    m_objectsByCell[cellId].push_back(objectId);
    const auto localRankHint =
      static_cast<uint32_t>(std::strtoul(GetFieldOrEmpty(row, "local_rank_hint").c_str(), nullptr, 10));
    const auto key = cellId + "::" + objectId;
    m_rankByCellObject[key] = localRankHint;

    const auto ancestorFrontierIds = SplitSemicolonTokens(GetFieldOrEmpty(row, "ancestor_frontier_ids"));
    if (!ancestorFrontierIds.empty()) {
      m_hasExplicitAncestorFrontierIndex = true;
      for (const auto& frontierHintCellId : ancestorFrontierIds) {
        m_concreteCellsByFrontierHint[frontierHintCellId].insert(cellId);
        if (seenObjectsByFrontierHint[frontierHintCellId].insert(objectId).second) {
          m_objectsByFrontierHint[frontierHintCellId].push_back(objectId);
        }
        const auto frontierKey = frontierHintCellId + "::" + objectId;
        auto bestRankIt = m_rankByFrontierObject.find(frontierKey);
        if (bestRankIt == m_rankByFrontierObject.end() || localRankHint < bestRankIt->second) {
          m_rankByFrontierObject[frontierKey] = localRankHint;
        }
      }
    }
  }

  if (!oracleController) {
    return;
  }

  for (const auto& row : HiRouteDatasetReader::ReadCsvRows(m_qrelsObjectCsvPath)) {
    const auto objectId = GetFieldOrEmpty(row, "object_id");
    if (m_objectsById.count(objectId) == 0) {
      continue;
    }
    const auto relevance =
      static_cast<uint32_t>(std::strtoul(GetFieldOrEmpty(row, "relevance").c_str(), nullptr, 10));
    m_oracleRankedQrels[GetFieldOrEmpty(row, "query_id")].push_back({objectId, relevance});
  }
  for (auto& item : m_oracleRankedQrels) {
    std::sort(item.second.begin(), item.second.end(), [] (const auto& left, const auto& right) {
      if (left.second != right.second) {
        return left.second > right.second;
      }
      return left.first < right.first;
    });
  }
}

bool
HiRouteControllerApp::matchesPredicate(const HiRouteObjectRecord& object,
                                       const HiRoutePredicateHeader& predicate) const
{
  return MatchesZoneConstraint(object.zoneId, predicate.zoneConstraint) &&
         (predicate.zoneTypeConstraint.empty() || object.zoneType == predicate.zoneTypeConstraint) &&
         (predicate.serviceConstraint.empty() || object.serviceClass == predicate.serviceConstraint) &&
         (predicate.freshnessConstraint.empty() ||
         object.freshnessClass == predicate.freshnessConstraint);
}

double
HiRouteControllerApp::semanticFacetScore(const HiRouteObjectRecord& object,
                                         const HiRouteDiscoveryRequest& request) const
{
  if (request.intentFacet.empty()) {
    return 0.0;
  }
  if (object.semanticFacet == request.intentFacet) {
    return 1.0;
  }
  if (object.semanticFacet.empty()) {
    return 0.15;
  }
  return 0.0;
}

double
HiRouteControllerApp::localRankScore(
  const std::string& objectId,
  const std::map<std::string, uint32_t>& bestRankByObjectId) const
{
  auto rankIt = bestRankByObjectId.find(objectId);
  if (rankIt == bestRankByObjectId.end()) {
    return 0.0;
  }
  return 1.0 / (1.0 + static_cast<double>(rankIt->second));
}

HiRouteControllerApp::CandidateLookup
HiRouteControllerApp::resolveCandidateLookup(const std::string& frontierHintCellId) const
{
  CandidateLookup lookup;
  if (frontierHintCellId.empty()) {
    lookup.objectIds.reserve(m_objectsById.size());
    for (const auto& item : m_objectsById) {
      lookup.objectIds.push_back(item.first);
    }
    lookup.localCandidateObjectIds = lookup.objectIds;
    return lookup;
  }

  auto exactCellIt = m_objectsByCell.find(frontierHintCellId);
  lookup.exactCellExists = exactCellIt != m_objectsByCell.end();

  if (m_hasExplicitAncestorFrontierIndex) {
    auto frontierIt = m_objectsByFrontierHint.find(frontierHintCellId);
    if (frontierIt != m_objectsByFrontierHint.end()) {
      lookup.objectIds = frontierIt->second;
      lookup.localCandidateObjectIds = frontierIt->second;
    }
    auto concreteCellsIt = m_concreteCellsByFrontierHint.find(frontierHintCellId);
    if (concreteCellsIt != m_concreteCellsByFrontierHint.end()) {
      lookup.descendantCellCount = concreteCellsIt->second.size();
      if (lookup.exactCellExists && concreteCellsIt->second.count(frontierHintCellId) != 0 &&
          lookup.descendantCellCount > 0) {
        --lookup.descendantCellCount;
      }
    }
    for (const auto& objectId : lookup.objectIds) {
      auto rankIt = m_rankByFrontierObject.find(frontierHintCellId + "::" + objectId);
      if (rankIt != m_rankByFrontierObject.end()) {
        lookup.bestRankByObjectId[objectId] = rankIt->second;
      }
    }
    return lookup;
  }

  if (lookup.exactCellExists) {
    lookup.objectIds = exactCellIt->second;
    lookup.localCandidateObjectIds = lookup.objectIds;
    for (const auto& objectId : lookup.objectIds) {
      auto rankIt = m_rankByCellObject.find(frontierHintCellId + "::" + objectId);
      if (rankIt != m_rankByCellObject.end()) {
        lookup.bestRankByObjectId[objectId] = rankIt->second;
      }
    }
    return lookup;
  }

  const auto descendantPrefix = frontierHintCellId + "-";
  std::set<std::string> dedup;
  for (const auto& item : m_objectsByCell) {
    if (item.first != frontierHintCellId && item.first.rfind(descendantPrefix, 0) != 0) {
      continue;
    }
    if (item.first != frontierHintCellId) {
      ++lookup.descendantCellCount;
    }
    for (const auto& objectId : item.second) {
      dedup.insert(objectId);
      auto rankIt = m_rankByCellObject.find(item.first + "::" + objectId);
      if (rankIt == m_rankByCellObject.end()) {
        continue;
      }
      auto bestIt = lookup.bestRankByObjectId.find(objectId);
      if (bestIt == lookup.bestRankByObjectId.end() || rankIt->second < bestIt->second) {
        lookup.bestRankByObjectId[objectId] = rankIt->second;
      }
    }
  }
  lookup.localCandidateObjectIds.assign(dedup.begin(), dedup.end());
  lookup.objectIds = lookup.localCandidateObjectIds;
  if (lookup.objectIds.empty()) {
    lookup.objectIds.reserve(m_objectsById.size());
    for (const auto& item : m_objectsById) {
      lookup.objectIds.push_back(item.first);
    }
  }
  return lookup;
}

HiRouteControllerApp::CandidateEvaluation
HiRouteControllerApp::evaluateCandidates(const HiRouteDiscoveryRequest& request,
                                         const std::string& frontierHintCellId,
                                         const CandidateLookup& lookup) const
{
  CandidateEvaluation evaluation;
  for (const auto& objectId : lookup.objectIds) {
    auto objectIt = m_objectsById.find(objectId);
    if (objectIt == m_objectsById.end()) {
      continue;
    }
    const auto& object = objectIt->second;
    if (!matchesPredicate(object, request.predicate)) {
      continue;
    }

    double score = 0.75;
    score += localRankScore(objectId, lookup.bestRankByObjectId);
    score += 0.9 * semanticFacetScore(object, request);
    if (!request.predicate.serviceConstraint.empty() &&
        object.serviceClass == request.predicate.serviceConstraint) {
      score += 0.45;
    }
    if (!request.predicate.freshnessConstraint.empty() &&
        object.freshnessClass == request.predicate.freshnessConstraint) {
      score += 0.2;
    }
    if (!request.predicate.zoneTypeConstraint.empty() &&
        object.zoneType == request.predicate.zoneTypeConstraint) {
      score += 0.2;
    }
    if (MatchesZoneConstraint(object.zoneId, request.predicate.zoneConstraint)) {
      score += 0.3;
    }
    evaluation.ranked.push_back({object, score});
  }

  std::vector<const HiRouteObjectRecord*> debugCandidateObjects;
  debugCandidateObjects.reserve(lookup.localCandidateObjectIds.size());
  for (const auto& objectId : lookup.localCandidateObjectIds) {
    auto objectIt = m_objectsById.find(objectId);
    if (objectIt != m_objectsById.end()) {
      debugCandidateObjects.push_back(&objectIt->second);
    }
  }
  evaluation.candidateObjectCountPreFilter = debugCandidateObjects.size();
  evaluation.candidateObjectCountPostFilter = evaluation.ranked.size();
  if (evaluation.candidateObjectCountPostFilter != 0) {
    return evaluation;
  }

  if (!frontierHintCellId.empty() && evaluation.candidateObjectCountPreFilter == 0) {
    if (!lookup.exactCellExists && frontierHintCellId.find("-mc-") != std::string::npos) {
      evaluation.zeroReason = "cell_missing";
    }
    else if (!lookup.exactCellExists) {
      evaluation.zeroReason = "descendant_miss";
    }
  }
  if (!evaluation.zeroReason.empty() || debugCandidateObjects.empty()) {
    return evaluation;
  }

  std::vector<const HiRouteObjectRecord*> filtered = debugCandidateObjects;
  if (!request.predicate.zoneConstraint.empty()) {
    std::vector<const HiRouteObjectRecord*> zoneMatched;
    for (const auto* object : filtered) {
      if (MatchesZoneConstraint(object->zoneId, request.predicate.zoneConstraint)) {
        zoneMatched.push_back(object);
      }
    }
    if (zoneMatched.empty()) {
      evaluation.zeroReason = "zone_mismatch";
      return evaluation;
    }
    filtered = zoneMatched;
  }
  if (!request.predicate.zoneTypeConstraint.empty()) {
    std::vector<const HiRouteObjectRecord*> zoneTypeMatched;
    for (const auto* object : filtered) {
      if (object->zoneType == request.predicate.zoneTypeConstraint) {
        zoneTypeMatched.push_back(object);
      }
    }
    if (zoneTypeMatched.empty()) {
      evaluation.zeroReason = "zone_type_mismatch";
      return evaluation;
    }
    filtered = zoneTypeMatched;
  }
  if (!request.predicate.serviceConstraint.empty()) {
    std::vector<const HiRouteObjectRecord*> serviceMatched;
    for (const auto* object : filtered) {
      if (object->serviceClass == request.predicate.serviceConstraint) {
        serviceMatched.push_back(object);
      }
    }
    if (serviceMatched.empty()) {
      evaluation.zeroReason = "service_mismatch";
      return evaluation;
    }
    filtered = serviceMatched;
  }
  if (!request.predicate.freshnessConstraint.empty()) {
    std::vector<const HiRouteObjectRecord*> freshnessMatched;
    for (const auto* object : filtered) {
      if (object->freshnessClass == request.predicate.freshnessConstraint) {
        freshnessMatched.push_back(object);
      }
    }
    if (freshnessMatched.empty()) {
      evaluation.zeroReason = "freshness_mismatch";
    }
  }
  return evaluation;
}

void
HiRouteControllerApp::appendManifestDebugRow(const HiRouteDiscoveryRequest& request,
                                             const std::string& frontierHintCellId,
                                             const CandidateLookup& lookup,
                                             const CandidateEvaluation& evaluation) const
{
  if (m_manifestDebugCsvPath.empty()) {
    return;
  }

  AppendCsvRow(
    m_manifestDebugCsvPath,
    {"query_id", "frontier_hint_cell_id", "exact_cell_exists", "descendant_cell_count",
     "candidate_object_count_pre_filter", "candidate_object_count_post_filter", "zero_reason"},
    {request.queryId,
     frontierHintCellId,
     lookup.exactCellExists ? "1" : "0",
     std::to_string(lookup.descendantCellCount),
     std::to_string(evaluation.candidateObjectCountPreFilter),
     std::to_string(evaluation.candidateObjectCountPostFilter),
     evaluation.zeroReason});
}

std::vector<HiRouteManifestEntry>
HiRouteControllerApp::buildManifest(const HiRouteDiscoveryRequest& request) const
{
  if (m_oracleMode || m_prefix.find("/oracle/") != std::string::npos) {
    return buildOracleManifest(request);
  }

  const auto lookup = resolveCandidateLookup(request.frontierHintCellId);
  auto evaluation = evaluateCandidates(request, request.frontierHintCellId, lookup);
  auto ranked = evaluation.ranked;

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

  if (!m_manifestDebugCsvPath.empty()) {
    appendManifestDebugRow(request, request.frontierHintCellId, lookup, evaluation);
    const auto rootFrontierHint = DomainRootForCellId(request.frontierHintCellId);
    if (!rootFrontierHint.empty() && rootFrontierHint != request.frontierHintCellId) {
      const auto rootLookup = resolveCandidateLookup(rootFrontierHint);
      const auto rootEvaluation = evaluateCandidates(request, rootFrontierHint, rootLookup);
      appendManifestDebugRow(request, rootFrontierHint, rootLookup, rootEvaluation);
    }
  }

  if (m_staleAfter > Seconds(0) && Simulator::Now() >= m_staleAfter && !manifest.empty() &&
      m_rand->GetValue(0.0, 1.0) < m_staleDropProbability) {
    manifest.erase(manifest.begin());
  }
  return manifest;
}

std::vector<HiRouteManifestEntry>
HiRouteControllerApp::buildOracleManifest(const HiRouteDiscoveryRequest& request) const
{
  std::vector<HiRouteManifestEntry> manifest;
  auto rankedIt = m_oracleRankedQrels.find(request.queryId);
  if (rankedIt == m_oracleRankedQrels.end()) {
    return manifest;
  }

  const auto resultLimit = request.requestedManifestSize == 0 ?
    m_manifestSize :
    std::min<uint32_t>(m_manifestSize, request.requestedManifestSize);
  manifest.reserve(std::min<size_t>(rankedIt->second.size(), resultLimit));

  for (const auto& item : rankedIt->second) {
    auto objectIt = m_objectsById.find(item.first);
    if (objectIt == m_objectsById.end()) {
      continue;
    }

    HiRouteManifestEntry entry;
    entry.canonicalName = objectIt->second.canonicalName;
    entry.confidenceScore = static_cast<double>(item.second);
    entry.domainId = objectIt->second.domainId;
    entry.cellId = "global-oracle";
    entry.objectId = objectIt->second.objectId;
    manifest.push_back(entry);
    if (manifest.size() >= resultLimit) {
      break;
    }
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
