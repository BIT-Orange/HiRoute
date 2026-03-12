/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_FLOOD_DISCOVERY_APP_HPP
#define NDNSIM_FLOOD_DISCOVERY_APP_HPP

#include "hiroute-ingress-app.hpp"

namespace ns3 {
namespace ndn {
namespace hiroute {

class FloodDiscoveryApp : public HiRouteIngressApp {
public:
  static TypeId
  GetTypeId();

  FloodDiscoveryApp();
  ~FloodDiscoveryApp() override = default;
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_FLOOD_DISCOVERY_APP_HPP
