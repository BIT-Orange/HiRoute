/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_HIROUTE_EMBEDDING_STORE_HPP
#define NDNSIM_HIROUTE_EMBEDDING_STORE_HPP

#include "ns3/ndnSIM/model/ndn-common.hpp"

#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace ns3 {
namespace ndn {
namespace hiroute {

class HiRouteEmbeddingStore {
public:
  void
  LoadFromCsv(const std::string& path, const std::string& rowKey = "embedding_row");

  const std::vector<double>*
  Find(uint32_t row) const;

  bool
  Empty() const;

  static std::vector<double>
  ParseVector(const std::string& encoded);

  static double
  NormalizedCosine(const std::vector<double>& left, const std::vector<double>& right);

private:
  std::map<uint32_t, std::vector<double>> m_vectorsByRow;
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_EMBEDDING_STORE_HPP
