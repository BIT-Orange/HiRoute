/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_FLAT_SEMANTIC_INGRESS_APP_HPP
#define NDNSIM_FLAT_SEMANTIC_INGRESS_APP_HPP

#include "hiroute-ingress-app.hpp"

namespace ns3 {
namespace ndn {
namespace hiroute {

class FlatSemanticIngressApp : public HiRouteIngressApp {
public:
  static TypeId
  GetTypeId();

  FlatSemanticIngressApp();
  ~FlatSemanticIngressApp() override = default;
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_FLAT_SEMANTIC_INGRESS_APP_HPP
