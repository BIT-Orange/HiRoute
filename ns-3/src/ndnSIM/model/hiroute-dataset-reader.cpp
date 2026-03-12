/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "hiroute-dataset-reader.hpp"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <stdexcept>

namespace ns3 {
namespace ndn {
namespace hiroute {

namespace {

std::string
trim(const std::string& value)
{
  auto begin = value.begin();
  while (begin != value.end() &&
         std::isspace(static_cast<unsigned char>(*begin)) != 0) {
    ++begin;
  }

  auto end = value.end();
  while (end != begin &&
         std::isspace(static_cast<unsigned char>(*(end - 1))) != 0) {
    --end;
  }

  return std::string(begin, end);
}

std::vector<std::string>
splitCsvLine(const std::string& line)
{
  std::vector<std::string> values;
  std::string current;
  bool inQuotes = false;

  for (size_t index = 0; index < line.size(); ++index) {
    const char ch = line[index];
    if (ch == '"') {
      if (inQuotes && index + 1 < line.size() && line[index + 1] == '"') {
        current.push_back('"');
        ++index;
        continue;
      }
      inQuotes = !inQuotes;
      continue;
    }
    if (ch == ',' && !inQuotes) {
      values.push_back(trim(current));
      current.clear();
      continue;
    }
    current.push_back(ch);
  }
  values.push_back(trim(current));
  return values;
}

} // namespace

std::vector<HiRouteCsvRow>
HiRouteDatasetReader::ReadCsvRows(const std::string& path)
{
  std::ifstream input(path.c_str());
  if (!input.good()) {
    throw std::runtime_error("failed to open csv: " + path);
  }

  std::string line;
  if (!std::getline(input, line)) {
    return {};
  }

  const auto header = splitCsvLine(line);
  std::vector<HiRouteCsvRow> rows;
  while (std::getline(input, line)) {
    if (line.empty()) {
      continue;
    }
    const auto values = splitCsvLine(line);
    HiRouteCsvRow row;
    for (size_t index = 0; index < header.size(); ++index) {
      row[header[index]] = index < values.size() ? values[index] : std::string();
    }
    rows.push_back(std::move(row));
  }
  return rows;
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
