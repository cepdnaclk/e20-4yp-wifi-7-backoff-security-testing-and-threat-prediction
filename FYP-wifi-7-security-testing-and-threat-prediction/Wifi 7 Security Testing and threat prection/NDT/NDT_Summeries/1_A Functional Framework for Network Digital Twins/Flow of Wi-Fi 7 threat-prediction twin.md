[[Improved Flow of Wi-Fi 7 threat-prediction twin]]


## Putting it all together for a Wi-Fi 7 threat-prediction twin

**Minimal lab (no physical APs yet):**

- **NetBox**: define AP inventory, rooms/floors, channels, Tx limits.
    
- **ns-3**: simulate Wi-Fi 7 links (MLO, puncturing), mobility, walls, and **attacks** (deauth, flood, jamming). Export KPIs (RSSI, SNR, errors, retrans, delay, throughput). (Matches the paper’s simulator set.)
    
- **Containerlab**: emulate L2/L3 services (AAA, controllers, SIEM/IDS, firewalls), plus message buses (**Kafka/MQTT**) to carry telemetry.
    
- **Data pipeline**: Kafka/Telegraf → time-series DB (InfluxDB/Prometheus) → **UDR**.
    
- **AI**: notebooks/pipelines to train **DL** anomaly models and **RL** defense agents using sim data, saved to **model repo**. (Paper: DL/RL training & storage.)
    
- **MANO/Orchestrator**: a controller service that reads model outputs and **applies** mitigations (channel/power/MLO policies) to the simulated network; later, to real APs.