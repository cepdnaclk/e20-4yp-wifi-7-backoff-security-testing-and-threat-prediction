#include <fstream>
#include <map>
#include <string>
#include <vector>
#include <sstream>
#include <stdexcept>
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
#include "ns3/rng-seed-manager.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("Wifi7MloDynamic");

static const double WINDOW = 0.1;
static uint32_t g_window = 0;

// ---------------------------------------------------------------------------
// Data structures (identical to wifi7-mlo-Normal.cc)
// ---------------------------------------------------------------------------

struct LinkStats {
    uint64_t tx = 0, rx = 0, ack = 0, macDrop = 0, phyDrop = 0, retrans = 0;
    double phyIdle = 0, phyTx = 0, phyRx = 0;
    uint64_t backoffSum = 0, backoffCnt = 0;
};

struct NodeStats {
    std::map<uint8_t, LinkStats> link;
};

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
    double bias;   // updated at each phase transition — written to JSON per window
    uint32_t nAp = 1;
    uint32_t nSta = 2;

    std::map<uint32_t, NodeStats> stats;
    std::map<uint64_t, uint32_t> txCount;

    std::map<FlowId, uint64_t> prevRxBytes, prevRxPackets, prevTxPackets;
    std::map<FlowId, double> prevDelaySum, prevJitterSum;
    FlowMonitorHelper* flowHelper = nullptr;
    Ptr<FlowMonitor> monitor = nullptr;

    void OnTxPsdu(std::string context, Ptr<const WifiPsdu> psdu) {
        uint32_t nodeId = GetNodeId(context);
        uint32_t nPackets = psdu->GetNMpdus();
        stats[nodeId].link[0].tx += nPackets;
        for (auto it = psdu->begin(); it != psdu->end(); ++it) {
            uint64_t uid = (*it)->GetPacket()->GetUid();
            txCount[uid]++;
        }
    }

    void OnRxPsdu(std::string context, Ptr<const WifiPsdu> psdu, RxSignalInfo rxInfo,
                  WifiTxVector txVector, std::vector<bool> status) {
        uint32_t nodeId = GetNodeId(context);
        uint32_t successCount = 0;
        for (bool outcome : status) { if (outcome) successCount++; }
        stats[nodeId].link[0].rx += successCount;
    }

    void OnTxMpdu(std::string context, Ptr<const WifiMpdu> mpdu) {
        uint32_t nodeId = GetNodeId(context);
        stats[nodeId].link[0].tx++;
        txCount[mpdu->GetPacket()->GetUid()]++;
    }

    void OnAcked(std::string context, Ptr<const WifiMpdu> mpdu) {
        uint32_t nodeId = GetNodeId(context);
        stats[nodeId].link[0].ack++;
        uint64_t uid = mpdu->GetPacket()->GetUid();
        if (txCount[uid] > 1) stats[nodeId].link[0].retrans += (txCount[uid] - 1);
    }

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
             << ",\"num_ap\":" << (int)nAp
             << ",\"num_sta\":" << (int)(nAp * nSta)
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

// ---------------------------------------------------------------------------
// ApplyAttack — identical to Normal.cc, usable at any simulation time
// ---------------------------------------------------------------------------

void ApplyAttack(NetDeviceContainer& devs, int bias, uint32_t minCw) {
    for (uint32_t i = 0; i < devs.GetN(); ++i) {
        Ptr<WifiNetDevice> dev = DynamicCast<WifiNetDevice>(devs.Get(i));
        if (!dev) continue;
        Ptr<WifiMac> mac = dev->GetMac();
        PointerValue ptr;

        uint32_t newCw;
        if (bias < 0) {
            uint32_t absBias = (uint32_t)(-bias);
            newCw = (absBias >= minCw) ? 0 : minCw - absBias;
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

// ---------------------------------------------------------------------------
// Phase transition callback — called by Simulator::Schedule at each t_i
// Updates tracer->bias so the JSON output reflects the new phase.
// ---------------------------------------------------------------------------

struct PhaseState {
    Tracer* tracer;
    NetDeviceContainer* staDevs;
    NetDeviceContainer* apDevs;
    int bias;
    uint32_t minCw;
};

void ApplyPhase(PhaseState* ps) {
    ApplyAttack(*(ps->staDevs), ps->bias, ps->minCw);
    ApplyAttack(*(ps->apDevs), ps->bias, ps->minCw);
    ps->tracer->bias = ps->bias;
    NS_LOG_UNCOND("[Dynamic] Phase transition at t="
                  << Simulator::Now().GetSeconds()
                  << "s  bias=" << ps->bias);
}

// ---------------------------------------------------------------------------
// Phase schedule parser
// Input format: "t0:b0,t1:b1,t2:b2,..."  (time in seconds, bias integer)
// Example: "0:0,20:5000,40:-5000,60:0"
// ---------------------------------------------------------------------------

struct Phase {
    double time;
    int    bias;
};

std::vector<Phase> ParsePhases(const std::string& spec) {
    std::vector<Phase> phases;
    if (spec.empty()) return phases;

    std::istringstream ss(spec);
    std::string token;
    while (std::getline(ss, token, ',')) {
        size_t colon = token.find(':');
        if (colon == std::string::npos)
            NS_FATAL_ERROR("Bad phase spec token '" << token << "' — expected 'time:bias'");
        Phase p;
        p.time = std::stod(token.substr(0, colon));
        p.bias = std::stoi(token.substr(colon + 1));
        phases.push_back(p);
    }
    // Sort ascending by time so the user can write them in any order
    std::sort(phases.begin(), phases.end(),
              [](const Phase& a, const Phase& b){ return a.time < b.time; });
    return phases;
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

int main(int argc, char* argv[]) {
    uint32_t nSta = 2, nAp = 1, minCw = 15;
    uint32_t seed = 42;
    double simTime = 80.0;

    // phases: comma-separated list of "time:bias" pairs.
    // The phase at time 0 sets the initial bias.
    // Each subsequent phase schedules a bias change mid-simulation.
    // Example: "0:0,20:5000,40:-5000,60:0"
    std::string phasesSpec = "0:0";

    std::string jsonPath = "default.json";
    std::string xmlPath  = "default.xml";

    CommandLine cmd(__FILE__);
    cmd.AddValue("nAp",     "Number of access points",             nAp);
    cmd.AddValue("nSta",    "Number of stations per access point", nSta);
    cmd.AddValue("seed",    "Random seed for RngSeedManager",      seed);
    cmd.AddValue("time",    "Simulation time (seconds)",           simTime);
    cmd.AddValue("phases",  "Phase schedule: 't0:b0,t1:b1,...'",   phasesSpec);
    cmd.AddValue("jsonPath","Path for JSON output",                 jsonPath);
    cmd.AddValue("xmlPath", "Path for XML output",                  xmlPath);
    cmd.Parse(argc, argv);

    // Parse and validate phase schedule
    std::vector<Phase> phases = ParsePhases(phasesSpec);
    if (phases.empty())
        NS_FATAL_ERROR("--phases must specify at least one entry, e.g. '0:0'");

    // Initial bias comes from the first phase (time 0 by convention)
    int initialBias = phases[0].bias;

    NS_LOG_UNCOND("[Dynamic] phases=" << phasesSpec);
    NS_LOG_UNCOND("[Dynamic] initial bias=" << initialBias);
    for (auto& p : phases)
        NS_LOG_UNCOND("[Dynamic]   t=" << p.time << "s  bias=" << p.bias);

    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(1);

    std::ofstream json(jsonPath.c_str());
    json << "[\n";
    bool first = true;
    Tracer tracer{&json, &first, (double)initialBias};
    tracer.nAp  = nAp;
    tracer.nSta = nSta;

    NodeContainer sta, ap;
    sta.Create(nSta * nAp);  // total stations = nSta per AP × nAp
    ap.Create(nAp);

    SpectrumWifiPhyHelper phy(2);
    phy.AddChannel(CreateObject<MultiModelSpectrumChannel>());
    phy.Set(0, "ChannelSettings", StringValue("{0,80,BAND_5GHZ,0}"));
    phy.Set(1, "ChannelSettings", StringValue("{0,80,BAND_6GHZ,0}"));

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211be);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                 "DataMode", StringValue("HeMcs11"));

    WifiMacHelper mac;
    mac.SetType("ns3::ApWifiMac", "Ssid", SsidValue(Ssid("mlo")));
    NetDeviceContainer apDevs = wifi.Install(phy, mac, ap);

    mac.SetType("ns3::StaWifiMac", "Ssid", SsidValue(Ssid("mlo")));
    NetDeviceContainer staDevs = wifi.Install(phy, mac, sta);

    // Apply initial bias
    ApplyAttack(staDevs, initialBias, minCw);
    ApplyAttack(apDevs, initialBias, minCw);

    MobilityHelper mobility;
    mobility.SetPositionAllocator("ns3::GridPositionAllocator",
        "MinX", DoubleValue(0.0), "MinY", DoubleValue(0.0),
        "DeltaX", DoubleValue(5.0), "DeltaY", DoubleValue(5.0),
        "GridWidth", UintegerValue(4), "LayoutType", StringValue("RowFirst"));
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(ap);
    mobility.Install(sta);

    InternetStackHelper stack;
    stack.Install(ap);
    stack.Install(sta);
    Ipv4AddressHelper address;
    address.SetBase("192.168.1.0", "255.255.255.0");
    address.Assign(apDevs);
    address.Assign(staDevs);

    ApplicationContainer apps;
    OnOffHelper onoff("ns3::UdpSocketFactory", Address());
    onoff.SetAttribute("OnTime",    StringValue("ns3::ConstantRandomVariable[Constant=1]"));
    onoff.SetAttribute("OffTime",   StringValue("ns3::ConstantRandomVariable[Constant=0]"));
    onoff.SetAttribute("DataRate",  DataRateValue(DataRate("50Mbps")));
    onoff.SetAttribute("PacketSize", UintegerValue(1024));

    // Mesh traffic between all nodes
    uint32_t totalNodes = ap.GetN() + sta.GetN();
    for (uint32_t i = 0; i < totalNodes; ++i) {
        for (uint32_t j = 0; j < totalNodes; ++j) {
            if (i == j) continue;
            Ptr<Node> dst = (j < ap.GetN()) ? ap.Get(j) : sta.Get(j - ap.GetN());
            Ipv4Address dstAddr = dst->GetObject<Ipv4>()->GetAddress(1, 0).GetLocal();
            onoff.SetAttribute("Remote", AddressValue(InetSocketAddress(dstAddr, 9)));
            Ptr<Node> src = (i < ap.GetN()) ? ap.Get(i) : sta.Get(i - ap.GetN());
            apps.Add(onoff.Install(src));
        }
    }
    apps.Start(Seconds(1.0));
    apps.Stop(Seconds(simTime));

    FlowMonitorHelper flowHelper;
    Ptr<FlowMonitor> monitor = flowHelper.InstallAll();
    tracer.flowHelper = &flowHelper;
    tracer.monitor    = monitor;

    // Trace hooks
    Config::ConnectFailSafe(
        "/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/TxPsdu",
        MakeCallback(&Tracer::OnTxPsdu, &tracer));
    Config::ConnectFailSafe(
        "/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/RxPsdu",
        MakeCallback(&Tracer::OnRxPsdu, &tracer));
    Config::ConnectFailSafe(
        "/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/AckedMpdu",
        MakeCallback(&Tracer::OnAcked, &tracer));
    Config::ConnectFailSafe(
        "/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/*/Queue/Drop",
        MakeCallback(&Tracer::OnQueueDrop, &tracer));
    Config::ConnectFailSafe(
        "/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/PhyEntities/*/PhyRxDrop",
        MakeCallback(&Tracer::OnPhyDrop, &tracer));
    Config::ConnectFailSafe(
        "/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/State/State",
        MakeCallback(&Tracer::OnPhyState, &tracer));
    Config::ConnectFailSafe(
        "/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/BE_Txop/BackoffTrace",
        MakeCallback(&Tracer::OnBackoff, &tracer));

    // ---------------------------------------------------------------------------
    // Schedule phase transitions (skip index 0 — already applied as initial bias)
    // PhaseState structs live for the duration of the simulation.
    // We keep them in a vector so they're not stack-allocated.
    // ---------------------------------------------------------------------------
    std::vector<PhaseState> phaseStates;
    phaseStates.reserve(phases.size());

    for (size_t i = 1; i < phases.size(); ++i) {
        const Phase& p = phases[i];
        if (p.time <= 0.0 || p.time >= simTime) {
            NS_LOG_WARN("[Dynamic] Phase t=" << p.time
                        << "s is out of simulation range [0," << simTime << ") — skipping");
            continue;
        }
        phaseStates.push_back({&tracer, &staDevs, &apDevs, p.bias, minCw});
        Simulator::Schedule(Seconds(p.time), &ApplyPhase, &phaseStates.back());
        NS_LOG_UNCOND("[Dynamic] Scheduled phase t=" << p.time << "s  bias=" << p.bias);
    }

    // Tick every 0.1 s to emit one JSON window
    Simulator::Schedule(Seconds(WINDOW), &Tick, &tracer);
    Simulator::Stop(Seconds(simTime + 0.1));
    Simulator::Run();
    Simulator::Destroy();

    json << "\n]\n";
    return 0;
}
