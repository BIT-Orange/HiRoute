/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "hiroute-scenario-common.hpp"

int
main(int argc, char* argv[])
{
  return ns3::ndn::hiroute::RunHiRouteScenario(
    argc, argv, ns3::ndn::hiroute::HiRouteScenarioMode::StateScaling);
}
