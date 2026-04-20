/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "hiroute-tlv.hpp"

#include <ndn-cxx/encoding/block-helpers.hpp>

#include <cstring>
#include <stdexcept>

namespace ns3 {
namespace ndn {
namespace hiroute {

namespace {

uint32_t
encodeDiscoveryStatus(HiRouteDiscoveryStatus status)
{
  return static_cast<uint32_t>(status);
}

HiRouteDiscoveryStatus
decodeDiscoveryStatus(uint64_t raw)
{
  switch (raw) {
    case 0:
      return HiRouteDiscoveryStatus::Ok;
    case 1:
      return HiRouteDiscoveryStatus::EmptyManifest;
    case 2:
      return HiRouteDiscoveryStatus::PredicateMismatch;
    case 3:
      return HiRouteDiscoveryStatus::CellMissing;
    case 4:
      return HiRouteDiscoveryStatus::InternalError;
    default:
      return HiRouteDiscoveryStatus::InternalError;
  }
}

std::string
defaultReasonCodeForStatus(HiRouteDiscoveryStatus status)
{
  switch (status) {
    case HiRouteDiscoveryStatus::Ok:
      return "ok";
    case HiRouteDiscoveryStatus::EmptyManifest:
      return "empty_manifest";
    case HiRouteDiscoveryStatus::PredicateMismatch:
      return "predicate_mismatch";
    case HiRouteDiscoveryStatus::CellMissing:
      return "cell_missing";
    case HiRouteDiscoveryStatus::InternalError:
      return "internal_error";
    default:
      return "internal_error";
  }
}

Block
encodePredicate(const HiRoutePredicateHeader& predicate)
{
  auto block = ::ndn::makeEmptyBlock(tlv::PredicateHeader);
  if (!predicate.zoneConstraint.empty()) {
    block.push_back(::ndn::makeStringBlock(tlv::ZoneConstraint, predicate.zoneConstraint));
  }
  if (!predicate.zoneTypeConstraint.empty()) {
    block.push_back(::ndn::makeStringBlock(tlv::ZoneTypeConstraint, predicate.zoneTypeConstraint));
  }
  if (!predicate.serviceConstraint.empty()) {
    block.push_back(::ndn::makeStringBlock(tlv::ServiceConstraint, predicate.serviceConstraint));
  }
  if (!predicate.freshnessConstraint.empty()) {
    block.push_back(::ndn::makeStringBlock(tlv::FreshnessConstraint, predicate.freshnessConstraint));
  }
  block.encode();
  return block;
}

HiRoutePredicateHeader
decodePredicate(const Block& block)
{
  if (block.type() != tlv::PredicateHeader) {
    throw std::runtime_error("unexpected predicate block type");
  }

  HiRoutePredicateHeader predicate;
  auto parsed = block;
  parsed.parse();
  for (const auto& element : parsed.elements()) {
    switch (element.type()) {
      case tlv::ZoneConstraint:
        predicate.zoneConstraint = ::ndn::readString(element);
        break;
      case tlv::ZoneTypeConstraint:
        predicate.zoneTypeConstraint = ::ndn::readString(element);
        break;
      case tlv::ServiceConstraint:
        predicate.serviceConstraint = ::ndn::readString(element);
        break;
      case tlv::FreshnessConstraint:
        predicate.freshnessConstraint = ::ndn::readString(element);
        break;
      default:
        break;
    }
  }
  return predicate;
}

Block
encodeResidualVector(const std::vector<float>& vector)
{
  if (vector.empty()) {
    return ::ndn::makeEmptyBlock(tlv::ResidualVector);
  }

  auto bytes = ::ndn::make_span(reinterpret_cast<const uint8_t*>(vector.data()),
                                vector.size() * sizeof(float));
  return ::ndn::makeBinaryBlock(tlv::ResidualVector, bytes);
}

std::vector<float>
decodeResidualVector(const Block& block)
{
  if (block.value_size() == 0) {
    return {};
  }
  if (block.value_size() % sizeof(float) != 0) {
    throw std::runtime_error("residual vector block is not float-aligned");
  }

  std::vector<float> vector(block.value_size() / sizeof(float));
  std::memcpy(vector.data(), block.value(), block.value_size());
  return vector;
}

Block
encodeManifestEntry(const HiRouteManifestEntry& entry)
{
  auto block = ::ndn::makeEmptyBlock(tlv::ManifestEntry);
  block.push_back(::ndn::makeStringBlock(tlv::CanonicalName, entry.canonicalName));
  block.push_back(::ndn::encoding::makeDoubleBlock(tlv::ConfidenceScore, entry.confidenceScore));
  block.push_back(::ndn::makeStringBlock(tlv::DomainId, entry.domainId));
  block.push_back(::ndn::makeStringBlock(tlv::CellId, entry.cellId));
  block.push_back(::ndn::makeStringBlock(tlv::ObjectId, entry.objectId));
  block.encode();
  return block;
}

HiRouteManifestEntry
decodeManifestEntry(const Block& block)
{
  if (block.type() != tlv::ManifestEntry) {
    throw std::runtime_error("unexpected manifest block type");
  }

  HiRouteManifestEntry entry;
  auto parsed = block;
  parsed.parse();
  for (const auto& element : parsed.elements()) {
    switch (element.type()) {
      case tlv::CanonicalName:
        entry.canonicalName = ::ndn::readString(element);
        break;
      case tlv::ConfidenceScore:
        entry.confidenceScore = ::ndn::encoding::readDouble(element);
        break;
      case tlv::DomainId:
        entry.domainId = ::ndn::readString(element);
        break;
      case tlv::CellId:
        entry.cellId = ::ndn::readString(element);
        break;
      case tlv::ObjectId:
        entry.objectId = ::ndn::readString(element);
        break;
      default:
        break;
    }
  }
  return entry;
}

} // namespace

Block
HiRouteTlv::EncodeDiscoveryRequest(const HiRouteDiscoveryRequest& request)
{
  auto block = ::ndn::makeEmptyBlock(tlv::HiRouteDiscoveryRequest);
  block.push_back(::ndn::makeStringBlock(tlv::QueryId, request.queryId));
  block.push_back(::ndn::makeNonNegativeIntegerBlock(tlv::QueryEmbeddingRow, request.queryEmbeddingRow));
  block.push_back(encodePredicate(request.predicate));
  block.push_back(::ndn::makeNonNegativeIntegerBlock(tlv::RefinementBudget, request.refinementBudget));
  block.push_back(::ndn::makeNonNegativeIntegerBlock(tlv::RequestedManifestSize,
                                                     request.requestedManifestSize));
  if (!request.frontierHintCellId.empty()) {
    block.push_back(::ndn::makeStringBlock(tlv::FrontierHintCellId, request.frontierHintCellId));
  }
  if (!request.intentFacet.empty()) {
    block.push_back(::ndn::makeStringBlock(tlv::IntentFacet, request.intentFacet));
  }
  if (!request.residualVector.empty()) {
    block.push_back(encodeResidualVector(request.residualVector));
  }
  block.encode();
  return block;
}

HiRouteDiscoveryRequest
HiRouteTlv::DecodeDiscoveryRequest(const Block& block)
{
  if (block.type() != tlv::HiRouteDiscoveryRequest) {
    throw std::runtime_error("unexpected discovery request block type");
  }

  HiRouteDiscoveryRequest request;
  auto parsed = block;
  parsed.parse();
  for (const auto& element : parsed.elements()) {
    switch (element.type()) {
      case tlv::QueryId:
        request.queryId = ::ndn::readString(element);
        break;
      case tlv::QueryEmbeddingRow:
        request.queryEmbeddingRow =
          static_cast<uint32_t>(::ndn::readNonNegativeInteger(element));
        break;
      case tlv::PredicateHeader:
        request.predicate = decodePredicate(element);
        break;
      case tlv::RefinementBudget:
        request.refinementBudget =
          static_cast<uint32_t>(::ndn::readNonNegativeInteger(element));
        break;
      case tlv::RequestedManifestSize:
        request.requestedManifestSize =
          static_cast<uint32_t>(::ndn::readNonNegativeInteger(element));
        break;
      case tlv::FrontierHintCellId:
        request.frontierHintCellId = ::ndn::readString(element);
        break;
      case tlv::IntentFacet:
        request.intentFacet = ::ndn::readString(element);
        request.predicate.intentFacet = request.intentFacet;
        break;
      case tlv::ResidualVector:
        request.residualVector = decodeResidualVector(element);
        break;
      default:
        break;
    }
  }
  return request;
}

Block
HiRouteTlv::EncodeDiscoveryReply(const HiRouteDiscoveryReply& reply)
{
  auto block = ::ndn::makeEmptyBlock(tlv::HiRouteDiscoveryReply);
  block.push_back(::ndn::makeNonNegativeIntegerBlock(tlv::ReplyStatus,
                                                     encodeDiscoveryStatus(reply.status)));
  if (!reply.selectedCellId.empty()) {
    block.push_back(::ndn::makeStringBlock(tlv::ReplySelectedCellId, reply.selectedCellId));
  }
  if (!reply.reasonCode.empty()) {
    block.push_back(::ndn::makeStringBlock(tlv::ReplyReasonCode, reply.reasonCode));
  }
  if (reply.localConfidence != 0.0) {
    block.push_back(::ndn::encoding::makeDoubleBlock(tlv::ReplyLocalConfidence,
                                                     reply.localConfidence));
  }
  for (const auto& entry : reply.manifest) {
    block.push_back(encodeManifestEntry(entry));
  }
  block.encode();
  return block;
}

HiRouteDiscoveryReply
HiRouteTlv::DecodeDiscoveryReply(const Block& block)
{
  if (block.type() != tlv::HiRouteDiscoveryReply) {
    throw std::runtime_error("unexpected discovery reply block type");
  }

  HiRouteDiscoveryReply reply;
  bool hasStatus = false;
  auto parsed = block;
  parsed.parse();
  for (const auto& element : parsed.elements()) {
    switch (element.type()) {
      case tlv::ReplyStatus:
        reply.status = decodeDiscoveryStatus(::ndn::readNonNegativeInteger(element));
        hasStatus = true;
        break;
      case tlv::ReplySelectedCellId:
        reply.selectedCellId = ::ndn::readString(element);
        break;
      case tlv::ReplyReasonCode:
        reply.reasonCode = ::ndn::readString(element);
        break;
      case tlv::ReplyLocalConfidence:
        reply.localConfidence = ::ndn::encoding::readDouble(element);
        break;
      case tlv::ManifestEntry:
        reply.manifest.push_back(decodeManifestEntry(element));
        break;
      default:
        break;
    }
  }

  // Backward compatibility for older replies that carried only manifest entries.
  if (!hasStatus) {
    reply.status = reply.manifest.empty() ? HiRouteDiscoveryStatus::EmptyManifest
                                          : HiRouteDiscoveryStatus::Ok;
  }
  if (reply.selectedCellId.empty() && !reply.manifest.empty()) {
    reply.selectedCellId = reply.manifest.front().cellId;
  }
  if (reply.localConfidence == 0.0 && !reply.manifest.empty()) {
    reply.localConfidence = reply.manifest.front().confidenceScore;
  }
  if (reply.reasonCode.empty()) {
    reply.reasonCode = defaultReasonCodeForStatus(reply.status);
  }

  return reply;
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
