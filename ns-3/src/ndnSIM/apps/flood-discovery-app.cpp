/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "flood-discovery-app.hpp"

namespace ns3 {
namespace ndn {
namespace hiroute {

NS_OBJECT_ENSURE_REGISTERED(FloodDiscoveryApp);

TypeId
FloodDiscoveryApp::GetTypeId()
{
  static TypeId tid =
    TypeId("ns3::ndn::FloodDiscoveryApp").SetGroupName("Ndn").SetParent<HiRouteIngressApp>().AddConstructor<FloodDiscoveryApp>();
  return tid;
}

FloodDiscoveryApp::FloodDiscoveryApp()
{
  SetStrategyMode("flood");
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
