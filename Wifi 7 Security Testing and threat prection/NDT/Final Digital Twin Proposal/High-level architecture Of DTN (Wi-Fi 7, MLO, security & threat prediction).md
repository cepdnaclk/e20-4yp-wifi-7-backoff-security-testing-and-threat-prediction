
# High-level architecture (Wi-Fi 7, MLO, security & threat prediction)

**Flow:** Physical/Simulated Wi-Fi 7 fabric → Telemetry & harmonization → Unified Data Repository → (A) AI workflow (DL/RL & GNN-based twin) + (B) Simulation framework (ns-3/OMNeT++/MATLAB) → NDT MANO + ZSM → Actuation on controllers/APs → Closed-loop feedback → Operator dashboard.

1_A Functional Framework for Ne…

**Key components**

- **Data Collection Framework (DC):**  
    Collect Wi-Fi 7/MLO telemetry (RSSI/SNR, per-link PER, RU usage, puncturing, OBSS/BSS coloring, channel utilization, contention/collision counters, EMLSR/MMLO events, deauth/disassoc counts). Harmonize into a _smart data model_ and stream to the twin. (Think: exporters → bus → schema → repo.)
    
    1_A Functional Framework for Ne…
    
- **Unified Data Repository (UDR):**  
    One store for live + synthetic (simulated) RF/network data. Serves training, inference, and validation; supports “snapshot to sim” and “sim back to prod” comparisons.
    
    1_A Functional Framework for Ne…
    
- **AI Workflow Layer:**
    
    - **Predictive models:** GNN-based digital-twin model (TwinNet-style) to infer per-flow/queue/link latency/loss/jitter under varying routing/scheduling and RF load.
        
    - **Security analytics:** DL for anomaly detection/traffic fingerprinting; RL for mitigation policy selection (e.g., MLO link steering, channel/RU re-plans, power/beam tweaks).
        
    - **MLOps:** retraining/versioning/rollbacks, edge/cloud split for low-latency inference.
        
        3_Building a Digital Twin for n…
        
        1_A Functional Framework for Ne…
        
- **Simulation Framework (what-if + data generation):**  
    ns-3 (EHT/802.11be PHY/MAC), OMNeT++ for packet-accurate scenarios, MATLAB/analytical PHY models where needed. Used to: (1) replay incidents, (2) synthesize rare attacks (multi-link DoS, jamming, spoofed control), (3) pre-train models.
    
    1_A Functional Framework for Ne…
    
    3_Building a Digital Twin for n…
    
- **NDT MANO + ZSM (automation):**  
    NDT MANO handles lifecycle of twin instances, mapping scenarios to models/simulators and managing CI/CD + MLOps; ZSM closes the loop, pushing safe, automated config changes to controllers/APs (zero-touch).
    
    1_A Functional Framework for Ne…
    
- **Orchestration scaffold (Containerlab):**  
    Use Containerlab to stand up the non-RF backbone of the twin: WLAN controllers, AAA (RADIUS), DHCP/DNS, L3/L2 (FRR/SONiC), telemetry buses (Kafka/MQTT), IDS/IPS (Zeek/Suricata), ML services—wired together from a YAML topology. Wrap VM-only NOS images via VRnetlab when needed.
    
    5_CONTAINERLAB ЯК ІНСТУРМЕНТ
    
- **Closed-loop feedback & dashboard:**  
    Twin monitors, predicts, tests in sim, then actuates; results are measured and fed back to refine models. A unified UI shows live KPIs, what-if outputs, and AI explanations.
    
    1_A Functional Framework for Ne…
    

---

# Why these design choices (and not the alternatives)

- **GNN-based twin vs. classic NN or fluid/analytic models**  
    Wi-Fi 7 + MLO is graph-structured (APs/links/queues/clients); GNNs learn path↔link↔queue dependencies and generalize to unseen topologies. Fluid/analytic models are fast but miss queuing/scheduling dynamics under load; TwinNet-style GNNs achieved low error and strong generalization in benchmarking, enabling near-real-time optimization and what-if planning.
    
    3_Building a Digital Twin for n…
    
- **Unified DC + harmonization + UDR vs. siloed collectors**  
    A single harmonized model across vendors/layers reduces integration debt and is required for persistent+on-demand twin views and safe sim-to-prod transitions. This is a core NDT requirement set (performance, security, interoperability).
    
    1_A Functional Framework for Ne…
    
- **ZSM closed-loop + F-MANO/MLOps vs. manual ops**  
    Automated lifecycle and standardized APIs let you scale multiple twin instances, keep models current, and enact mitigations quickly and safely—critical for live threat response and dynamic MLO steering.
    
    1_A Functional Framework for Ne…
    
- **Containerlab-first scaffold vs. ad-hoc VMs or Compose**  
    You get reproducible topologies as code, dense scale on a single host, peer-to-peer wiring, and smooth CI/CD; VRnetlab bridges VM-only images. This reduces cost and accelerates iteration for both networking and security drills.
    
    5_CONTAINERLAB ЯК ІНСТУРМЕНТ
    
- **Simulator federation (ns-3/OMNeT++/MATLAB) vs. single tool**  
    Different questions need different fidelity: PHY/MAC RF behavior (ns-3/MATLAB) vs. packet-accurate queueing and scheduling (OMNeT++). The functional framework explicitly calls for a simulator framework with model catalogs, time management, and standardized interfaces.
    
    1_A Functional Framework for Ne…
    

---

# Building with or without a physical system

**If you have real APs/clients/controllers (preferred):**

- Tap controller/AP telemetry; mirror traffic to IDS/feature extractors; stream to UDR.
    
- “Snapshot-to-sim”: export current state into the sim framework for safe what-if testing; apply ZSM actions back to the WLAN controller under guardrails (intents and caps).
    
    1_A Functional Framework for Ne…
    

**If you don’t have physical gear (simulation-only ramp):**

- Use **Containerlab** to bootstrap the control/data-plane backbone (controllers, AAA, FRR/SONiC, telemetry bus).
    
- Run **ns-3** EHT modules in containers to emulate Wi-Fi 7 air-interface and MLO; wire ns-3 veth/tap into FRR/SONiC so packets traverse a realistic L2/L3 under policy.
    
- Add **OMNeT++** scenarios for queueing/scheduling fidelity and **MATLAB** PHY models for channel/beam/ puncturing experiments.
    
- Generate synthetic incident datasets (multi-link DoS, coordinated jamming, deauth storms, RU starvation).
    
- Train the **GNN twin** and anomaly detectors on the synthetic+augmented data; validate via cross-scenario generalization before any on-prem trials.
    
    5_CONTAINERLAB ЯК ІНСТУРМЕНТ
    
    3_Building a Digital Twin for n…
    
    1_A Functional Framework for Ne…
    

---

# What to predict, detect, and act on (MLO-centric)

- **Telemetry features (examples):** per-link SNR/RSSI, PHY/MAC counters, RU maps and puncturing rate, BSS color density, per-AC queue stats, MLO link asymmetry, FEC retries, beacon/probe anomalies, deauth/disassoc rates, DFS events. (Feeds DC→UDR.)
    
    1_A Functional Framework for Ne…
    
- **Twin tasks:**
    
    - QoS KPI inference per flow/path/queue under proposed configs (GNN twin).
        
    - Threat scoring (anomaly detection on time-series/RF+net features).
        
    - Policy search: RL or hybrid (RL + constrained search) for mitigations—channel/RU/multi-link selection, power/beam, client steering, per-AC scheduling.
        
        3_Building a Digital Twin for n…
        
        1_A Functional Framework for Ne…
        
- **Actuation (ZSM):** push safe configs to controllers/APs; enforce rate-limit/isolation/steering; update MLO policy; rotate keys if needed; confirm efficacy in closed loop.
    
    1_A Functional Framework for Ne…
    

---

# Minimal phased plan (actionable)

1. **Scaffold (2–3 days):** Containerlab YAML with: FRR/SONiC, AAA, DHCP/DNS, Kafka/MQTT, IDS, ML-svc, dashboard. Add VRnetlab nodes if required NOS is VM-only.
    
    5_CONTAINERLAB ЯК ІНСТУРМЕНТ
    
2. **Simulate RF (week 1):** ns-3 Wi-Fi 7 EHT + MLO, wired into FRR; create traffic profiles + baseline KPIs; add OMNeT++ queueing scenarios for scheduler variants.
    
    3_Building a Digital Twin for n…
    
3. **Data layer (week 1):** Telemetry exporters → harmonization → UDR; define schemas for RF + L2/L3 + security events.
    
    1_A Functional Framework for Ne…
    
4. **Twin v1 (week 2):** Train GNN twin for delay/loss/jitter on sim data; validate generalization across topologies/loads.
    
    3_Building a Digital Twin for n…
    
5. **Security loop (week 2):** Train anomaly detector; script attack what-ifs (multi-link DoS, deauth, RU starvation/jamming); evaluate mitigations via RL/hybrid search.
    
    1_A Functional Framework for Ne…
    
6. **Closed loop (ongoing):** Stand up NDT MANO + ZSM intents; gate actuation with safety constraints; add dashboard cards (live vs. predicted vs. what-if).
    
    1_A Functional Framework for Ne…
    

---

## Sources you’re building on

- Functional NDT framework (Data Collection, UDR, Simulation Framework, AI workflows, NDT-MANO, ZSM, closed loops).
    
    1_A Functional Framework for Ne…
    
- GNN-based digital twin (TwinNet): path-link-queue message-passing, strong generalization, and speed vs. packet-level sims—enables real-time optimization/what-if.
    
    3_Building a Digital Twin for n…
    
- Containerlab as the reproducible, CI-friendly networking lab substrate (YAML topologies, veth/bridges, VRnetlab for VM images).
    
    5_CONTAINERLAB ЯК ІНСТУРМЕНТ