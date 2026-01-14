# Guide to Modeling Backoff Manipulation in Wi-Fi 7 with ns-3

This guide provides a walkthrough of how to model and analyze the impact of backoff manipulation on Wi-Fi 7 MLO networks using ns-3, based on the methodology developed in this project.

## 1. Setting up the Simulation Environment

The first step is to set up a basic ns-3 simulation with a Wi-Fi 7 MLO network. The scripts in the `scratch/` directory of this project provide an excellent starting point.

### Key Components:
-   **Nodes:** Create a set of APs and STAs using `NodeContainer`.
-   **PHY and Channel:** Use `SpectrumWifiPhyHelper` to create a multi-band channel (e.g., 5 GHz and 6 GHz for MLO).
-   **Wi-Fi Standard:** Set the Wi-Fi standard to 802.11be using `WifiHelper::SetStandard(WIFI_STANDARD_80211be)`.
-   **MAC Layer:** Use `WifiMacHelper` to set the MAC layer type to `ns3::ApWifiMac` and `ns3::StaWifiMac` and configure the SSID for MLO.
-   **Mobility:** Although this project uses a static grid layout, you can use any of ns-3's mobility models to simulate different spatial arrangements of nodes.
-   **Internet Stack and IP Addressing:** Install the internet stack on all nodes and assign IP addresses using `InternetStackHelper` and `Ipv4AddressHelper`.

## 2. Implementing the Backoff Manipulation

The core of the experiment is the ability to modify the backoff parameters of the nodes. This is done by directly accessing and modifying the `MinCw` of the `QosTxop` for the desired access category.

The `ApplyAttack` function from this project provides a clean and effective way to do this:
```cpp
void ApplyAttack(NetDeviceContainer& devs, int bias, uint32_t minCw) {
    for (uint32_t i = 0; i < devs.GetN(); ++i) {
        Ptr<WifiNetDevice> dev = DynamicCast<WifiNetDevice>(devs.Get(i));
        if (!dev) continue;
        Ptr<WifiMac> mac = dev->GetMac();
        PointerValue ptr;
        
        uint32_t newCw;
        if (bias < 0) {
            uint32_t absBias = (uint32_t)(-bias);
            if (absBias >= minCw) newCw = 0;
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
To use this, you will need to:
1.  Add this function to your simulation script.
2.  Add a `bias` parameter to your command-line arguments.
3.  Call this function after you have installed the Wi-Fi devices, passing the `NetDeviceContainer` of the nodes you want to affect and the desired `bias`.

## 3. Comprehensive Data Collection

To get a deep understanding of the impact of your backoff manipulation, it is essential to collect a wide range of KPIs. The `Tracer` struct from this project is an excellent template.

### Key Steps:
1.  **Create a `Tracer` struct:** This struct should contain member variables to store the collected statistics (e.g., tx/rx counters, drop counters, backoff sums).
2.  **Implement callbacks:** Create methods within your `Tracer` struct to handle the data from the trace sources. These methods will be called by ns-3 whenever the corresponding event occurs.
3.  **Connect to trace sources:** In your `main` function, connect the `Tracer`'s callbacks to the desired trace sources using `Config::ConnectFailSafe`. Refer to the `kpi_collection_methodology.md` file for a list of useful trace sources.
4.  **Use `FlowMonitor`:** Install `FlowMonitor` to collect network-level statistics like throughput, delay, and jitter.
5.  **Periodically dump data:** Use `Simulator::Schedule` to call a `Dump` function periodically. This function should process the collected data from your `Tracer` and `FlowMonitor` and write it to a file (e.g., in JSON format).

## 4. Running the simulations and analyzing the results

Once your simulation script is set up, you can run it with different `bias` values to generate your dataset.

### Example Workflow:
1.  **Run with `bias = 0`:** This will give you a baseline performance measurement.
2.  **Run with positive `bias` values:** This will simulate less aggressive nodes.
3.  **Run with negative `bias` values:** This will simulate more aggressive nodes (the "attack" scenario).

After running the simulations, you will have a set of JSON files containing the time-series data for your KPIs. You can then use your favorite data analysis tools (e.g., Python with pandas, R, MATLAB) to parse this data, plot the results, and draw conclusions about the impact of backoff manipulation on your Wi-Fi 7 MLO network.

By following this guide and using the scripts from this project as a starting point, you can conduct your own sophisticated and detailed analysis of Wi-Fi 7 performance in ns-3.
