/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "hiroute-summary-store.hpp"

#include <fstream>
#include <sstream>
#include <stdexcept>

namespace ns3 {
namespace ndn {
namespace hiroute {

namespace {

std::vector<std::string>
splitCsvLine(const std::string& line)
{
  std::vector<std::string> values;
  std::string current;
  bool inQuotes = false;

  for (char ch : line) {
    if (ch == '"') {
      inQuotes = !inQuotes;
      continue;
    }
    if (ch == ',' && !inQuotes) {
      values.push_back(current);
      current.clear();
      continue;
    }
    current.push_back(ch);
  }
  values.push_back(current);
  return values;
}

std::map<std::string, std::string>
makeRow(const std::vector<std::string>& header, const std::vector<std::string>& values)
{
  std::map<std::string, std::string> row;
  for (size_t index = 0; index < header.size(); ++index) {
    row[header[index]] = index < values.size() ? values[index] : std::string();
  }
  return row;
}

} // namespace

void
HiRouteSummaryStore::LoadFromCsv(const std::string& path)
{
  std::ifstream input(path.c_str());
  if (!input.good()) {
    throw std::runtime_error("failed to open summary csv: " + path);
  }

  std::string line;
  if (!std::getline(input, line)) {
    throw std::runtime_error("summary csv is empty: " + path);
  }
  const auto header = splitCsvLine(line);

  m_entries.clear();
  while (std::getline(input, line)) {
    if (line.empty()) {
      continue;
    }
    m_entries.push_back(HiRouteSummaryEntry::FromCsvRow(makeRow(header, splitCsvLine(line))));
  }
  rebuildIndexes();
}

const HiRouteSummaryEntry*
HiRouteSummaryStore::Find(const std::string& cellId) const
{
  auto it = m_cellIndex.find(cellId);
  return it == m_cellIndex.end() ? nullptr : &m_entries[it->second];
}

std::vector<const HiRouteSummaryEntry*>
HiRouteSummaryStore::GetChildren(const std::string& parentId) const
{
  std::vector<const HiRouteSummaryEntry*> children;
  auto it = m_children.find(parentId);
  if (it == m_children.end()) {
    return children;
  }

  children.reserve(it->second.size());
  for (size_t index : it->second) {
    children.push_back(&m_entries[index]);
  }
  return children;
}

std::vector<const HiRouteSummaryEntry*>
HiRouteSummaryStore::GetEntriesAtLevel(uint32_t level) const
{
  std::vector<const HiRouteSummaryEntry*> entries;
  for (const auto& entry : m_entries) {
    if (entry.level == level) {
      entries.push_back(&entry);
    }
  }
  return entries;
}

std::vector<const HiRouteSummaryEntry*>
HiRouteSummaryStore::FilterByPredicate(const std::string& zoneConstraint,
                                       const std::string& zoneTypeConstraint,
                                       const std::string& serviceConstraint,
                                       const std::string& freshnessConstraint) const
{
  std::vector<const HiRouteSummaryEntry*> admissible;
  admissible.reserve(m_entries.size());
  for (const auto& entry : m_entries) {
    if (entry.MatchesPredicate(zoneConstraint, zoneTypeConstraint, serviceConstraint,
                               freshnessConstraint)) {
      admissible.push_back(&entry);
    }
  }
  return admissible;
}

const std::vector<HiRouteSummaryEntry>&
HiRouteSummaryStore::GetEntries() const
{
  return m_entries;
}

void
HiRouteSummaryStore::rebuildIndexes()
{
  m_cellIndex.clear();
  m_children.clear();
  for (size_t index = 0; index < m_entries.size(); ++index) {
    const auto& entry = m_entries[index];
    m_cellIndex[entry.cellId] = index;
    if (!entry.parentId.empty()) {
      m_children[entry.parentId].push_back(index);
    }
  }
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
