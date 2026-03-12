/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_ORACLE_CONTROLLER_APP_HPP
#define NDNSIM_ORACLE_CONTROLLER_APP_HPP

#include "hiroute-controller-app.hpp"

namespace ns3 {
namespace ndn {
namespace hiroute {

class OracleControllerApp : public HiRouteControllerApp {
public:
  static TypeId
  GetTypeId();

  OracleControllerApp();
  ~OracleControllerApp() override = default;
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_ORACLE_CONTROLLER_APP_HPP
