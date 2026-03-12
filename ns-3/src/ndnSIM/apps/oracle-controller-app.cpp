/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "oracle-controller-app.hpp"

#include "ns3/log.h"

NS_LOG_COMPONENT_DEFINE("ndn.OracleControllerApp");

namespace ns3 {
namespace ndn {
namespace hiroute {

NS_OBJECT_ENSURE_REGISTERED(OracleControllerApp);

TypeId
OracleControllerApp::GetTypeId()
{
  static TypeId tid =
    TypeId("ns3::ndn::OracleControllerApp").SetGroupName("Ndn").SetParent<HiRouteControllerApp>().AddConstructor<OracleControllerApp>();
  return tid;
}

OracleControllerApp::OracleControllerApp()
{
  SetOracleMode(true);
  SetPrefix("/hiroute/oracle/controller");
}

} // namespace hiroute
} // namespace ndn
} // namespace ns3
