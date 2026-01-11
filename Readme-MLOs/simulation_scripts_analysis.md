# Analysis of Simulation Scripts

The core of this project's experimentation lies in the set of C++ simulation scripts located in the `scratch/` directory. These scripts are responsible for setting up the Wi-Fi 7 MLO network, running the simulation with different parameters, and collecting the resulting data. The primary scripts are `wifi7-mlo-Normal.cc`, `wifi7-mlo-Negative.cc`, and `wifi7-mlo-Positive.cc`.

## Commonalities

All the simulation scripts share a common structure:
1.  **Network Setup:** They create a number of APs and STAs, and configure them to use Wi-Fi 7 (802.11be) with MLO. The MLO setup uses two links, one on the 5 GHz band and one on the 6 GHz band.
2.  **Traffic Generation:** A full mesh of UDP traffic is generated between all nodes in the network using `OnOffHelper`. This ensures that there is consistent channel contention, which is essential for studying the backoff mechanism.
3.  **Data Collection:** A `Tracer` struct is implemented to collect a wide range of KPIs. This struct uses a combination of `FlowMonitor` and various MAC/PHY layer trace sources to gather data. The data is dumped periodically to a JSON file.
4.  **Parameterization:** The scripts can be configured via the command line to change parameters such as the number of stations, simulation time, and the `bias` value.

## Scenario-Specific Scripts

The different `wifi7-mlo-*.cc` scripts are used to run the different simulation scenarios by modifying the backoff behavior of the nodes.

### `wifi7-mlo-Normal.cc`

This script represents the baseline scenario. It is intended to be run with a `bias` of 0. In this case, the `ApplyAttack` function is called, but since the bias is zero, the `minCw` is not changed from its default value. This provides a performance baseline against which the other scenarios can be compared.

### `wifi7-mlo-Positive.cc`

This script is used to simulate a scenario where nodes are less aggressive in their channel contention. It is intended to be run with a positive `bias` value (e.g., `+5000`). The `ApplyAttack` function adds this positive bias to the default `minCw`, resulting in a larger contention window. This increased backoff time should lead to fewer collisions, but might also underutilize the channel, potentially decreasing overall throughput.

### `wifi7-mlo-Negative.cc`

This script simulates a scenario where nodes are more aggressive. It is intended to be run with a negative `bias` value (e.g., `-5000`). The `ApplyAttack` function subtracts the bias from the `minCw`, making the contention window smaller. This can be interpreted as a simulation of a backoff manipulation attack, where a malicious node tries to gain an unfair share of the channel resources. This is expected to increase collisions and significantly degrade network performance for well-behaved nodes.

A key feature in the latest version of the code is the "FIXED NEGATIVE BIAS LOGIC" in the `ApplyAttack` function. This logic prevents integer underflow when a large negative bias is applied, ensuring that the contention window is clamped to 0 instead of wrapping around to a very large number. This is a critical correction for accurately simulating this attack scenario.

## The `ApplyAttack` Function

The `ApplyAttack` function is the key component that enables the backoff manipulation:

```cpp
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
```

This function iterates through all the network devices and modifies the `MinCw` of the Best Effort (`BE`) access category's `QosTxop`. By modifying this parameter, the script directly influences the backoff behavior of the nodes, allowing for the study of its impact on the network's performance.
