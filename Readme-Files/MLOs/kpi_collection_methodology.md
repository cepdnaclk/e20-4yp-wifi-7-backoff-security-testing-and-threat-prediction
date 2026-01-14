# KPI Collection Methodology

A key strength of this project is its comprehensive and detailed data collection methodology. The simulation scripts are instrumented to collect a wide range of Key Performance Indicators (KPIs) at different layers of the network stack. This allows for a deep and multi-faceted analysis of the network's performance under different backoff manipulation scenarios.

## The `Tracer` Struct

The core of the data collection mechanism is the `Tracer` struct. This struct holds all the necessary data structures and methods to collect, process, and output the KPIs. It is instantiated in the `main` function and its methods are connected to various trace sources in the ns-3 Wi-Fi model.

## Data Collection approach

The data is collected in a time-windowed fashion. A `Tick` function is scheduled to be called periodically (every `WINDOW` seconds, which is set to 0.1s in the scripts). This function calls the `Tracer::Dump()` method, which processes the collected data for the last window and writes it to a JSON file.

This approach provides a time-series view of the network's performance, which is much more powerful than simply collecting aggregate statistics at the end of the simulation. It allows for the analysis of the dynamic behavior of the network and how it evolves over time.

## Collected KPIs

The collected KPIs can be broadly categorized into two groups: network-level KPIs (collected using `FlowMonitor`) and MAC/PHY-level KPIs (collected using various trace sources).

### Network-Level KPIs (from `FlowMonitor`)

The `FlowMonitor` is used to collect per-flow statistics, which are then aggregated to provide a network-wide view of performance. The following KPIs are collected:

-   `net_throughput_mbps`: The total throughput of the network in Mbps.
-   `net_avg_delay_ms`: The average end-to-end delay of packets in milliseconds.
-   `net_avg_jitter_ms`: The average jitter in milliseconds.
-   `net_packet_loss_ratio`: The ratio of lost packets to transmitted packets.
-   `net_active_flows`: The number of active flows in the network.

### MAC/PHY-Level KPIs (from Trace Sources)

The `Tracer` struct connects to a number of trace sources in the Wi-Fi MAC and PHY layers to collect detailed statistics about the low-level behavior of the network. The collected KPIs include:

-   `mac_total_tx`: The total number of transmitted MPDUs/PSDUs.
-   `mac_total_rx`: The total number of received MPDUs/PSDUs.
-   `mac_total_ack`: The total number of received ACKs.
-   `mac_total_retrans`: The total number of retransmissions.
-   `mac_drop_count`: The number of packets dropped at the MAC layer.
-   `phy_drop_count`: The number of packets dropped at the PHY layer.
-   `avg_backoff_slots`: The average backoff duration in slots. This is a crucial KPI for this project, as it directly reflects the impact of the `bias` parameter.
-   `channel_busy_ratio`: The ratio of time the channel was busy (either transmitting or receiving).

## Trace Source Connections

The `Tracer` methods are connected to the following trace sources using `Config::ConnectFailSafe` to ensure that the simulation does not crash if a trace path is not found:

-   `/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/TxPsdu`: For transmitted PSDUs in MLO.
-   `/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/RxPsdu`: For received PSDUs in MLO.
-   `/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/AckedMpdu`: For received ACKs.
-   `/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/*/Queue/Drop`: For packets dropped from the MAC queue.
-   `/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/PhyEntities/*/PhyRxDrop`: For packets dropped at the PHY layer.
-   `/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/State/State`: To monitor the PHY state (idle, tx, rx) for calculating the channel busy ratio.
-in- `BE_Txop/BackoffTrace`: For backoff duration. This is connected to the `BE_Txop` trace source to specifically monitor the backoff behavior of the Best Effort access category.

This detailed and multi-layered approach to data collection is a significant strength of the project, enabling a thorough and nuanced analysis of the impact of backoff manipulation on Wi-Fi 7 MLO networks.
