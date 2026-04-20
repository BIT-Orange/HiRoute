/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "hiroute-embedding-store.hpp"

#include "hiroute-dataset-reader.hpp"

#include <cmath>
#include <cstdlib>
#include <sstream>

namespace ns3 {
namespace ndn {
namespace hiroute {

void
HiRouteEmbeddingStore::LoadFromCsv(const std::string& path, const std::string& rowKey)
{
  m_vectorsByRow.clear();
  if (path.empty()) {
    return;
  }
  for (const auto& row : HiRouteDatasetReader::ReadCsvRows(path)) {
    const auto rowValue = GetFieldOrEmpty(row, rowKey);
    if (rowValue.empty()) {
      continue;
    }
    const auto encoded = GetFieldOrEmpty(row, "embedding_vector");
    if (encoded.empty()) {
      continue;
    }
    const auto index = static_cast<uint32_t>(std::strtoul(rowValue.c_str(), nullptr, 10));
    m_vectorsByRow[index] = ParseVector(encoded);
  }
}

const std::vector<double>*
HiRouteEmbeddingStore::Find(uint32_t row) const
{
  auto it = m_vectorsByRow.find(row);
  return it == m_vectorsByRow.end() ? nullptr : &it->second;
}

bool
HiRouteEmbeddingStore::Empty() const
{
  return m_vectorsByRow.empty();
}

std::vector<double>
HiRouteEmbeddingStore::ParseVector(const std::string& encoded)
{
  std::vector<double> values;
  std::stringstream parser(encoded);
  std::string token;
  while (std::getline(parser, token, '|')) {
    if (token.empty()) {
      continue;
    }
    values.push_back(std::strtod(token.c_str(), nullptr));
  }
  return values;
}

double
HiRouteEmbeddingStore::NormalizedCosine(const std::vector<double>& left,
                                        const std::vector<double>& right)
{
  if (left.empty() || right.empty() || left.size() != right.size()) {
    return 0.0;
  }

  double dot = 0.0;
  double leftNorm = 0.0;
  double rightNorm = 0.0;
  for (size_t index = 0; index < left.size(); ++index) {
    dot += left[index] * right[index];
    leftNorm += left[index] * left[index];
    rightNorm += right[index] * right[index];
  }
  if (leftNorm <= 0.0 || rightNorm <= 0.0) {
    return 0.0;
  }
  return dot / std::sqrt(leftNorm * rightNorm);
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
