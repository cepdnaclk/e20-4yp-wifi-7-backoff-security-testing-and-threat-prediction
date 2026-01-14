## 📘 General Digital-Twin and Network Terms

- **NDT** _(Network Digital Twin)_ — a data-driven, AI-enhanced virtual replica of a communication network that mirrors and predicts the real network’s behavior in near real time.
    
- **MANO** _(Management and Orchestration)_ — software layer that deploys, configures, and manages both network and twin functions, including model lifecycles and cross-domain orchestration.
    
- **F-MANO** _(Federated MANO)_ — distributed MANO architecture for coordinating multiple twin instances across different domains or sites.
    
- **ZSM** _(Zero-Touch Service & Network Management)_ — automation framework enabling the twin or AI to configure and optimize networks without human intervention.
    
- **UDR** _(Unified Data Repository)_ — central data store holding both live and simulated telemetry for analytics, learning, and validation.
    
- **UDM** _(Unified Data Model)_ — schema/ontology defining how devices, links, metrics, and configurations are represented uniformly across physical and virtual systems.
    
- **DC Framework** _(Data Collection Framework)_ — component responsible for collecting, harmonizing, and securing telemetry data from physical or simulated networks.
    
- **Closed Loop Feedback** — mechanism where the twin continuously observes, predicts, tests virtually, and sends optimized configurations back to the physical network.
    
- **Intent-Driven Control Loop** — AI interprets high-level goals (e.g., _minimize latency_) and automatically searches configurations to meet those intents.
    

---

## 🧠 AI / Machine Learning Components

- **AI Workflow Layer** — pipeline that handles data preprocessing, model training, inference, evaluation, and deployment for optimization and threat prediction.
    
- **GNN** _(Graph Neural Network)_ — neural model that learns dependencies across graph-structured systems such as nodes (APs/clients) and links (MLO connections).
    
- **TwinNet** — a GNN-based digital-twin architecture modeling path-link-queue interactions for predicting SLA metrics like delay and jitter.
    
- **DL** _(Deep Learning)_ — multilayer neural networks used here for traffic fingerprinting and anomaly detection.
    
- **RL** _(Reinforcement Learning)_ — agent that learns mitigation or optimization actions by receiving rewards from simulated or real feedback.
    
- **RNN** _(Recurrent Neural Network)_ — sequential model (e.g., GRU/LSTM) embedded inside TwinNet to capture ordered queue dependencies.
    
- **ILP** _(Integer Linear Programming)_ — mathematical optimization method sometimes hybridized with RL to constrain large action spaces.
    
- **FL** _(Federated Learning)_ — decentralized training approach where local nodes train models and share updates (not raw data) to a central aggregator.
    
- **MLOps** _(Machine Learning Operations)_ — lifecycle management for models: versioning, retraining, validation, deployment, and rollback.
    

---

## 📡 Wi-Fi 7 / 802.11be Specific Terms

- **Wi-Fi 7 (EHT)** _(Extremely High Throughput)_ — IEEE 802.11be generation supporting multi-link, 320 MHz channels, and advanced scheduling.
    
- **MLO** _(Multi-Link Operation)_ — simultaneous multi-band connection between an AP and STA, improving throughput and reliability.
    
- **EMLSR** _(Enhanced Multi-Link Single Radio)_ — MLO mode allowing a single radio to time-share multiple links efficiently.
    
- **RU** _(Resource Unit)_ — sub-channel block assigned to users in OFDMA transmissions.
    
- **OFDMA** _(Orthogonal Frequency-Division Multiple Access)_ — multi-user transmission technique dividing spectrum into orthogonal sub-carriers.
    
- **BSS Coloring** — mechanism tagging overlapping BSSs (Basic Service Sets) with colors to mitigate interference.
    
- **OBSS-PD** _(Overlapping BSS Power Detection)_ — threshold control that allows concurrent transmissions from neighboring BSSs if signals are below a limit.
    
- **PHY / MAC** _(Physical / Medium Access Control Layers)_ — radio and data-link layers of the Wi-Fi protocol stack.
    
- **DFS** _(Dynamic Frequency Selection)_ — regulatory function requiring radar avoidance and channel switching.
    
- **SNR / RSSI** _(Signal-to-Noise Ratio / Received Signal Strength Indicator)_ — physical-layer metrics indicating signal quality.
    
- **MCS** _(Modulation and Coding Scheme)_ — defines data rate based on modulation type and coding rate.
    

---

## 🧩 Networking / Simulation Environment

- **ns-3** — discrete-event network simulator with Wi-Fi 7 (EHT) modules for PHY/MAC experiments.
    
- **OMNeT++** — modular packet-level simulator used for queueing, scheduling, and routing studies.
    
- **MATLAB PHY Models** — analytical or simulation models for channel, beamforming, and link-budget evaluation.
    
- **FRR** _(Free Range Routing)_ — open-source routing stack supporting OSPF/BGP; emulates L3 routing in the twin.
    
- **SONiC** _(Software for Open Networking in the Cloud)_ — open network OS for L2/L3 switching and routing emulation.
    
- **VRnetlab** — wrapper that runs VM-based router images (e.g., Cisco, Juniper) as Docker containers for integration.
    
- **Containerlab** — CLI tool defining and deploying container-based network topologies in YAML for reproducible labs.
    
- **veth Pair** _(Virtual Ethernet Pair)_ — Linux kernel mechanism creating a direct virtual link between containers or namespaces.
    
- **Bridge Interface** — virtual switch interconnecting multiple veth pairs.
    
- **YAML Topology** — declarative file describing nodes, images, and links in Containerlab.
    
- **CI/CD** _(Continuous Integration / Continuous Deployment)_ — pipeline for automated twin/lab deployments and model updates.
    
- **AAA** _(Authentication, Authorization, Accounting)_ — network service verifying identity, access rights, and usage; part of ZSM security.
    
- **RADIUS** _(Remote Authentication Dial-In User Service)_ — protocol implementing AAA for Wi-Fi networks.
    
- **DHCP / DNS** _(Dynamic Host Configuration Protocol / Domain Name System)_ — network services for IP assignment and name resolution.
    
- **IDS/IPS** _(Intrusion Detection/Prevention System)_ — security components (e.g., Zeek, Suricata) inspecting traffic for threats.
    
- **Kafka / MQTT** — message brokers used as telemetry buses streaming KPIs to analytics or AI modules.
    

---

## ⚙️ Performance and Evaluation Metrics

- **SLA** _(Service Level Agreement)_ — contractually specified QoS targets (latency, jitter, loss).
    
- **QoS / QoE** _(Quality of Service / Experience)_ — network/service performance indicators experienced by users.
    
- **MAPE** _(Mean Absolute Percentage Error)_ — accuracy metric comparing predicted vs. actual values.
    
- **ROC/AUC** _(Receiver Operating Characteristic / Area Under Curve)_ — evaluation metric for anomaly detection models.
    
- **MTTD** _(Mean Time To Detect)_ — average time a system takes to recognize a fault or attack.
    
- **KPI** _(Key Performance Indicator)_ — measurable value reflecting network health or goal achievement.
    
- **Feature Store** — curated repository of engineered input features for ML models.
    
- **Hot/Cold Data Tiering** — storage approach separating real-time (hot) metrics from archival (cold) data.
    

---

## 🔐 Security and Testing Context

- **DoS/DDoS** _(Denial-of-Service / Distributed DoS)_ — attacks flooding links or devices to degrade service.
    
- **Anomaly Detection** — identifying deviations from normal traffic or RF patterns using DL/GNN models.
    
- **Threat Mitigation Loop** — AI-driven feedback process that detects, simulates, and applies counter-measures automatically.
    
- **Red-Team Traffic Generators** — scripted attack scenarios producing malicious or stress-test traffic.
    
- **Blue-Team Runbooks** — operational defense playbooks for incident response.
    

---

## 🔄 System Integration and Governance

- **P2V** _(Physical-to-Virtual)_ — communication channel linking real devices to their virtual twin counterparts.
    
- **P2P** _(Peer-to-Peer)_ — direct communication among network devices or simulators.
    
- **V2V** _(Virtual-to-Virtual)_ — interactions within virtualized environments for fast, time-compressed experiments.
    
- **Edge / Cloud / Fog Computing** — hierarchical computing placements balancing latency, scale, and bandwidth.
    
- **DRL** _(Deep Reinforcement Learning)_ — combination of deep nets and RL for complex decision spaces.
    
- **Blockchain Integration** — optional tamper-evidence layer for federated learning or config auditing.
    
- **Snapshot-to-Sim / Sim-to-Prod** — exporting a live network state into simulation or replaying simulation results back to production.