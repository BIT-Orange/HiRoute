/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "flat-semantic-ingress-app.hpp"

namespace ns3 {
namespace ndn {
namespace hiroute {

NS_OBJECT_ENSURE_REGISTERED(FlatSemanticIngressApp);

TypeId
FlatSemanticIngressApp::GetTypeId()
{
  static TypeId tid =
    TypeId("ns3::ndn::FlatSemanticIngressApp").SetGroupName("Ndn").SetParent<HiRouteIngressApp>().AddConstructor<FlatSemanticIngressApp>();
  return tid;
}

FlatSemanticIngressApp::FlatSemanticIngressApp()
{
  SetStrategyMode("flat");
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
