/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef NDNSIM_EXACT_NAME_INGRESS_APP_HPP
#define NDNSIM_EXACT_NAME_INGRESS_APP_HPP

#include "hiroute-ingress-app.hpp"

namespace ns3 {
namespace ndn {
namespace hiroute {

class ExactNameIngressApp : public HiRouteIngressApp {
public:
  static TypeId
  GetTypeId();

  ExactNameIngressApp();
  ~ExactNameIngressApp() override = default;
};

} // namespace hiroute
} // namespace ndn
} // namespace ns3

#endif // NDNSIM_EXACT_NAME_INGRESS_APP_HPP
