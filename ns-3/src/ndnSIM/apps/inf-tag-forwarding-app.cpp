/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "inf-tag-forwarding-app.hpp"

namespace ns3 {
namespace ndn {
namespace hiroute {

NS_OBJECT_ENSURE_REGISTERED(InfTagForwardingApp);

TypeId
InfTagForwardingApp::GetTypeId()
{
  static TypeId tid =
    TypeId("ns3::ndn::InfTagForwardingApp")
      .SetGroupName("Ndn")
      .SetParent<HiRouteIngressApp>()
      .AddConstructor<InfTagForwardingApp>();
  return tid;
}

InfTagForwardingApp::InfTagForwardingApp()
{
  SetStrategyMode("inf_tag_forwarding");
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
