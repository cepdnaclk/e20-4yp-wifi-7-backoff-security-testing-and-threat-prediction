
[[Glossary Terms]]
# **High-level flow (re-stated, richer)**

Physical/Simulated Wi-Fi 7 fabric → Telemetry & harmonization → Unified Data Repository (UDR/UDM) → **AI workflow** (GNN-based twin + DL/RL security) **and** **Simulation framework** (ns-3/OMNeT++/MATLAB) → NDT **MANO + ZSM** → Actuation on controllers/APs → Closed-loop feedback → Unified dashboard.

1_A Functional Framework for Ne…

---

**1) Data Collection Framework (what to collect, how to normalize, why)**

**What to collect (Wi-Fi 7 / MLO):** per-link RSSI/SNR, EHT MCS & RU maps, puncturing usage, BSS coloring density/OBSS-PD events, channel utilization, per-AC queue stats, retries/FEC, EMLSR/MLO decisions and failovers, DFS/mute windows, deauth/disassoc counters; L2/L3 counters from switches/routers; controller logs.  
**How to transport & harmonize:** exporters/agents → message bus (Kafka/MQTT) → harmonizer that maps vendor/driver counters into a _unified_ “smart data model” (names/units/semantics) before landing in the UDR. The framework must support multi-protocol ingestion, privacy, access policies, and scale across edge→cloud.

1_A Functional Framework for Ne…

  
**Why:** the 6G-TWIN functional framework puts **Data Collection** as a pillar (ingest, harmonize, secure), with explicit FRs for integration, harmonization, and secure/legacy protocol support—this is what enables a **continuous** physical↔virtual mapping instead of one-off imports.

1_A Functional Framework for Ne…

---

**2) Unified Data Repository & Unified Data Model (UDR/UDM)**

**UDR role:** one store for **historical** + **real-time** data (RF, L2/L3, controller logs, and simulated outputs) that the NDT reads/writes to. **UDM role:** the schema/ontology that defines basic models (devices, links, configs, environment) and functional models (traffic analysis, planning, control). This pairing makes “snapshot-to-sim” and “sim-back-to-prod” comparable and auditable.

1_A Functional Framework for Ne…

  
**Why:** the framework explicitly centers a unified repository/model to support real-time mapping (what separates an NDT from mere simulation) and open north/southbound interfaces to apps/physical network.

1_A Functional Framework for Ne…

_Practical note:_ in implementation, split hot time-series (metrics) vs. cold object/history (snapshots, sim outputs). Keep feature stores (windowed aggregates) materialized for ML.

---

**3) Simulation Framework (what-if, data synthesis, fidelity control)**

**Components:**

- **ns-3 (EHT/802.11be):** PHY/MAC fidelity—MLO, channelization, puncturing, beamforming; produce tap/veth interfaces toward the L2/L3 emulated core.
- **OMNeT++:** packet-accurate queueing/scheduling variants (ACs, DRR/WFQ-like QoS), failure propagation, large topology “what-ifs.”
- **MATLAB/analytical PHY:** controlled channel models, antenna/beam experiments, link budgets.  
    **Framework responsibilities (from FRs):** simulator federation, **time management**, parameterization, exception handling, machine-readable model specs, closed-loop protocol to ship configs/results.

1_A Functional Framework for Ne…

  
**Why:** different questions require different fidelity; the framework mandates standardized interfaces, time sync, and simulator interoperability so you can **compose** radio-accurate and queue-accurate views without locking into one tool.

1_A Functional Framework for Ne…

---

**4) AI Workflow: GNN-based digital twin + DL/RL security/automation**

**GNN twin (TwinNet-style):** model the network as **paths–links–queues** with **message passing** and **RNN aggregation** to preserve order dependencies (e.g., which queue drops first). Outputs: per-path delay/loss/jitter under candidate configs and loads. Trained on sim + (optional) real traces.

3_Building a Digital Twin for n…

**Why GNN here:** Wi-Fi 7 + MLO creates graph-structured interactions (APs/clients/links/queues); TwinNet shows **strong generalization** to unseen topologies and **near-real-time** inference compared to packet simulators—ideal for intent loops and what-ifs.

3_Building a Digital Twin for n…

  
**Security analytics (DL):** sequence/graph models for anomaly detection (traffic fingerprints, beacon/probe anomalies, MLO asymmetries, RU starvation, multi-link DoS).  
**Policy selection (RL or hybrid):** state = KPIs + topology snapshot; actions = {channel/RU, OBSS-PD, power, beam, MLO link choice, client steering}; reward = weighted (SLA, threat score, stability). Use **constrained RL** or RL + heuristic/ILP to tame action spaces.

---

**5) Orchestration scaffold with Containerlab (and where VMs fit)**

**What you stand up:** controller, AAA (RADIUS), DHCP/DNS, FRR/SONiC L2/L3, telemetry brokers (Kafka/MQTT), IDS/IPS (Zeek/Suricata), ML services, dashboards—all wired as code in a **YAML topology**. When an image is VM-only (e.g., IOS XR), wrap with **VRnetlab** so it behaves like a container node.

5_CONTAINERLAB ЯК ІНСТУРМЕНТ

**How links work:** Containerlab auto-creates **veth/bridge** peer links for low-latency p2p wiring—perfect to couple ns-3 taps into FRR/SONiC and keep data-plane flows realistic.

5_CONTAINERLAB ЯК ІНСТУРМЕНТ

  
**Why not Docker Compose/only VMs:** Compose can’t express complex **peer-to-peer** topologies and lifecycle at scale; Containerlab was built for this problem and scales better than pure VMs for big labs.

5_CONTAINERLAB ЯК ІНСТУРМЕНТ

**Tiny example (conceptual):**

topology:

  nodes:

    ns3: { kind: linux, image: your/ns3-eht }

    frr: { kind: linux, image: frrouting/frr }

    kafka: { kind: linux, image: bitnami/kafka }

    suricata: { kind: linux, image: jasonish/suricata }

  links:

    - endpoints: ["ns3:eth0","frr:eth1"]

    - endpoints: ["frr:eth2","kafka:eth0"]

    - endpoints: ["frr:eth3","suricata:eth0"]

---

**6) MANO + ZSM + Actuation (how it all runs itself)**

**NDT-MANO:** lifecycle of **NDT instances** (compose models/simulators, deploy, refine), manage data/model repositories, coordinate AI training and simulation, and unify deployment across domains.

1_A Functional Framework for Ne…

  
**ZSM:** closed loops to monitor, optimize, and **apply** changes using standardized APIs; includes **AAA-protected** programmable interfaces and CI/CD for model/config rollouts.

1_A Functional Framework for Ne…

  
**Why:** this is how you move from “dashboards” to **self-optimizing, self-healing** Wi-Fi—automated intents, safe rollouts, quick rollback, and cross-domain scaling.

1_A Functional Framework for Ne…

---

**7) Closed loop + Dashboard (what you see, how it learns)**

Twin as a sandbox (train/validate AI, run what-ifs), then push decisions; telemetry confirms effect; results re-train models—**continuous improvement**. A unified dashboard compares live vs. predicted vs. simulated KPIs and explains the AI’s decision trail.

1_A Functional Framework for Ne…

---

**Why these choices (explicit trade-offs)**

- **GNN twin vs. fluid/analytic:** fluid models are fast but miss queuing/scheduling and path dependencies under MLO + QoS; TwinNet-style GNN retains accuracy and generalizes to new topologies with millisecond inference for “intent loops.”

3_Building a Digital Twin for n…

- **Simulator federation vs. single sim:** PHY/MAC (ns-3/MATLAB) and queueing/scheduling (OMNeT++) solve **different** fidelity problems; the framework requires time sync and standardized interfaces to run them together.

1_A Functional Framework for Ne…

- **Containerlab vs. ad-hoc VMs/Compose:** YAML topologies + p2p wiring + VRnetlab bridge → reproducible, dense, CI-ready labs; Compose can’t express complex p2p; pure VMs limit scale and iteration speed.

5_CONTAINERLAB ЯК ІНСТУРМЕНТ

- **ZSM + MANO vs. manual ops:** mandated by the framework to achieve automation, standardized APIs, and MLOps/CI for multi-instance twins—necessary for resilient threat response.

1_A Functional Framework for Ne…

---

**If you do have a physical fabric**

- Stream controller/AP telemetry into the DC→UDR; mirror traffic to IDS/feature extractors; “snapshot-to-sim” for what-ifs; ZSM pushes guarded changes back (intents + policy caps + rollback).

1_A Functional Framework for Ne…

**If you don’t have a physical fabric (sim-only ramp)**

1. **Backbone:** Containerlab (controllers, AAA, FRR/SONiC, Kafka, IDS, ML, UI).

5_CONTAINERLAB ЯК ІНСТУРМЕНТ

2. **RF:** ns-3 EHT/MLO containers produce taps; wire into FRR to reach services/IDS.
3. **Fidelity add-ons:** OMNeT++ queueing scenarios; MATLAB PHY runs for channel/beam cases.
4. **Data:** exporters → harmonizer → UDR with the same schema as “real.”
5. **Models:** pre-train GNN twin and anomaly detectors on synthetic/augmented sets; cross-scenario validate.
6. **Loop:** stand up MANO/ZSM with simulation-only actuation (no physical push) to exercise intent logic.

1_A Functional Framework for Ne…

5_CONTAINERLAB ЯК ІНСТУРМЕНТ

---

**Concrete design details you can lift into your build**

**A. Telemetry → bus → schema (example)**

**Kafka topics (illustrative):**

- wifi7.rf.perlink: {ap_id, sta_id, band, link_id, snr_db, mcs, ru_size, ru_puncturing, tx_power_dbm, retries, per, ts}
- wifi7.mlo.events: {sta_id, ap_primary, ap_secondary, mlo_state, emlsr_flag, link_failover, cause, ts}
- wifi7.mac.qos: {ap_id, ac, qlen, drops, e2e_delay_p50/p95, ts}
- wifi7.l2l3.ifstats: {node, if, rx/tx_bytes, errors, discards, ts}
- wifi7.security.signals: {ap_id, sta_id?, event, score, src, ts}

**Harmonization:** map vendor counters to UDM fields; store raw + normalized; enforce units; attach provenance.

**B. GNN-twin feature mapping (Wi-Fi 7)**

- **Paths** = STA↔AP (per-MLO-link) + wired path; **Links** = wireless link(s) + L2/L3 hops; **Queues** = per-AC queues + scheduler params.
- **Inputs**: topology, scheduling policy, buffer sizes, traffic matrix, link RF features (SNR/MCS/RU).
- **Outputs**: per-path delay/jitter/loss, hotspot score. Train with MSE; validate on unseen topologies/loads. (Follows TwinNet’s path-link-queue message-passing with RNN aggregation.)

3_Building a Digital Twin for n…

**C. Threat models & mitigations (examples)**

- **Anomalies:** multi-link DoS (imbalance, excessive retries), spoofed deauth bursts, RU starvation, beam mis-steer, rogue AP.
- **Mitigations:** re-pick MLO primary, channel/RU re-plan, adjust OBSS-PD, power/beam tweaks, client steering, temporary isolation; verify impact via twin before ZSM applies.

**D. Guardrails & governance**

- ZSM must enforce AAA, intent scopes, rate-limits, and rollback; tie every actuation to a twin experiment ID and expected KPI envelope. (Matches FRs for ZSM AAA and CI/CD.)

1_A Functional Framework for Ne…

**E. Minimal Containerlab wiring pattern**

- ns-3 container exposes tap0; Containerlab links ns3:eth0 ↔ frr:eth1; FRR advertises routes to Kafka/IDS/DNS; mirror selected flows to Suricata/Zeek; all nodes defined declaratively in YAML. (Low-latency veth/bridge links.)

5_CONTAINERLAB ЯК ІНСТУРМЕНТ

---

**Evaluation & success criteria (security + performance)**

- **Prediction:** per-path delay MAPE vs. simulator/ground truth; jitter error; generalization to unseen layouts (TwinNet-style).

3_Building a Digital Twin for n…

- **Detection:** ROC/AUC for threat detectors; mean time-to-detect (MTTD).
- **Mitigation:** SLA adherence after actuation; % throughput retained under attack; time-to-recover.
- **Ops:** safe-change rate (no rollback), change lead-time, drift alerts, model retraining cadence.

---

**Phased build (actionable)**

1. **Week 0–1:** Containerlab scaffold (controllers, AAA, FRR/SONiC, Kafka, IDS, UI), VRnetlab for any VM-only NOS; CI for clab deploy/destroy.

5_CONTAINERLAB ЯК ІНСТУРМЕНТ

2. **Week 1–2:** ns-3 EHT/MLO hooked to FRR; traffic profiles; baseline KPIs.
3. **Week 2–3:** OMNeT++ queueing scenarios; harmonizer→UDR; define UDM (basic/functional).

1_A Functional Framework for Ne…

4. **Week 3–4:** Train GNN twin on synthetic runs; validate on unseen topologies.

3_Building a Digital Twin for n…

5. **Week 4–5:** DL anomaly models + RL/hybrid mitigations; run scripted attacks; measure end-to-end loop with ZSM (sim-only at first).

1_A Functional Framework for Ne…

6. **Week 5+:** (optional) attach real AP/controller telemetry; enable guarded actuation to prod via intents.

---

If you want, I can draft:

- a first **UDM/UDR schema** (tables & JSON objects for RF/L2/L3/security),
- a **Containerlab YAML** for the scaffold (ns-3 ↔ FRR ↔ Kafka/Suricata),
- and a **TwinNet-style feature spec** (inputs/outputs) tailored to MLO.