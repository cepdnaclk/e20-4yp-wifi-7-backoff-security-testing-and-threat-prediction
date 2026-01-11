# Report 3: Anomaly Detection Analysis

## 1. Introduction

This report analyzes the characteristics of anomalies within the Wifi7 dataset. An anomaly, in this context, is a deviation from normal system behavior, as exemplified by the data in the `Attack` folder compared to the `Normal` folder.

The statistical analysis from the previous report confirms that anomalies are not subtle; they are clear, significant events that drastically alter the statistical properties of the network metrics.

## 2. Primary Anomaly Indicator: The `bias` Feature

The most direct indicator of an anomaly is the `bias` feature itself.
-   In all normal data, `bias` is **0**.
-   In all attack data, `bias` is a **non-zero** value (e.g., -100, 100, 500, etc.).

While a simple rule-based system could use this feature for perfect classification, the goal of a machine learning model here is likely to learn the *effects* of the bias on the other, more organic network features. This allows the model to potentially identify similar anomalous behavior even if the `bias` feature itself isn't present or is unknown.

## 3. Secondary Indicators: Network Performance Degradation

The attack scenarios create clear anomalies in the form of severe network performance degradation. By comparing the summary statistics of the Normal and Attack samples, we can define anomalies as significant deviations from the normal baseline.

### Key Anomaly Signatures:

1.  **Explosion in Latency and Jitter:**
    -   **Normal Behavior:** Average delay is low (mean ~11 ms) and stable (std dev ~4 ms).
    -   **Anomalous Behavior:** Average delay is extremely high (mean ~318 ms) and erratic (std dev ~88 ms).
    -   **Detection:** A simple threshold (e.g., `net_avg_delay_ms > 100`) would likely be a very effective, if basic, anomaly detector. The same logic applies to `net_avg_jitter_ms`.

2.  **Spike in Packet Loss:**
    -   **Normal Behavior:** Packet loss is present but relatively low and stable (mean ~19%).
    -   **Anomalous Behavior:** Packet loss skyrockets to an average of ~64%.
    -   **Detection:** A window showing a `net_packet_loss_ratio` significantly above the normal mean (e.g., > 0.4) is a strong indicator of an anomaly.

3.  **Drop in Throughput and Backoff Slots:**
    -   **Normal Behavior:** Throughput is high (mean ~412 Mbps) and the average backoff is around 10 slots.
    -   **Anomalous Behavior:** Throughput is nearly halved (mean ~231 Mbps) and the average backoff slots decrease significantly (mean ~3).
    -   **Detection:** This inverse relationship is a more complex but powerful signature of an anomaly. A model can learn that when throughput and backoff slots are both suppressed, it's indicative of the specific attack pattern in this dataset.

## 4. Conclusion

The anomalies in this dataset are well-defined and have a significant, measurable impact on multiple system metrics. The features that are the strongest indicators of anomalous behavior are:

-   `net_avg_delay_ms`
-   `net_packet_loss_ratio`
-   `net_throughput_mbps`
-   `avg_backoff_slots`

The clear statistical separation between normal and attack states suggests that a machine learning model can be trained effectively to distinguish between these behaviors with a high degree of accuracy.
