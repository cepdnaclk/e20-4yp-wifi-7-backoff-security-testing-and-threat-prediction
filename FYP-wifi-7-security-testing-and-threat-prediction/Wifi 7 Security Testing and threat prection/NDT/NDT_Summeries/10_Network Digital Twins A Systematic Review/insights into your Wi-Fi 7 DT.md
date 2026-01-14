# 5) Turning the paper’s insights into your Wi-Fi 7 threat-prediction NDT (step-by-step)

Below is a practical blueprint that mirrors the paper’s recommendations while matching your exact toolchain.

## 5.1 System architecture (what to build)

1. **Inventory & intent (NetBox).**
    
    - Model SSIDs, APs, radios, channels, MLO links, BSS coloring, client roles. Treat these as **physical assets** plus **logical services** (RADIUS, DHCP, DNS).
        
2. **Radio/network behavior (ns-3 – 802.11be Wi-Fi 7).**
    
    - Simulate normal and adversarial behaviors: **MLO link flapping**, **EHT (Extremely High Throughput) 320 MHz contention)**, **BSS Color spoofing**, **RTS/CTS abuse**, **jamming**, **spoofed association/auth frames**, **QoS flooding**. The SLR shows security papers exist but are fewer—lean into that gap.
        
3. **Network services (Containerlab).**
    
    - Spin up emulated services (AAA, controllers, telemetry brokers). This is your **logical twin** layer, complementing the **physical** ns-3 radios.
        
4. **Telemetry plane (Kafka/MQTT).**
    
    - Stream **PHY/MAC counters** (RSSI, PER, retries, airtime), **MAC state**, **MLO per-link stats**, **EAPOL timing**, **AP CPU/mem**, **flow metadata**. The paper emphasizes performance + edge constraints, so keep messages lean to avoid bottlenecks.
        
5. **Time-series store (InfluxDB/Prometheus).**
    
    - Persist metrics; label with **scenario/attack type** to support supervised and RL training, reflecting the paper’s performance-first angle.
        
6. **Graph twin (NetworkX/Neo4j).**
    
    - Build a **network graph**: nodes = AP radios, MLO links, clients, services; edges = associations, backhaul, interference. This enables **GNN-based** detection (common in NDT optimizations).
        
7. **AI layer (PyTorch/TensorFlow).**
    
    - **Supervised**: classify attack types from labeled telemetry.
        
    - **Unsupervised**: detect anomalies (autoencoders) when telemetry deviates.
        
    - **DRL**: learn **mitigations** (e.g., re-assign MLO links, adjust channel widths, move clients) — DRL is frequently used in NDT for resource allocation/offloading.
        
8. **Orchestration (Kubernetes).**
    
    - Edge pool runs **ns-3 + brokers + lightweight inference**; cloud pool runs **training + heavy analytics**. This **edge–cloud mixed** deployment mirrors the most common pattern in the SLR. Use **nodeSelectors/taints** to separate tiers.
        
9. **Visualization & control (Grafana/D3).**
    
    - Dashboards for performance and **attack timelines**; a **graph view** for MLO link health; and **“what-if”** controls to run counterfactuals (e.g., “what if I disable Link-2 of MLO for this station?”).
        
10. **Closed loop (policy).**
    

- Turn predictions into actions via a **controller**: adjust **channel/MLO**, **BSS color**, **tx power**, **allocation**, or **rate-limit** suspicious flows. The paper notes centralized, distributed, or mixed control; start **distributed per-AP twin** with a **central policy hub**.
    

## 5.2 Example threat experiments (ready-to-run ideas)

- **MLO DoS**: In ns-3, periodically jam one MLO link; measure **failover latency** and **throughput** on the other link. Kafka → InfluxDB; train a **binary classifier** to flag MLO-targeted DoS within **N** ms.
    
- **BSS Color spoof**: Inject frames with forged color to trigger hidden-node style contention; detect **retry spikes** + **airtime skew**, classify as spoof vs congestion using a **graph-temporal model** (GNN + LSTM).
    
- **EAPOL delay attack**: Add jitter to auth exchanges; predict **auth failure cascade** and trigger **load-balancing** to other AP radios via the controller.  
    These align with the paper’s emphasis on **performance + security** and with **simulation/experimental** methodologies common in NDT research.
    

## 5.3 Why this design matches the SLR

- **Edge-first + cloud assist** → majority pattern in NDTs.
    
- **AI throughout** (classification, anomaly detection, DRL) → used in 57.4% of papers.
    
- **Explicit architecture** → half of papers do it; include yours in the thesis.
    
- **Distributed twins** per AP/link + central coordinator → mirrors mixed deployment paradigms in the survey.
    

# 6) What to learn/borrow (a checklist)

- **Define assets as physical + logical** (radios + services).
    
- **Adopt a mixed edge–cloud** deployment from day one.
    
- **Use graphs** to model network state; consider **GNNs** for prediction/optimization.
    
- **Prefer simulation/experimental-simulation** to iterate quickly (ns-3 + Containerlab).
    
- **Bake in performance KPIs** alongside security metrics.
    
- **Design for hierarchical views** (AP → Site → Global), even if you start flat.