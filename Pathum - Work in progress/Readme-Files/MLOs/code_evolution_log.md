# Code Evolution Log

The simulation scripts, particularly `scratch/wifi7-mlo-Normal.cc`, show a clear history of iterative development and refinement. By examining the commented-out code blocks, we can trace the evolution of the data collection and simulation logic. This demonstrates a robust development process, where the methodology was gradually improved to be more accurate and comprehensive.

## Initial Version (V1)

The earliest version of the code, marked as `WORKING V1`, established the foundational data collection framework.

### Key Features of V1:

*   **Basic KPI Collection:** It collected essential metrics like TX/RX packets, ACKs, and drops.
*   **Retransmission Counting:** It implemented a basic retransmission counting mechanism by tracking the number of times a packet's unique ID was seen in the `OnTxMpdu` callback.
*   **Simple Drop Tracking:** It used a generic `OnDropped` callback for MAC drops and a specific `OnQueueDrop` callback, indicating an early focus on congestion-related metrics.
*   **MLO Backoff Signature:** A key fix was introduced in the `OnBackoff` callback signature (`void OnBackoff(std::string context, uint32_t bo, uint8_t linkId)`), which was updated to match the ns-3.46 MLO implementation. This was crucial for correctly capturing per-link backoff statistics.

### Limitations of V1:

*   **Inaccurate Retransmission Logic:** The logic for counting retransmissions was flawed. It cleaned up the `txCount` map immediately after a packet was ACKed, which would fail to correctly count retransmissions that might occur on other links in an MLO setup.
*   **Incomplete Trace Paths:** The trace paths for drops and PHY state were not fully optimized for MLO, potentially leading to incomplete data. For instance, it relied on `/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/State/State` which might not capture per-link PHY states correctly in all MLO scenarios.

## Intermediate Version (V2)

The version marked as `WORKING V2` represents a significant step forward in the accuracy and detail of the data collection.

### Improvements in V2:

*   **Corrected Retransmission Logic:** The `txCount` map is no longer cleared immediately after an ACK. The comment `// Don't erase immediately, other links might retransmit` explicitly notes this crucial fix, ensuring that retransmissions across different links in an MLO setup are counted correctly.
*   **More Robust Trace Paths:** The trace paths were updated to be more specific and robust for MLO. For example, it added `/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/LinkEntities/*/FrameExchangeManager/TxMpdu` to capture transmissions on specific links. It also added specific paths for queue drops and PHY drops within `PhyEntities`.
*   **PSDU Handling:** This version introduced `OnTxPsdu` and `OnRxPsdu` callbacks to handle aggregated packets (PSDUs). This is a critical improvement for accurately measuring throughput and packet counts in modern Wi-Fi standards like Wi-Fi 7, which rely heavily on aggregation.

### Limitations of V2:

*   **Simplified Link Mapping:** The `OnPhyState` callback used a simple heuristic (`if (context.find("PhyEntities/1") != std::string::npos) linkId = 1;`) to determine the link ID. While often correct in a simple two-link setup, this is not a fully robust way to map PHY state to a specific link.

## Latest Version

The most recent version of the code (the uncommented version at the top of the file) builds upon V2 and represents the most mature version of the simulation script.

### Improvements in the Latest Version:

*   **Refined Negative Bias Logic:** The `ApplyAttack` function includes the "FIXED NEGATIVE BIAS LOGIC". This is a critical bug fix that prevents integer underflow when applying a negative bias to the contention window, ensuring the simulation's accuracy when modeling aggressive backoff behavior.
*   **Cleaner Code Structure:** The code is better organized, with clear separation between data structures, callbacks, and the main simulation setup.
*   **Comprehensive Trace Connections:** The latest version uses a comprehensive set of `Config::ConnectFailSafe` calls to connect to a wide range of trace sources, ensuring that all relevant data is captured. The use of `FailSafe` also makes the script more robust to changes in the underlying ns-3 implementation.

This iterative development process, with its clear progression of fixes and improvements, is a testament to a thorough and careful approach to simulation-based research. The evolution from a basic data collection script to a robust and accurate MLO analysis tool demonstrates a deep understanding of both the ns-3 simulator and the complexities of the Wi-Fi 7 standard.
