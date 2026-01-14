# 1) What the paper is (in one minute)

This is a 2024 systematic literature review (SLR) on Network Digital Twins (NDTs), synthesizing 138 primary studies across 2017–2024. It charts where NDTs are used (domains), how they’re built (architectures, deployments), and what methods they rely on (AI/ML, optimization, etc.). The headline for you: NDTs are most often used to optimize network performance; security is a substantial but smaller slice, and most systems deploy at the edge or across the edge–cloud continuum—exactly the shape of your planned lab.

> “From the analysis of **138** primary studies, various insights emerge.”  
> “Networking Digital Twin is a **particularly recent** concept… explored… since **2017**.”  
> “The vast majority of the studies propose solutions to **optimize network performance**, but there are also many oriented towards **security**…”

# 2) Method (why you can trust the trends)

The authors followed Kitchenham SLR guidelines, ran a broad Google Scholar search, applied clear inclusion/exclusion criteria, and then did forward- and backward-snowballing to reach 138 studies. They report inter-rater agreement and share a replication package. For your dissertation’s Related Work, this is a credible umbrella source.

# 3) Key findings you can reuse (mapped to your build)

## 3.1 Research activity landscape

- **Growth & venues.** NDT work grows from 2017 and peaks around 2022–2024; journals dominate over conferences. For lit cites in your thesis, this helps justify _why now_.
    
- **Research strategies.** Simulation and _experimental simulation_ are most common; there are also lab/field experiments and some formal methods. That fits your **ns-3** plan (simulation) and **Containerlab** (experimental emulation).
    

> “The vast majority of studies utilize **computing simulations**… Experimental simulations… are the second most popular.”

- **Core quality goals.** Performance efficiency leads; security and functional suitability follow. That means your KPIs should include **latency, throughput, reliability** first, with **attack detection**/**mitigation quality** layered on.
    

## 3.2 Application context

- **Top domains.** Smart industry, edge computing, and vehicular dominate. Even though Wi-Fi 7 is under-represented, your **edge-heavy** architecture aligns with the mainstream NDT shape.
    
- **Communication tech.** Most papers don’t fix one tech; among those that do, **Beyond-5G/6G** dominates. Critically, they note:
    
    > “There is just a **single entry** for **Bluetooth** and **Wi-Fi** communication technologies…”  
    > That’s your research gap: a Wi-Fi 7-focused NDT for **security/threat prediction** is novel and publishable.
    
- **Assets.** NDTs model **physical** (e.g., radios, links) and **logical** assets (e.g., VNFs (Virtual Network Functions), slices). Your plan to combine **ns-3 radios** (physical) and **Containerlab services** (logical) follows the paper’s “phygital” direction.
    

## 3.3 Properties of NDTs (design choices)

- **AI-enabled (57.4%).** Over half of NDTs use AI, often **DRL (Deep Reinforcement Learning)**, **GNNs (Graph Neural Networks)**, or **Federated Learning**. Your **PyTorch/TensorFlow** layer is on-trend.
    
- **Deployment: edge > cloud; many mixed.** Low-latency functions at the **edge**, heavy analytics in the **cloud** (“Edge,Cloud” mixed). That maps to **Kubernetes** with **node pools/labels** and to your **Kafka/InfluxDB** pipeline.
    

> “The majority of papers consider DT deployed at the **edge**… **hybrid** solutions involving both **edge and cloud** are common…”

- **Architectural descriptions (~49%).** Almost half provide explicit **architecture diagrams**. Do the same: a multi-tier diagram showing **NetBox → ns-3 → Telemetry → Store → Graph/ML → Actuation** will align with best practice.
    
- **Centralized vs distributed.** There are **centralized** twins (a single global NDT) and **distributed** ones (many twins collaborating), plus **mixed** (e.g., A3C agents at edge, global coordination). Your Wi-Fi 7 MLO (Multi-Link Operation) use-case benefits from **distributed twins** per AP/Link, with a **central coordinator** for predictions.
    
- **Auxiliary tech.** SDN/NFV, blockchain (for trust), and **Markovian models / MDPs** show up often; GNNs and DRL are frequent in optimization/slicing. Your **Neo4j/NetworkX** graph + **GNN classifier** for threat propagation is well-supported.
    

# 4) Short quotes you can drop into your thesis

- “Digital twins… replicate the **structure and behavior** of the physical network.”
    
- “AI… plays a **fundamental role** in the field of NDTs.”
    
- “Edge nodes have typically **limited resources**… this may affect performance.”
    
- “A **hierarchical** digital twin… digital representations… at various levels of granularity.” (rare but promising)
    


    

# 7) Mini-glossary (quick acronym decodes)

- **DT** (Digital Twin): high-fidelity virtual model of a physical/logical system that stays in sync with it.
    
- **NDT** (Network Digital Twin): a DT specialized for networks.
    
- **QoS** (Quality of Service): performance guarantees like bandwidth/latency.
    
- **URLLC** (Ultra-Reliable Low-Latency Communications): stringent latency/reliability class.
    
- **SDN** (Software-Defined Networking): control plane separated from data plane.
    
- **NFV** (Network Function Virtualization): network functions as software on commodity hardware.
    
- **MEC** (Mobile Edge Computing): compute close to users for low latency.
    
- **MLO** (Multi-Link Operation, Wi-Fi 7): client/AP use multiple links concurrently.
    
- **DRL** (Deep Reinforcement Learning): learning via rewards to choose actions.
    
- **GNN** (Graph Neural Network): neural nets over graphs.
    
- **MDP** (Markov Decision Process): mathematical model for sequential decisions.
    
- **V2X/V2V** (Vehicle-to-Everything / Vehicle-to-Vehicle): comms paradigms.
    

# 8) A concrete “first milestone” plan (2 weeks of lab work)

- **Day 1–2:** Model APs/clients/MLO links in **NetBox**; export topology JSON.
    
- **Day 3–5:** Build **ns-3 802.11be** scenario that reads the NetBox JSON; emit per-interval metrics to **Kafka**.
    
- **Day 6–7:** Stand up **Containerlab** services (AAA/DHCP) and link to ns-3 flows.
    
- **Day 8–9:** Pipe Kafka → **InfluxDB**; Grafana dashboard for throughput, retry, per-link MLO stats.
    
- **Day 10–11:** Build **Neo4j** graph from telemetry; prototype **GNN** or simple anomaly detector (PyTorch).
    
- **Day 12–14:** Add one attack (MLO link jam); train classifier; implement a **controller action** to re-route clients.
    

# 9) Limitations/positioning (useful for your write-up)

The SLR shows Wi-Fi studies are rare (only one explicit Wi-Fi paper). That’s a **gap** and your contribution. Also, NDT security is present but smaller than performance—your work pushes security forward within an NDT, aligning with trends the SLR highlights.