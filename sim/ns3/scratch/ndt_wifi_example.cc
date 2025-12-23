#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/applications-module.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("NdtWifiExample");

int main(int argc, char* argv[])
{
  uint32_t nSta = 2;
  double simTime = 5.0;
  uint32_t payloadSize = 1472;
  uint32_t seed = 42;

  CommandLine cmd;
  cmd.AddValue("nSta", "Number of stations", nSta);
  cmd.AddValue("simTime", "Simulation time (s)", simTime);
  cmd.AddValue("seed", "RNG seed", seed);
  cmd.Parse(argc, argv);

  RngSeedManager::SetSeed(seed);
  RngSeedManager::SetRun(1);

  NodeContainer apNode;
  apNode.Create(1);

  NodeContainer staNodes;
  staNodes.Create(nSta);

  YansWifiChannelHelper channel = YansWifiChannelHelper::Default();

  // ns-3.46+: don't use YansWifiPhyHelper::Default()
  YansWifiPhyHelper phy;
  phy.SetChannel(channel.Create());

  WifiHelper wifi;
  wifi.SetStandard(WIFI_STANDARD_80211ax); // baseline (upgrade later to EHT/MLO)
  wifi.SetRemoteStationManager("ns3::MinstrelHtWifiManager");

  WifiMacHelper mac;
  Ssid ssid = Ssid("ndt-wifi");

  // STA MAC
  mac.SetType("ns3::StaWifiMac",
              "Ssid", SsidValue(ssid),
              "ActiveProbing", BooleanValue(false));
  NetDeviceContainer staDevs = wifi.Install(phy, mac, staNodes);

  // AP MAC
  mac.SetType("ns3::ApWifiMac",
              "Ssid", SsidValue(ssid));
  NetDeviceContainer apDev = wifi.Install(phy, mac, apNode);

  MobilityHelper mobility;
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  mobility.Install(apNode);
  mobility.Install(staNodes);

  apNode.Get(0)->GetObject<MobilityModel>()->SetPosition(Vector(0.0, 0.0, 0.0));
  for (uint32_t i = 0; i < nSta; i++)
  {
    staNodes.Get(i)->GetObject<MobilityModel>()->SetPosition(Vector(2.0 + i, 0.0, 0.0));
  }

  InternetStackHelper stack;
  stack.Install(apNode);
  stack.Install(staNodes);

  Ipv4AddressHelper address;
  address.SetBase("10.1.1.0", "255.255.255.0");
  Ipv4InterfaceContainer staIf = address.Assign(staDevs);
  Ipv4InterfaceContainer apIf = address.Assign(apDev);

  // UDP server on STA-1
  uint16_t port = 9000;
  UdpServerHelper server(port);
  ApplicationContainer serverApp = server.Install(staNodes.Get(0));
  serverApp.Start(Seconds(1.0));
  serverApp.Stop(Seconds(simTime));

  // UDP client on AP -> STA-1
  UdpClientHelper client(staIf.GetAddress(0), port);
  client.SetAttribute("MaxPackets", UintegerValue(0)); // unlimited
  client.SetAttribute("Interval", TimeValue(MicroSeconds(100))); // 10k pps
  client.SetAttribute("PacketSize", UintegerValue(payloadSize));

  ApplicationContainer clientApp = client.Install(apNode.Get(0));
  clientApp.Start(Seconds(1.1));
  clientApp.Stop(Seconds(simTime));

  Simulator::Stop(Seconds(simTime));
  Simulator::Run();

  // Throughput from received packets
  Ptr<UdpServer> udpServer = DynamicCast<UdpServer>(serverApp.Get(0));
  uint64_t rxPackets = udpServer->GetReceived();
  uint64_t rxBytes = rxPackets * payloadSize;

  double duration = simTime - 1.1;
  if (duration <= 0.0) duration = 1.0;

  double mbps = (rxBytes * 8.0) / (duration * 1e6);
  std::cout << "Throughput: " << mbps << " Mbps" << std::endl;

  Simulator::Destroy();
  return 0;
}
