/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_HIROUTE_DATASET_READER_HPP
#define NDNSIM_HIROUTE_DATASET_READER_HPP

#include "ns3/ndnSIM/model/ndn-common.hpp"

#include <map>
#include <string>
#include <vector>

namespace ns3 {
namespace ndn {
namespace hiroute {

using HiRouteCsvRow = std::map<std::string, std::string>;

class HiRouteDatasetReader {
public:
  static std::vector<HiRouteCsvRow>
  ReadCsvRows(const std::string& path);
};

inline std::string
GetFieldOrEmpty(const HiRouteCsvRow& row, const std::string& key)
{
  auto it = row.find(key);
  return it == row.end() ? std::string() : it->second;
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_HIROUTE_DATASET_READER_HPP
