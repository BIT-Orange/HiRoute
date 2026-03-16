/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_INF_TAG_FORWARDING_APP_HPP
#define NDNSIM_INF_TAG_FORWARDING_APP_HPP

#include "hiroute-ingress-app.hpp"

namespace ns3 {
namespace ndn {
namespace hiroute {

class InfTagForwardingApp : public HiRouteIngressApp {
public:
  static TypeId
  GetTypeId();

  InfTagForwardingApp();
  ~InfTagForwardingApp() override = default;
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_INF_TAG_FORWARDING_APP_HPP
