# Report 2: Summary Statistics

## 1. Introduction

This report provides a comparative statistical summary of a sample "Normal" dataset and a sample "Attack" dataset. The goal is to quantify the differences in data distribution between the two classes and identify which features are most affected by the attack scenario.

-   **Normal Sample:** `session_1_scenario_1_normal_run_1.json`
-   **Attack Sample:** `session_1_scenario_1_negative_bias_100_run_3.json`

*Note: Statistics are based on the raw values within each time window.*

---

## 2. Statistics for Normal Scenario

```
             window     bias  net_throughput_mbps  net_avg_delay_ms  net_avg_jitter_ms  net_packet_loss_ratio  net_active_flows  avg_backoff_slots  channel_busy_ratio
count  14000.000000  14000.0         14000.000000      14000.000000       14000.000000           14000.000000      14000.000000       14000.000000        14000.000000
mean    6999.500000      0.0           411.705951         10.652535           0.212352               0.187046          5.993214           9.960813            0.878944
std     4041.596219      0.0            27.667147          4.259161           0.257379               0.050333          0.173696           3.872754            0.027475
min        0.000000      0.0             0.000000          0.000000           0.000000               0.000000          0.000000           0.000000            0.003568
25%     3499.750000      0.0           397.319000          8.494865           0.184082               0.152835          6.000000           9.299765            0.873389
50%     6999.500000      0.0           413.731000          9.769935           0.194690               0.182532          6.000000           9.712775            0.881693
75%    10499.250000      0.0           428.795000         11.496000           0.209293               0.214944          6.000000          10.179125            0.888461
max    13999.000000      0.0           501.846000         85.297800          16.031300               0.650102          6.000000         195.521000            0.917879
```

## 3. Statistics for Attack Scenario (Bias: -100)

```
            window    bias  net_throughput_mbps  net_avg_delay_ms  net_avg_jitter_ms  net_packet_loss_ratio  net_active_flows  avg_backoff_slots  channel_busy_ratio
count   1000.000000  1000.0          1000.000000       1000.000000        1000.000000            1000.000000       1000.000000        1000.000000         1000.000000
mean     499.500000  -100.0           230.966084        318.003928           5.141676               0.641332          4.134000           3.030961            0.902162
std      288.819436     0.0            93.269325         88.531692          11.308658               0.110989          0.935371           3.152872            0.091807
min        0.000000  -100.0             0.000000          0.000000           0.000000               0.000000          0.000000           0.000000            0.003568
25%      249.750000  -100.0           173.201000        266.048750           0.309376               0.577917          4.000000           1.768047            0.904430
50%      499.500000  -100.0           211.662500        329.185000           0.641412               0.661888          4.000000           2.233135            0.913993
75%      749.250000  -100.0           259.486000        375.578750           2.964305               0.716308          5.000000           2.920890            0.919319
max      999.000000  -100.0           684.052000        549.616000          91.445600               0.833333          6.000000          29.508700            0.946278
```
*Note: The `mac_` and `phy_` features are all zero in these samples and are excluded from the formatted tables for brevity.*

## 4. Comparative Analysis

The statistical summaries reveal a dramatic difference between the Normal and Attack scenarios:

-   **Network Throughput:** The mean throughput drops significantly during an attack (from ~412 Mbps to ~231 Mbps). The standard deviation is also much higher, indicating more erratic performance.
-   **Average Delay:** This is the most striking indicator. The mean delay explodes from **~11 ms** in the normal state to **~318 ms** under attack. This is a 30x increase, making it a powerful feature for detection.
-   **Average Jitter:** Jitter also sees a massive increase, from a mean of ~0.21 ms to ~5.14 ms. The maximum value and standard deviation are also drastically higher.
-   **Packet Loss:** The mean packet loss ratio jumps from ~18% to ~64%, clearly indicating severe network degradation.
-   **Average Backoff Slots:** This value is significantly lower on average during the attack (~3.0 vs. ~10.0). This is a counter-intuitive but interesting signature, suggesting the attack alters the fundamental channel access behavior.
-   **Channel Busy Ratio:** The channel is slightly busier on average during the attack, but the difference is less pronounced than in other metrics.

In conclusion, the attack has a clear and quantifiable impact on nearly all network performance metrics. The distributions of these metrics are fundamentally different between the two classes, making this an excellent dataset for a classification model.
