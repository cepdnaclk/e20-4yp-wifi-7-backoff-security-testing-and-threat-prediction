# Project Overview: Wi-Fi 7 MLO Performance Analysis under Backoff Manipulation

This project investigates the performance of Wi-Fi 7 (802.11be) Multi-Link Operation (MLO) networks under various conditions, with a specific focus on the impact of manipulating the backoff mechanism. The goal is to collect a comprehensive set of Key Performance Indicators (KPIs) to understand how changes in the contention window (CW) affect network behavior.

## Simulation Environment

The simulations are built upon the ns-3 network simulator (version 3.46.1), which provides a detailed and extensible model of the Wi-Fi 7 standard. The project uses custom C++ simulation scripts located in the `scratch` directory to define the network topology, traffic patterns, and data collection methods.

## Methodology

The core of the project is a series of simulations that modify the `minCw` (minimum contention window) parameter of the Wi-Fi MAC layer for all nodes in the network. This is achieved by introducing a `bias` value, which is added to the default `minCw`. By using different bias values (positive, negative, and zero), the project simulates three main scenarios:

1.  **Normal Operation:** The default backoff parameters are used, providing a baseline for performance.
2.  **Increased Contention (Positive Bias):** The `minCw` is increased, making nodes less aggressive in contending for the channel. This is expected to reduce collisions but may also decrease throughput.
3.  **Decreased Contention (Negative Bias):** The `minCw` is decreased, making nodes more aggressive. This can be seen as a form of a Denial-of-Service (DoS) attack, where malicious or misbehaving nodes can monopolize the channel, leading to increased collisions and reduced performance for other nodes.

## Data Collection and Analysis

The simulations are heavily instrumented to collect a rich dataset of KPIs at both the network and MAC/PHY layers. This data is collected in a time-windowed fashion and written to JSON files, making it suitable for time-series analysis and for use as a dataset for training machine learning models, such as Graph Neural Networks (GNNs), as hinted by the output file names.

The collected KPIs include:
-   Network-level metrics (throughput, delay, jitter, packet loss) from `FlowMonitor`.
-   MAC/PHY-level metrics (TX/RX counts, retransmissions, drops, backoff statistics, channel busy ratio) from various trace sources in the ns-3 Wi-Fi model.

This comprehensive data collection allows for a deep understanding of the complex interactions between the backoff mechanism, channel contention, and overall network performance in a Wi-Fi 7 MLO environment.
