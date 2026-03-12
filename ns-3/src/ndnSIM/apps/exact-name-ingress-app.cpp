/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "exact-name-ingress-app.hpp"

namespace ns3 {
namespace ndn {
namespace hiroute {

NS_OBJECT_ENSURE_REGISTERED(ExactNameIngressApp);

TypeId
ExactNameIngressApp::GetTypeId()
{
  static TypeId tid =
    TypeId("ns3::ndn::ExactNameIngressApp").SetGroupName("Ndn").SetParent<HiRouteIngressApp>().AddConstructor<ExactNameIngressApp>();
  return tid;
}

ExactNameIngressApp::ExactNameIngressApp()
{
  SetStrategyMode("exact");
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
