/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */

#include "ns3/core-module.h"
#include "ns3/constant-position-mobility-model.h"
#include "ns3/ndnSIM-module.h"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>

namespace {

std::string
normalizeWeightsFile(const std::string& weightsFile, const std::string& outputFile, double weightScale)
{
  std::ifstream input(weightsFile.c_str());
  if (!input.is_open()) {
    throw std::runtime_error("cannot open weights file: " + weightsFile);
  }

  std::string normalizedFile = outputFile + ".weights.normalized";
  std::ofstream output(normalizedFile.c_str());
  if (!output.is_open()) {
    throw std::runtime_error("cannot write normalized weights file: " + normalizedFile);
  }

  std::string line;
  while (std::getline(input, line)) {
    if (line.empty() || line[0] == '#') {
      output << line << std::endl;
      continue;
    }

    std::istringstream parser(line);
    std::string from;
    std::string to;
    std::string attribute;
    parser >> from >> to >> attribute;

    if (from.empty() || to.empty() || attribute.empty()) {
      output << line << std::endl;
      continue;
    }

    double rawWeight = std::stod(attribute);
    long long normalizedWeight = std::llround(rawWeight * weightScale);
    if (normalizedWeight <= 0) {
      normalizedWeight = 1;
    }

    output << from << ' ' << to << ' ' << normalizedWeight << std::endl;
  }

  return normalizedFile;
}

void
ensureNodePositions(const ns3::NodeContainer& nodes, double scale)
{
  const uint32_t total = nodes.GetN();
  const double radius = std::max(50.0, 10.0 * std::sqrt(static_cast<double>(std::max(1u, total)))) * scale;

  for (uint32_t index = 0; index < total; ++index) {
    ns3::Ptr<ns3::Node> node = nodes.Get(index);
    ns3::Ptr<ns3::MobilityModel> mobility = node->GetObject<ns3::MobilityModel>();
    if (mobility != 0) {
      continue;
    }

    double angle = (2.0 * M_PI * static_cast<double>(index)) / static_cast<double>(std::max(1u, total));
    ns3::Ptr<ns3::ConstantPositionMobilityModel> position =
      ns3::CreateObject<ns3::ConstantPositionMobilityModel>();
    position->SetPosition(ns3::Vector(radius * std::cos(angle), radius * std::sin(angle), 0.0));
    node->AggregateObject(position);
  }
}

} // namespace

int
main(int argc, char* argv[])
{
  std::string latencyFile;
  std::string weightsFile;
  std::string outputFile;
  std::string graphvizFile;
  std::string bandwidth = "10Mbps";
  std::string queue = "100";
  double scale = 1.0;
  double weightScale = 10.0;

  ns3::CommandLine cmd;
  cmd.AddValue("latency", "Path to Rocketfuel *.latencies.intra file", latencyFile);
  cmd.AddValue("weights", "Path to Rocketfuel *.weights.intra file", weightsFile);
  cmd.AddValue("output", "Path to generated ndnSIM annotated topology", outputFile);
  cmd.AddValue("graphviz", "Optional DOT output path", graphvizFile);
  cmd.AddValue("bandwidth", "Default link bandwidth assigned during conversion", bandwidth);
  cmd.AddValue("queue", "Default queue size assigned during conversion", queue);
  cmd.AddValue("scale", "Coordinate scale for generated topology", scale);
  cmd.AddValue("weightScale", "Multiplier applied before rounding Rocketfuel decimal weights", weightScale);
  cmd.Parse(argc, argv);

  if (latencyFile.empty() || weightsFile.empty() || outputFile.empty()) {
    std::cerr << "latency, weights, and output arguments are required" << std::endl;
    return 1;
  }

  std::string normalizedWeightsFile;
  try {
    normalizedWeightsFile = normalizeWeightsFile(weightsFile, outputFile, weightScale);

    ns3::RocketfuelWeightsReader reader("", scale);
    reader.SetDefaultBandwidth(bandwidth);
    reader.SetDefaultQueue(queue);

    reader.SetFileName(latencyFile);
    reader.SetFileType(ns3::RocketfuelWeightsReader::LATENCIES);
    reader.Read();

    reader.SetFileName(normalizedWeightsFile);
    reader.SetFileType(ns3::RocketfuelWeightsReader::WEIGHTS);
    reader.Read();

    reader.Commit();
    ensureNodePositions(reader.GetNodes(), std::max(1.0, scale));
    reader.SaveTopology(outputFile);
    if (!graphvizFile.empty()) {
      reader.SaveGraphviz(graphvizFile);
    }
  }
  catch (const std::exception& error) {
    std::cerr << error.what() << std::endl;
    if (!normalizedWeightsFile.empty()) {
      std::remove(normalizedWeightsFile.c_str());
    }
    return 1;
  }

  std::remove(normalizedWeightsFile.c_str());
  std::cout << outputFile << std::endl;
  return 0;
}
