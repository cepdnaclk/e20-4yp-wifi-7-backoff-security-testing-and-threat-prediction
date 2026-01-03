// #include <fstream>
// #include <map>
// #include <string>
// #include <vector>
// #include <regex>

// #include "ns3/core-module.h"
// #include "ns3/network-module.h"
// #include "ns3/wifi-module.h"
// #include "ns3/spectrum-wifi-helper.h"
// #include "ns3/multi-model-spectrum-channel.h"
// #include "ns3/mobility-module.h"
// #include "ns3/internet-module.h"
// #include "ns3/applications-module.h"
// #include "ns3/netanim-module.h"
// #include "ns3/flow-monitor-module.h" 

// using namespace ns3;

// NS_LOG_COMPONENT_DEFINE("Wifi7MloAttack");

// static const double WINDOW = 0.1; 
// static uint32_t g_window = 0;

// /* ===================== DATA STRUCTURES ===================== */
// struct LinkStats {
//     uint64_t tx = 0, rx = 0, ack = 0, macDrop = 0, phyDrop = 0, retrans = 0;
//     double phyIdle = 0, phyTx = 0, phyRx = 0;
//     uint64_t backoffSum = 0, backoffCnt = 0;
// };

// struct NodeStats {
//     std::map<uint8_t, LinkStats> link; 
// };

// // Helper to extract Node ID from context string "/NodeList/5/DeviceList/..."
// uint32_t GetNodeIdFromContext(std::string context) {
//     size_t start = context.find("/NodeList/");
//     if (start == std::string::npos) return 0;
//     start += 10; // Length of "/NodeList/"
//     size_t end = context.find("/", start);
//     if (end == std::string::npos) return 0;
//     try {
//         return std::stoi(context.substr(start, end - start));
//     } catch (...) {
//         return 0;
//     }
// }

// struct Tracer {
//     std::ofstream* out;
//     bool* first;
//     double bias;
    
//     // Map: NodeID -> Stats
//     std::map<uint32_t, NodeStats> stats;
//     std::map<uint64_t, uint32_t> txCount;
    
//     // History for FlowMonitor (Windowing)
//     std::map<FlowId, uint64_t> prevRxBytes;
//     std::map<FlowId, uint64_t> prevRxPackets;
//     std::map<FlowId, uint64_t> prevTxPackets;
//     std::map<FlowId, double> prevDelaySum;
//     std::map<FlowId, double> prevJitterSum;
    
//     FlowMonitorHelper* flowHelper = nullptr;
//     Ptr<FlowMonitor> monitor = nullptr;

//     // --- UPDATED CALLBACKS WITH CONTEXT ---

//     void OnTxMpdu(std::string context, Ptr<const WifiMpdu> mpdu) {
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         txCount[mpdu->GetPacket()->GetUid()]++;
//         stats[nodeId].link[0].tx++;
//     }

//     void OnRxMpdu(std::string context, Ptr<const WifiMpdu> mpdu) {
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         stats[nodeId].link[0].rx++;
//     }

//     void OnAcked(std::string context, Ptr<const WifiMpdu> mpdu) {
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         uint64_t uid = mpdu->GetPacket()->GetUid();
//         stats[nodeId].link[0].ack++;
//         if (txCount[uid] > 1) stats[nodeId].link[0].retrans += txCount[uid] - 1;
//     }

//     void OnDropped(std::string context, Ptr<const WifiMpdu> mpdu, WifiMacDropReason reason) { 
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         stats[nodeId].link[0].macDrop++; 
//     }

//     void OnPhyDropped(std::string context, Ptr<const Packet> packet, WifiPhyRxfailureReason reason) {
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         stats[nodeId].link[0].phyDrop++;
//     }

//     // --- FIX IS HERE: Added 'uint8_t linkId' to match NS-3.46 Signature ---
//     void OnBackoff(std::string context, uint32_t bo, uint8_t linkId) {
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         // Now we use the actual linkId provided by the simulation!
//         auto& s = stats[nodeId].link[linkId];
//         s.backoffSum += bo; 
//         s.backoffCnt++;
//     }

//     void OnPhyState(std::string context, Time start, Time dur, WifiPhyState state) {
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         uint8_t linkId = 0;
//         // Parse context to find which link (band) this is
//         auto pos = context.find("/PhyEntities/");
//         if (pos != std::string::npos) {
//              try { linkId = std::stoi(context.substr(pos + 13, 1)); } catch (...) { linkId = 0; }
//         }

//         auto& s = stats[nodeId].link[linkId];
//         if (state == WifiPhyState::IDLE) s.phyIdle += dur.GetSeconds();
//         else if (state == WifiPhyState::TX) s.phyTx += dur.GetSeconds();
//         else s.phyRx += dur.GetSeconds();
//     }

//     void Dump() {
//         if (!monitor || !flowHelper) return;

//         monitor->CheckForLostPackets();
//         std::map<FlowId, FlowMonitor::FlowStats> flowStats = monitor->GetFlowStats();
        
//         // --- GLOBAL NETWORK METRICS ---
//         double winThroughput = 0;
//         double winDelay = 0;
//         double winJitter = 0;
//         uint64_t winRxPackets = 0;
//         uint64_t winTxPackets = 0;
//         uint64_t winLostPackets = 0;
//         uint32_t activeFlows = 0;

//         for (auto const& item : flowStats) {
//             FlowId flowId = item.first;
            
//             // Delta calculations
//             uint64_t currentRxBytes = item.second.rxBytes;
//             uint64_t currentRxPkts = item.second.rxPackets;
//             uint64_t currentTxPkts = item.second.txPackets;
//             double currentDelay = item.second.delaySum.GetSeconds();
//             double currentJitter = item.second.jitterSum.GetSeconds();

//             double deltaBytes = (double)(currentRxBytes - prevRxBytes[flowId]);
//             double deltaRxPkts = (double)(currentRxPkts - prevRxPackets[flowId]);
//             double deltaTxPkts = (double)(currentTxPkts - prevTxPackets[flowId]);
//             double deltaDelay = currentDelay - prevDelaySum[flowId];
//             double deltaJitter = currentJitter - prevJitterSum[flowId];

//             prevRxBytes[flowId] = currentRxBytes;
//             prevRxPackets[flowId] = currentRxPkts;
//             prevTxPackets[flowId] = currentTxPkts;
//             prevDelaySum[flowId] = currentDelay;
//             prevJitterSum[flowId] = currentJitter;

//             if (deltaRxPkts > 0) {
//                 activeFlows++;
//                 winRxPackets += deltaRxPkts;
//                 winThroughput += deltaBytes * 8.0; 
//                 winDelay += (deltaDelay / deltaRxPkts);
//                 winJitter += (deltaJitter / deltaRxPkts);
//             }
//             if (deltaTxPkts > deltaRxPkts) winLostPackets += (deltaTxPkts - deltaRxPkts);
//             winTxPackets += deltaTxPkts;
//         }

//         double throughputMbps = (winThroughput / WINDOW) / 1e6;
//         if (activeFlows > 0) {
//             winDelay /= activeFlows;
//             winJitter /= activeFlows;
//         }
//         double lossRatio = (winTxPackets > 0) ? (double)winLostPackets / winTxPackets : 0.0;

//         // --- AGGREGATE NODE STATS ---
//         uint64_t netTx = 0, netRx = 0, netAck = 0, netMacDrop = 0, netPhyDrop = 0, netRetrans = 0;
//         double netBackoff = 0;
//         double netBusy = 0;
//         uint32_t nodeCount = 0;

//         // Iterate over ALL nodes to sum up stats
//         for(auto const& nodePair : stats) {
//             nodeCount++;
//             auto& nodeLinks = nodePair.second.link;
            
//             // Sum across links for this node
//             for(auto& l : nodeLinks) {
//                 auto& s = l.second;
//                 netTx += s.tx; netRx += s.rx; netAck += s.ack;
//                 netMacDrop += s.macDrop; netPhyDrop += s.phyDrop;
//                 netRetrans += s.retrans;
                
//                 if (s.backoffCnt > 0) netBackoff += (double)s.backoffSum / s.backoffCnt;
//                 double totalTime = s.phyTx + s.phyRx + s.phyIdle;
//                 if (totalTime > 0) netBusy += (s.phyTx + s.phyRx) / totalTime;
//             }
//         }
        
//         // Average the averages for backoff/busy
//         if (nodeCount > 0) {
//             netBackoff /= nodeCount;
//             netBusy /= nodeCount;
//         }

//         // --- WRITE JSON ---
//         if (!(*first)) *out << ",\n";
//         *first = false;
//         *out << "{\"window\":" << g_window++ 
//              << ",\"bias\":" << bias 
//              // Network Layer (FlowMonitor)
//              << ",\"net_throughput_mbps\":" << throughputMbps
//              << ",\"net_avg_delay_ms\":" << winDelay * 1000.0
//              << ",\"net_avg_jitter_ms\":" << winJitter * 1000.0
//              << ",\"net_packet_loss_ratio\":" << lossRatio
//              << ",\"net_active_flows\":" << activeFlows
//              // Physical/MAC Layer (Aggregated from ALL nodes)
//              << ",\"mac_total_tx\":" << netTx
//              << ",\"mac_total_rx\":" << netRx
//              << ",\"mac_total_ack\":" << netAck
//              << ",\"mac_total_retrans\":" << netRetrans
//              << ",\"mac_drop_count\":" << netMacDrop
//              << ",\"phy_drop_count\":" << netPhyDrop
//              << ",\"avg_backoff_slots\":" << netBackoff
//              << ",\"channel_busy_ratio\":" << netBusy
//              << "}"; 
        
//         // Reset counters
//         for (auto& n : stats) {
//             for (auto& l : n.second.link) { l.second = LinkStats(); }
//         }
//         txCount.clear();
//     }
// };

// void Tick(Tracer* t) {
//     t->Dump();
//     Simulator::Schedule(Seconds(WINDOW), &Tick, t);
// }

// void ApplyAttack(NetDeviceContainer& devs, uint32_t minCw) {
//     for (uint32_t i = 0; i < devs.GetN(); ++i) {
//         Ptr<WifiNetDevice> dev = DynamicCast<WifiNetDevice>(devs.Get(i));
//         if (!dev) continue;
//         Ptr<WifiMac> mac = dev->GetMac();
//         PointerValue ptr;
//         if (mac->GetAttributeFailSafe("BE_Txop", ptr)) {
//             Ptr<QosTxop> qosTxop = ptr.Get<QosTxop>();
//             qosTxop->SetMinCw(minCw, 0); 
//             qosTxop->SetMinCw(minCw, 1);
//         }
//     }
// }

// int main(int argc, char* argv[]) {
//     uint32_t nSta = 2, nAp = 1, minCw = 15;
//     double bias = 0, simTime = 10.0;

//     CommandLine cmd(__FILE__);
//     cmd.AddValue("nSta", "Number of stations", nSta);
//     cmd.AddValue("nAp", "Number of APs", nAp);
//     cmd.AddValue("minCw", "Minimum Contention Window Base", minCw);
//     cmd.AddValue("bias", "Backoff bias", bias);
//     cmd.AddValue("time", "Simulation time", simTime);
//     cmd.Parse(argc, argv);

//     uint32_t attackedCw = minCw + (uint32_t)bias;

//     std::ofstream json("gnn_dataset_output_5000.json");
//     json << "[\n";
//     bool first = true;
//     Tracer tracer{&json, &first, bias};

//     NodeContainer sta, ap;
//     sta.Create(nSta); ap.Create(nAp);

//     SpectrumWifiPhyHelper phy(2); 
//     phy.AddChannel(CreateObject<MultiModelSpectrumChannel>());
//     phy.Set(0, "ChannelSettings", StringValue("{0,80,BAND_5GHZ,0}"));
//     phy.Set(1, "ChannelSettings", StringValue("{0,80,BAND_6GHZ,0}"));

//     WifiHelper wifi;
//     wifi.SetStandard(WIFI_STANDARD_80211be);
//     wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager", "DataMode", StringValue("HeMcs11"));

//     WifiMacHelper mac;
//     mac.SetType("ns3::ApWifiMac", "Ssid", SsidValue(Ssid("mlo")));
//     NetDeviceContainer apDevs = wifi.Install(phy, mac, ap);

//     mac.SetType("ns3::StaWifiMac", "Ssid", SsidValue(Ssid("mlo")));
//     NetDeviceContainer staDevs = wifi.Install(phy, mac, sta);

//     ApplyAttack(staDevs, attackedCw);
//     ApplyAttack(apDevs, attackedCw);

//     MobilityHelper mobility;
//     mobility.SetPositionAllocator("ns3::GridPositionAllocator",
//         "MinX", DoubleValue(0.0), "MinY", DoubleValue(0.0),
//         "DeltaX", DoubleValue(5.0), "DeltaY", DoubleValue(5.0),
//         "GridWidth", UintegerValue(4), "LayoutType", StringValue("RowFirst"));
//     mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
//     mobility.Install(ap); mobility.Install(sta);

//     InternetStackHelper stack;
//     stack.Install(ap); stack.Install(sta);

//     Ipv4AddressHelper address;
//     address.SetBase("192.168.1.0", "255.255.255.0");
//     Ipv4InterfaceContainer apInterface = address.Assign(apDevs);
//     Ipv4InterfaceContainer staInterface = address.Assign(staDevs);

//     // --- FULL MESH TRAFFIC ---
//     ApplicationContainer apps;
//     NodeContainer allNodes;
//     allNodes.Add(ap);
//     allNodes.Add(sta);

//     OnOffHelper onoff("ns3::UdpSocketFactory", Address());
//     onoff.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
//     onoff.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));
//     onoff.SetAttribute("DataRate", DataRateValue(DataRate("20Mbps"))); 
//     onoff.SetAttribute("PacketSize", UintegerValue(1024));

//     for (uint32_t i = 0; i < allNodes.GetN(); ++i) {
//         for (uint32_t j = 0; j < allNodes.GetN(); ++j) {
//             if (i == j) continue; 
//             Ptr<Node> destNode = allNodes.Get(j);
//             Ptr<Ipv4> ipv4 = destNode->GetObject<Ipv4>();
//             Ipv4Address destAddr = ipv4->GetAddress(1, 0).GetLocal();
//             onoff.SetAttribute("Remote", AddressValue(InetSocketAddress(destAddr, 9)));
//             apps.Add(onoff.Install(allNodes.Get(i)));
//         }
//     }
//     apps.Start(Seconds(1.0));
//     apps.Stop(Seconds(simTime));

//     FlowMonitorHelper flowHelper;
//     Ptr<FlowMonitor> monitor = flowHelper.InstallAll();
//     tracer.flowHelper = &flowHelper;
//     tracer.monitor = monitor;

//     // --- TRACES WITH CONTEXT (FIXED FOR MLO SIGNATURES) ---
//     // The key fix is in the OnBackoff callback signature, but we check paths safely too.
    
//     // 1. Transmission (Try MLO path first, then standard)
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/TxMpdu", MakeCallback(&Tracer::OnTxMpdu, &tracer));
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/TxMpdu", MakeCallback(&Tracer::OnTxMpdu, &tracer));

//     // 2. Reception
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/RxMpdu", MakeCallback(&Tracer::OnRxMpdu, &tracer));
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/RxMpdu", MakeCallback(&Tracer::OnRxMpdu, &tracer));

//     // 3. Acknowledgments
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/AckedMpdu", MakeCallback(&Tracer::OnAcked, &tracer));
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/AckedMpdu", MakeCallback(&Tracer::OnAcked, &tracer));

//     // 4. Backoff (Standard BE_Txop usually works, but requires updated signature)
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/BE_Txop/BackoffTrace", MakeCallback(&Tracer::OnBackoff, &tracer));
    
//     // 5. MAC Drops (Try standard and FrameExchangeManager)
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/Drop", MakeCallback(&Tracer::OnDropped, &tracer));
    
//     // 6. PHY Drops & State (Standard)
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/PhyRxDrop", MakeCallback(&Tracer::OnPhyDropped, &tracer));
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/State/State", MakeCallback(&Tracer::OnPhyState, &tracer));

//     AnimationInterface anim("wifi7-visual.xml");
//     anim.SetMaxPktsPerTraceFile(10000000); 
//     for (uint32_t i = 0; i < ap.GetN(); ++i) { anim.UpdateNodeDescription(ap.Get(i), "AP"); anim.UpdateNodeColor(ap.Get(i), 0, 0, 255); }
//     for (uint32_t i = 0; i < sta.GetN(); ++i) { anim.UpdateNodeDescription(sta.Get(i), "STA"); anim.UpdateNodeColor(sta.Get(i), 255, 0, 0); }

//     Simulator::Schedule(Seconds(WINDOW), &Tick, &tracer);
//     Simulator::Stop(Seconds(simTime + 0.1));
//     Simulator::Run();
//     Simulator::Destroy();

//     json << "\n]\n";
//     return 0;
// }

















/////////////////////////////////////////  WORKING V1
// #include <fstream>
// #include <map>
// #include <string>
// #include <vector>
// #include <regex>

// #include "ns3/core-module.h"
// #include "ns3/network-module.h"
// #include "ns3/wifi-module.h"
// #include "ns3/spectrum-wifi-helper.h"
// #include "ns3/multi-model-spectrum-channel.h"
// #include "ns3/mobility-module.h"
// #include "ns3/internet-module.h"
// #include "ns3/applications-module.h"
// #include "ns3/netanim-module.h"
// #include "ns3/flow-monitor-module.h" 

// using namespace ns3;

// NS_LOG_COMPONENT_DEFINE("Wifi7MloAttack");

// static const double WINDOW = 0.1; 
// static uint32_t g_window = 0;

// /* ===================== DATA STRUCTURES ===================== */
// struct LinkStats {
//     uint64_t tx = 0, rx = 0, ack = 0, macDrop = 0, phyDrop = 0, retrans = 0;
//     double phyIdle = 0, phyTx = 0, phyRx = 0;
//     uint64_t backoffSum = 0, backoffCnt = 0;
// };

// struct NodeStats {
//     std::map<uint8_t, LinkStats> link; 
// };

// // Helper to extract Node ID from context string "/NodeList/5/DeviceList/..."
// uint32_t GetNodeIdFromContext(std::string context) {
//     size_t start = context.find("/NodeList/");
//     if (start == std::string::npos) return 0;
//     start += 10; // Length of "/NodeList/"
//     size_t end = context.find("/", start);
//     if (end == std::string::npos) return 0;
//     try {
//         return std::stoi(context.substr(start, end - start));
//     } catch (...) {
//         return 0;
//     }
// }

// struct Tracer {
//     std::ofstream* out;
//     bool* first;
//     double bias;
    
//     // Map: NodeID -> Stats
//     std::map<uint32_t, NodeStats> stats;
//     std::map<uint64_t, uint32_t> txCount;
    
//     // History for FlowMonitor (Windowing)
//     std::map<FlowId, uint64_t> prevRxBytes;
//     std::map<FlowId, uint64_t> prevRxPackets;
//     std::map<FlowId, uint64_t> prevTxPackets;
//     std::map<FlowId, double> prevDelaySum;
//     std::map<FlowId, double> prevJitterSum;
    
//     FlowMonitorHelper* flowHelper = nullptr;
//     Ptr<FlowMonitor> monitor = nullptr;

//     // --- CALLBACKS ---

//     void OnTxMpdu(std::string context, Ptr<const WifiMpdu> mpdu) {
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         // Track unique packet ID to count how many times it is sent (for retransmissions)
//         txCount[mpdu->GetPacket()->GetUid()]++;
//         stats[nodeId].link[0].tx++;
//     }

//     void OnRxMpdu(std::string context, Ptr<const WifiMpdu> mpdu) {
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         stats[nodeId].link[0].rx++;
//     }

//     void OnAcked(std::string context, Ptr<const WifiMpdu> mpdu) {
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         uint64_t uid = mpdu->GetPacket()->GetUid();
//         stats[nodeId].link[0].ack++;
        
//         // If we saw this packet ID sent more than once, it was a retransmission
//         if (txCount[uid] > 1) {
//             stats[nodeId].link[0].retrans += (txCount[uid] - 1);
//         }
//         // Clean up to save memory
//         txCount.erase(uid); 
//     }

//     // 1. GENERIC MAC DROP
//     void OnDropped(std::string context, Ptr<const WifiMpdu> mpdu, WifiMacDropReason reason) { 
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         stats[nodeId].link[0].macDrop++; 
//     }

//     // 2. QUEUE DROP (Crucial for Congestion Attacks)
//     void OnQueueDrop(std::string context, Ptr<const WifiMpdu> mpdu) {
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         stats[nodeId].link[0].macDrop++; // Count queue drops as MAC drops
//     }

//     // 3. PHY DROP (Updated for MLO)
//     void OnPhyDropped(std::string context, Ptr<const Packet> packet, WifiPhyRxfailureReason reason) {
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         stats[nodeId].link[0].phyDrop++;
//     }

//     // 4. BACKOFF (With MLO Signature)
//     void OnBackoff(std::string context, uint32_t bo, uint8_t linkId) {
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         auto& s = stats[nodeId].link[linkId];
//         s.backoffSum += bo; 
//         s.backoffCnt++;
//     }

//     void OnPhyState(std::string context, Time start, Time dur, WifiPhyState state) {
//         uint32_t nodeId = GetNodeIdFromContext(context);
//         uint8_t linkId = 0;
//         // Parse context to find which link (band) this is
//         auto pos = context.find("/PhyEntities/");
//         if (pos != std::string::npos) {
//              try { linkId = std::stoi(context.substr(pos + 13, 1)); } catch (...) { linkId = 0; }
//         }

//         auto& s = stats[nodeId].link[linkId];
//         if (state == WifiPhyState::IDLE) s.phyIdle += dur.GetSeconds();
//         else if (state == WifiPhyState::TX) s.phyTx += dur.GetSeconds();
//         else s.phyRx += dur.GetSeconds();
//     }

//     void Dump() {
//         if (!monitor || !flowHelper) return;

//         monitor->CheckForLostPackets();
//         std::map<FlowId, FlowMonitor::FlowStats> flowStats = monitor->GetFlowStats();
        
//         double winThroughput = 0;
//         double winDelay = 0;
//         double winJitter = 0;
//         uint64_t winRxPackets = 0;
//         uint64_t winTxPackets = 0;
//         uint64_t winLostPackets = 0;
//         uint32_t activeFlows = 0;

//         for (auto const& item : flowStats) {
//             FlowId flowId = item.first;
            
//             uint64_t currentRxBytes = item.second.rxBytes;
//             uint64_t currentRxPkts = item.second.rxPackets;
//             uint64_t currentTxPkts = item.second.txPackets;
//             double currentDelay = item.second.delaySum.GetSeconds();
//             double currentJitter = item.second.jitterSum.GetSeconds();

//             double deltaBytes = (double)(currentRxBytes - prevRxBytes[flowId]);
//             double deltaRxPkts = (double)(currentRxPkts - prevRxPackets[flowId]);
//             double deltaTxPkts = (double)(currentTxPkts - prevTxPackets[flowId]);
//             double deltaDelay = currentDelay - prevDelaySum[flowId];
//             double deltaJitter = currentJitter - prevJitterSum[flowId];

//             prevRxBytes[flowId] = currentRxBytes;
//             prevRxPackets[flowId] = currentRxPkts;
//             prevTxPackets[flowId] = currentTxPkts;
//             prevDelaySum[flowId] = currentDelay;
//             prevJitterSum[flowId] = currentJitter;

//             if (deltaRxPkts > 0) {
//                 activeFlows++;
//                 winRxPackets += deltaRxPkts;
//                 winThroughput += deltaBytes * 8.0; 
//                 winDelay += (deltaDelay / deltaRxPkts);
//                 winJitter += (deltaJitter / deltaRxPkts);
//             }
//             if (deltaTxPkts > deltaRxPkts) winLostPackets += (deltaTxPkts - deltaRxPkts);
//             winTxPackets += deltaTxPkts;
//         }

//         double throughputMbps = (winThroughput / WINDOW) / 1e6;
//         if (activeFlows > 0) {
//             winDelay /= activeFlows;
//             winJitter /= activeFlows;
//         }
//         double lossRatio = (winTxPackets > 0) ? (double)winLostPackets / winTxPackets : 0.0;

//         uint64_t netTx = 0, netRx = 0, netAck = 0, netMacDrop = 0, netPhyDrop = 0, netRetrans = 0;
//         double netBackoff = 0;
//         double netBusy = 0;
//         uint32_t nodeCount = 0;

//         for(auto const& nodePair : stats) {
//             nodeCount++;
//             auto& nodeLinks = nodePair.second.link;
            
//             for(auto& l : nodeLinks) {
//                 auto& s = l.second;
//                 netTx += s.tx; netRx += s.rx; netAck += s.ack;
//                 netMacDrop += s.macDrop; netPhyDrop += s.phyDrop;
//                 netRetrans += s.retrans;
                
//                 if (s.backoffCnt > 0) netBackoff += (double)s.backoffSum / s.backoffCnt;
//                 double totalTime = s.phyTx + s.phyRx + s.phyIdle;
//                 if (totalTime > 0) netBusy += (s.phyTx + s.phyRx) / totalTime;
//             }
//         }
        
//         if (nodeCount > 0) {
//             netBackoff /= nodeCount;
//             netBusy /= nodeCount;
//         }

//         if (!(*first)) *out << ",\n";
//         *first = false;
//         *out << "{\"window\":" << g_window++ 
//              << ",\"bias\":" << bias 
//              << ",\"net_throughput_mbps\":" << throughputMbps
//              << ",\"net_avg_delay_ms\":" << winDelay * 1000.0
//              << ",\"net_avg_jitter_ms\":" << winJitter * 1000.0
//              << ",\"net_packet_loss_ratio\":" << lossRatio
//              << ",\"net_active_flows\":" << activeFlows
//              << ",\"mac_total_tx\":" << netTx
//              << ",\"mac_total_rx\":" << netRx
//              << ",\"mac_total_ack\":" << netAck
//              << ",\"mac_total_retrans\":" << netRetrans
//              << ",\"mac_drop_count\":" << netMacDrop
//              << ",\"phy_drop_count\":" << netPhyDrop
//              << ",\"avg_backoff_slots\":" << netBackoff
//              << ",\"channel_busy_ratio\":" << netBusy
//              << "}"; 
        
//         for (auto& n : stats) {
//             for (auto& l : n.second.link) { l.second = LinkStats(); }
//         }
//         // Do NOT clear txCount here, as retransmissions span windows
//     }
// };

// void Tick(Tracer* t) {
//     t->Dump();
//     Simulator::Schedule(Seconds(WINDOW), &Tick, t);
// }

// void ApplyAttack(NetDeviceContainer& devs, uint32_t minCw) {
//     for (uint32_t i = 0; i < devs.GetN(); ++i) {
//         Ptr<WifiNetDevice> dev = DynamicCast<WifiNetDevice>(devs.Get(i));
//         if (!dev) continue;
//         Ptr<WifiMac> mac = dev->GetMac();
//         PointerValue ptr;
//         if (mac->GetAttributeFailSafe("BE_Txop", ptr)) {
//             Ptr<QosTxop> qosTxop = ptr.Get<QosTxop>();
//             qosTxop->SetMinCw(minCw, 0); 
//             qosTxop->SetMinCw(minCw, 1);
//         }
//     }
// }

// int main(int argc, char* argv[]) {
//     uint32_t nSta = 2, nAp = 1, minCw = 15;
//     double bias = 0, simTime = 10.0;

//     CommandLine cmd(__FILE__);
//     cmd.AddValue("nSta", "Number of stations", nSta);
//     cmd.AddValue("nAp", "Number of APs", nAp);
//     cmd.AddValue("minCw", "Minimum Contention Window Base", minCw);
//     cmd.AddValue("bias", "Backoff bias", bias);
//     cmd.AddValue("time", "Simulation time", simTime);
//     cmd.Parse(argc, argv);

//     uint32_t attackedCw = minCw + (uint32_t)bias;

//     std::ofstream json("apple_neg5000.json");
//     json << "[\n";
//     bool first = true;
//     Tracer tracer{&json, &first, bias};

//     NodeContainer sta, ap;
//     sta.Create(nSta); ap.Create(nAp);

//     SpectrumWifiPhyHelper phy(2); 
//     phy.AddChannel(CreateObject<MultiModelSpectrumChannel>());
//     phy.Set(0, "ChannelSettings", StringValue("{0,80,BAND_5GHZ,0}"));
//     phy.Set(1, "ChannelSettings", StringValue("{0,80,BAND_6GHZ,0}"));

//     WifiHelper wifi;
//     wifi.SetStandard(WIFI_STANDARD_80211be);
//     wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager", "DataMode", StringValue("HeMcs11"));

//     WifiMacHelper mac;
//     mac.SetType("ns3::ApWifiMac", "Ssid", SsidValue(Ssid("mlo")));
//     NetDeviceContainer apDevs = wifi.Install(phy, mac, ap);

//     mac.SetType("ns3::StaWifiMac", "Ssid", SsidValue(Ssid("mlo")));
//     NetDeviceContainer staDevs = wifi.Install(phy, mac, sta);

//     ApplyAttack(staDevs, attackedCw);
//     ApplyAttack(apDevs, attackedCw);

//     MobilityHelper mobility;
//     mobility.SetPositionAllocator("ns3::GridPositionAllocator",
//         "MinX", DoubleValue(0.0), "MinY", DoubleValue(0.0),
//         "DeltaX", DoubleValue(5.0), "DeltaY", DoubleValue(5.0),
//         "GridWidth", UintegerValue(4), "LayoutType", StringValue("RowFirst"));
//     mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
//     mobility.Install(ap); mobility.Install(sta);

//     InternetStackHelper stack;
//     stack.Install(ap); stack.Install(sta);

//     Ipv4AddressHelper address;
//     address.SetBase("192.168.1.0", "255.255.255.0");
//     Ipv4InterfaceContainer apInterface = address.Assign(apDevs);
//     Ipv4InterfaceContainer staInterface = address.Assign(staDevs);

//     // --- FULL MESH TRAFFIC ---
//     ApplicationContainer apps;
//     NodeContainer allNodes;
//     allNodes.Add(ap);
//     allNodes.Add(sta);

//     OnOffHelper onoff("ns3::UdpSocketFactory", Address());
//     onoff.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
//     onoff.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));
//     onoff.SetAttribute("DataRate", DataRateValue(DataRate("20Mbps"))); 
//     onoff.SetAttribute("PacketSize", UintegerValue(1024));

//     for (uint32_t i = 0; i < allNodes.GetN(); ++i) {
//         for (uint32_t j = 0; j < allNodes.GetN(); ++j) {
//             if (i == j) continue; 
//             Ptr<Node> destNode = allNodes.Get(j);
//             Ptr<Ipv4> ipv4 = destNode->GetObject<Ipv4>();
//             Ipv4Address destAddr = ipv4->GetAddress(1, 0).GetLocal();
//             onoff.SetAttribute("Remote", AddressValue(InetSocketAddress(destAddr, 9)));
//             apps.Add(onoff.Install(allNodes.Get(i)));
//         }
//     }
//     apps.Start(Seconds(1.0));
//     apps.Stop(Seconds(simTime));

//     FlowMonitorHelper flowHelper;
//     Ptr<FlowMonitor> monitor = flowHelper.InstallAll();
//     tracer.flowHelper = &flowHelper;
//     tracer.monitor = monitor;

//     // --- UPDATED TRACE PATHS (FIXING THE ZEROS) ---
    
//     // 1. Transmission
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/TxMpdu", MakeCallback(&Tracer::OnTxMpdu, &tracer));
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/TxMpdu", MakeCallback(&Tracer::OnTxMpdu, &tracer));

//     // 2. Reception
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/RxMpdu", MakeCallback(&Tracer::OnRxMpdu, &tracer));
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/RxMpdu", MakeCallback(&Tracer::OnRxMpdu, &tracer));

//     // 3. Acknowledgments
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/AckedMpdu", MakeCallback(&Tracer::OnAcked, &tracer));
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/AckedMpdu", MakeCallback(&Tracer::OnAcked, &tracer));

//     // 4. Backoff
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/BE_Txop/BackoffTrace", MakeCallback(&Tracer::OnBackoff, &tracer));
    
//     // 5. DROPS (Fixes: Added Queue Drops and LinkEntity Drops)
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/Drop", MakeCallback(&Tracer::OnDropped, &tracer));
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/*/Queue/Drop", MakeCallback(&Tracer::OnQueueDrop, &tracer)); // Queue Drops!
    
//     // 6. PHY DROPS (Fixes: Look inside PhyEntities for MLO)
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/PhyEntities/*/PhyRxDrop", MakeCallback(&Tracer::OnPhyDropped, &tracer));
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/PhyRxDrop", MakeCallback(&Tracer::OnPhyDropped, &tracer));

//     // 7. PHY STATE
//     Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/State/State", MakeCallback(&Tracer::OnPhyState, &tracer));

//     AnimationInterface anim("wifi7-visual.xml");
//     anim.SetMaxPktsPerTraceFile(10000000); 
//     for (uint32_t i = 0; i < ap.GetN(); ++i) { anim.UpdateNodeDescription(ap.Get(i), "AP"); anim.UpdateNodeColor(ap.Get(i), 0, 0, 255); }
//     for (uint32_t i = 0; i < sta.GetN(); ++i) { anim.UpdateNodeDescription(sta.Get(i), "STA"); anim.UpdateNodeColor(sta.Get(i), 255, 0, 0); }

//     Simulator::Schedule(Seconds(WINDOW), &Tick, &tracer);
//     Simulator::Stop(Seconds(simTime + 0.1));
//     Simulator::Run();
//     Simulator::Destroy();

//     json << "\n]\n";
//     return 0;
// }











////////////////////////////////// WORKING V2
#include <fstream>
#include <map>
#include <string>
#include <vector>
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/wifi-module.h"
#include "ns3/spectrum-wifi-helper.h"
#include "ns3/multi-model-spectrum-channel.h"
#include "ns3/mobility-module.h"
#include "ns3/internet-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h" 
#include "ns3/netanim-module.h"


using namespace ns3;

NS_LOG_COMPONENT_DEFINE("Wifi7MloAttack");

static const double WINDOW = 0.1; 
static uint32_t g_window = 0;

// --- DATA COLLECTION STRUCTURES ---
struct LinkStats {
    uint64_t tx = 0, rx = 0, ack = 0, macDrop = 0, phyDrop = 0, retrans = 0;
    double phyIdle = 0, phyTx = 0, phyRx = 0;
    uint64_t backoffSum = 0, backoffCnt = 0;
};

struct NodeStats {
    std::map<uint8_t, LinkStats> link; 
};

// Helper to extract Node ID
uint32_t GetNodeId(std::string context) {
    size_t start = context.find("/NodeList/");
    if (start == std::string::npos) return 0;
    start += 10; 
    size_t end = context.find("/", start);
    if (end == std::string::npos) return 0;
    return std::stoi(context.substr(start, end - start));
}

struct Tracer {
    std::ofstream* out;
    bool* first;
    double bias;
    
    std::map<uint32_t, NodeStats> stats;
    std::map<uint64_t, uint32_t> txCount; // Map Packet UID -> Transmit Count
    
    // Flow Monitor History
    std::map<FlowId, uint64_t> prevRxBytes, prevRxPackets, prevTxPackets;
    std::map<FlowId, double> prevDelaySum, prevJitterSum;
    FlowMonitorHelper* flowHelper = nullptr;
    Ptr<FlowMonitor> monitor = nullptr;

    // --- NEW: Handle Aggregated Packets (PSDU) ---
    void OnTxPsdu(std::string context, Ptr<const WifiPsdu> psdu) {
        uint32_t nodeId = GetNodeId(context);
        
        // A PSDU contains multiple MPDUs (packets). We count them all.
        uint32_t nPackets = psdu->GetNMpdus();
        stats[nodeId].link[0].tx += nPackets;

        // Track retransmissions for every packet in the bundle
        for (auto it = psdu->begin(); it != psdu->end(); ++it) {
             Ptr<const WifiMpdu> mpdu = *it;
             uint64_t uid = mpdu->GetPacket()->GetUid();
             txCount[uid]++;
        }
    }

    void OnRxPsdu(std::string context, Ptr<const WifiPsdu> psdu, RxSignalInfo rxInfo, WifiTxVector txVector, std::vector<bool> status) {
        uint32_t nodeId = GetNodeId(context);
        // Only count successfully received MPDUs in the aggregate
        uint32_t successCount = 0;
        for (bool outcome : status) {
            if (outcome) successCount++;
        }
        stats[nodeId].link[0].rx += successCount;
    }

    // Fallback for Non-MLO / Management frames
    void OnTxMpdu(std::string context, Ptr<const WifiMpdu> mpdu) {
        uint32_t nodeId = GetNodeId(context);
        stats[nodeId].link[0].tx++;
        txCount[mpdu->GetPacket()->GetUid()]++;
    }

    void OnAcked(std::string context, Ptr<const WifiMpdu> mpdu) {
        uint32_t nodeId = GetNodeId(context);
        stats[nodeId].link[0].ack++;
        
        uint64_t uid = mpdu->GetPacket()->GetUid();
        if (txCount[uid] > 1) {
            stats[nodeId].link[0].retrans += (txCount[uid] - 1);
        }
        // Don't erase immediately, other links might retransmit
    }

    // --- DROPS ---
    // If these are still 0, it means the Queue is NOT full (common in simple sims)
    void OnQueueDrop(std::string context, Ptr<const WifiMpdu> mpdu) {
        uint32_t nodeId = GetNodeId(context);
        stats[nodeId].link[0].macDrop++; 
    }
    
    void OnPhyDrop(std::string context, Ptr<const Packet> packet, WifiPhyRxfailureReason reason) {
        uint32_t nodeId = GetNodeId(context);
        stats[nodeId].link[0].phyDrop++;
    }

    void OnBackoff(std::string context, uint32_t bo, uint8_t linkId) {
        uint32_t nodeId = GetNodeId(context);
        auto& s = stats[nodeId].link[linkId];
        s.backoffSum += bo; 
        s.backoffCnt++;
    }

    void OnPhyState(std::string context, Time start, Time dur, WifiPhyState state) {
        uint32_t nodeId = GetNodeId(context);
        // Simple mapping: link 0 is 5GHz, link 1 is 6GHz usually
        uint8_t linkId = 0; 
        if (context.find("PhyEntities/1") != std::string::npos) linkId = 1;

        auto& s = stats[nodeId].link[linkId];
        if (state == WifiPhyState::IDLE) s.phyIdle += dur.GetSeconds();
        else if (state == WifiPhyState::TX) s.phyTx += dur.GetSeconds();
        else s.phyRx += dur.GetSeconds();
    }

    void Dump() {
        if (!monitor) return;
        monitor->CheckForLostPackets();
        std::map<FlowId, FlowMonitor::FlowStats> flowStats = monitor->GetFlowStats();
        
        double winThroughput = 0, winDelay = 0, winJitter = 0;
        uint64_t winRxPackets = 0, winTxPackets = 0, winLost = 0;
        uint32_t activeFlows = 0;

        for (auto const& item : flowStats) {
            FlowId flowId = item.first;
            double rxDelta = (double)(item.second.rxPackets - prevRxPackets[flowId]);
            double txDelta = (double)(item.second.txPackets - prevTxPackets[flowId]);
            double bytesDelta = (double)(item.second.rxBytes - prevRxBytes[flowId]);
            
            prevRxPackets[flowId] = item.second.rxPackets;
            prevTxPackets[flowId] = item.second.txPackets;
            prevRxBytes[flowId] = item.second.rxBytes;

            if (rxDelta > 0) {
                activeFlows++;
                winRxPackets += rxDelta;
                winThroughput += bytesDelta * 8.0;
                
                double dDelay = item.second.delaySum.GetSeconds() - prevDelaySum[flowId];
                double dJitter = item.second.jitterSum.GetSeconds() - prevJitterSum[flowId];
                prevDelaySum[flowId] = item.second.delaySum.GetSeconds();
                prevJitterSum[flowId] = item.second.jitterSum.GetSeconds();

                winDelay += (dDelay / rxDelta);
                winJitter += (dJitter / rxDelta);
            }
            if (txDelta > rxDelta) winLost += (txDelta - rxDelta);
            winTxPackets += txDelta;
        }

        double mbps = (winThroughput / WINDOW) / 1e6;
        if (activeFlows > 0) { winDelay /= activeFlows; winJitter /= activeFlows; }
        double lossRatio = (winTxPackets > 0) ? (double)winLost / winTxPackets : 0.0;

        // Aggregating Node Stats
        uint64_t totTx = 0, totRx = 0, totAck = 0, totMacDrop = 0, totPhyDrop = 0, totRetrans = 0;
        double avgBackoff = 0, busyRatio = 0;
        int nodesWithBackoff = 0, nodesBusy = 0;

        for (auto& nodePair : stats) {
            for (auto& linkPair : nodePair.second.link) {
                auto& s = linkPair.second;
                totTx += s.tx; totRx += s.rx; totAck += s.ack;
                totMacDrop += s.macDrop; totPhyDrop += s.phyDrop;
                totRetrans += s.retrans;

                if (s.backoffCnt > 0) {
                    avgBackoff += (double)s.backoffSum / s.backoffCnt;
                    nodesWithBackoff++;
                }
                double tTime = s.phyTx + s.phyRx + s.phyIdle;
                if (tTime > 0) {
                    busyRatio += (s.phyTx + s.phyRx) / tTime;
                    nodesBusy++;
                }
                // Reset per-window stats
                s.tx = s.rx = s.ack = s.macDrop = s.phyDrop = s.retrans = s.backoffSum = s.backoffCnt = 0;
                s.phyTx = s.phyRx = s.phyIdle = 0;
            }
        }
        if (nodesWithBackoff > 0) avgBackoff /= nodesWithBackoff;
        if (nodesBusy > 0) busyRatio /= nodesBusy;

        if (!(*first)) *out << ",\n";
        *first = false;
        *out << "{\"window\":" << g_window++ 
             << ",\"bias\":" << bias 
             << ",\"net_throughput_mbps\":" << mbps
             << ",\"net_avg_delay_ms\":" << winDelay * 1000.0
             << ",\"net_avg_jitter_ms\":" << winJitter * 1000.0
             << ",\"net_packet_loss_ratio\":" << lossRatio
             << ",\"net_active_flows\":" << activeFlows
             << ",\"mac_total_tx\":" << totTx
             << ",\"mac_total_rx\":" << totRx
             << ",\"mac_total_ack\":" << totAck
             << ",\"mac_total_retrans\":" << totRetrans
             << ",\"mac_drop_count\":" << totMacDrop
             << ",\"phy_drop_count\":" << totPhyDrop
             << ",\"avg_backoff_slots\":" << avgBackoff
             << ",\"channel_busy_ratio\":" << busyRatio
             << "}"; 
    }
};

void Tick(Tracer* t) {
    t->Dump();
    Simulator::Schedule(Seconds(WINDOW), &Tick, t);
}

void ApplyAttack(NetDeviceContainer& devs, int bias, uint32_t minCw) {
    for (uint32_t i = 0; i < devs.GetN(); ++i) {
        Ptr<WifiNetDevice> dev = DynamicCast<WifiNetDevice>(devs.Get(i));
        if (!dev) continue;
        Ptr<WifiMac> mac = dev->GetMac();
        PointerValue ptr;
        
        // --- FIXED NEGATIVE BIAS LOGIC ---
        uint32_t newCw;
        if (bias < 0) {
            // Prevent underflow (wrapping to 4 billion)
            uint32_t absBias = (uint32_t)(-bias);
            if (absBias >= minCw) newCw = 0; // Clamp to 0
            else newCw = minCw - absBias;
        } else {
            newCw = minCw + (uint32_t)bias;
        }

        if (mac->GetAttributeFailSafe("BE_Txop", ptr)) {
            Ptr<QosTxop> qosTxop = ptr.Get<QosTxop>();
            qosTxop->SetMinCw(newCw, 0); 
            qosTxop->SetMinCw(newCw, 1);
        }
    }
}

int main(int argc, char* argv[]) {
    uint32_t nSta = 2, nAp = 2, minCw = 15;
    double bias = 0, simTime = 240.0;

    std::string jsonPath = "default.json";
    std::string xmlPath = "default.xml";


    CommandLine cmd(__FILE__);
    cmd.AddValue("bias", "Backoff bias", bias);
    cmd.AddValue("time", "Simulation time", simTime);
    cmd.AddValue ("jsonPath", "Path for JSON output", jsonPath);
    cmd.AddValue ("xmlPath", "Path for XML output", xmlPath);
    cmd.Parse(argc, argv);

    std::ofstream json("Wifi7_Datasets/Normal/session_2_scenario_1.json");        //////////////////////////////////////////// rename this here
    json << "[\n";
    bool first = true;
    Tracer tracer{&json, &first, bias};

    NodeContainer sta, ap;
    sta.Create(nSta); ap.Create(nAp);

    SpectrumWifiPhyHelper phy(2); 
    phy.AddChannel(CreateObject<MultiModelSpectrumChannel>());
    phy.Set(0, "ChannelSettings", StringValue("{0,80,BAND_5GHZ,0}"));
    phy.Set(1, "ChannelSettings", StringValue("{0,80,BAND_6GHZ,0}"));

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211be);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager", "DataMode", StringValue("HeMcs11"));
    
    WifiMacHelper mac;
    mac.SetType("ns3::ApWifiMac", "Ssid", SsidValue(Ssid("mlo")));
    NetDeviceContainer apDevs = wifi.Install(phy, mac, ap);

    mac.SetType("ns3::StaWifiMac", "Ssid", SsidValue(Ssid("mlo")));
    NetDeviceContainer staDevs = wifi.Install(phy, mac, sta);

    // Apply Attack with Integer Fix
    ApplyAttack(staDevs, (int)bias, minCw);
    ApplyAttack(apDevs, (int)bias, minCw);

    MobilityHelper mobility;
    mobility.SetPositionAllocator("ns3::GridPositionAllocator", "MinX", DoubleValue(0.0), "MinY", DoubleValue(0.0), "DeltaX", DoubleValue(5.0), "DeltaY", DoubleValue(5.0), "GridWidth", UintegerValue(4), "LayoutType", StringValue("RowFirst"));
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(ap); mobility.Install(sta);

    InternetStackHelper stack;
    stack.Install(ap); stack.Install(sta);
    Ipv4AddressHelper address;
    address.SetBase("192.168.1.0", "255.255.255.0");
    address.Assign(apDevs); address.Assign(staDevs);

    ApplicationContainer apps;
    OnOffHelper onoff("ns3::UdpSocketFactory", Address());
    onoff.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
    onoff.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));
    onoff.SetAttribute("DataRate", DataRateValue(DataRate("800Mbps"))); 
    onoff.SetAttribute("PacketSize", UintegerValue(1024));

    // Create Mesh Traffic
    for (uint32_t i = 0; i < ap.GetN() + sta.GetN(); ++i) {
        for (uint32_t j = 0; j < ap.GetN() + sta.GetN(); ++j) {
            if (i == j) continue;
            Ptr<Node> dst = (j < ap.GetN()) ? ap.Get(j) : sta.Get(j - ap.GetN());
            Ipv4Address dstAddr = dst->GetObject<Ipv4>()->GetAddress(1, 0).GetLocal();
            onoff.SetAttribute("Remote", AddressValue(InetSocketAddress(dstAddr, 9)));
            apps.Add(onoff.Install((i < ap.GetN()) ? ap.Get(i) : sta.Get(i - ap.GetN())));
        }
    }
    apps.Start(Seconds(1.0));
    apps.Stop(Seconds(simTime));

    FlowMonitorHelper flowHelper;
    Ptr<FlowMonitor> monitor = flowHelper.InstallAll();
    tracer.flowHelper = &flowHelper;
    tracer.monitor = monitor;

    // --- UPDATED TRACE PATHS FOR WIFI 7 ---
    // 1. PSDU Hooks (Crucial for Aggregation)
    Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/TxPsdu", MakeCallback(&Tracer::OnTxPsdu, &tracer));
    Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/RxPsdu", MakeCallback(&Tracer::OnRxPsdu, &tracer));
    
    // 2. ACK Hooks
    Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/AckedMpdu", MakeCallback(&Tracer::OnAcked, &tracer));
    
    // 3. Queue Drops
    Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/*/Queue/Drop", MakeCallback(&Tracer::OnQueueDrop, &tracer));
    
    // 4. PHY Hooks
    Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/PhyEntities/*/PhyRxDrop", MakeCallback(&Tracer::OnPhyDrop, &tracer));
    Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/State/State", MakeCallback(&Tracer::OnPhyState, &tracer));
    
    // 5. Backoff
    Config::ConnectFailSafe("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/BE_Txop/BackoffTrace", MakeCallback(&Tracer::OnBackoff, &tracer));



    Simulator::Schedule(Seconds(WINDOW), &Tick, &tracer);
    Simulator::Stop(Seconds(simTime + 0.1));
    Simulator::Run();
    Simulator::Destroy();

    json << "\n]\n";
    return 0;
}


// 1063 1147