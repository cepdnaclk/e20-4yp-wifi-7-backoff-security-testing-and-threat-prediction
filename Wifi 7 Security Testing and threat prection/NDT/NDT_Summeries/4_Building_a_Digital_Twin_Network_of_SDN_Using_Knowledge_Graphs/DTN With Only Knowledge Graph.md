# How to build your Wi-Fi 7 threat-prediction twin (step-by-step, no physical network)

Below is a **direct adaptation** of the paper’s approach to a Wi-Fi 7 context. Where the paper says “SDN controller,” read it as your **simulator/telemetry source**. You will:

## 1) Choose your data source (simulator/emulator/logs)

- Use a **wireless simulator/emulator** to produce realistic state and events for Wi-Fi 7 features: **MLO** (multi-link operation), **OFDMA** (orthogonal frequency-division multiple access), **4K-QAM** (high-order modulation), **preamble puncturing**, **punctured resource units**, **channel widths** (e.g., 320 MHz), **BSS** (basic service set), **MLD** (multi-link device), etc.
    
- Export per-interval snapshots (JSON/CSV) of: AP/STA inventory, links (per band/channel/link), PHY/MAC KPIs (RSSI, SNR, MCS, PER, retries), scheduling (OFDMA resource units), contention/backoff, association/auth frames, and **security events** (deauth/disassoc frames, spoofed beacons, jamming indicators).
    

> You’re playing the “controller” role the paper expects; your sim/logs are the **input** to KG via the Template’s mechanisms.

## 2) Design your Wi-Fi 7 KG schema (entities & relations)

Use the paper’s modeling style:

- **Entities (nodes):** `AccessPoint`, `Station`, `BSS`, `MLD`, `Link` (per MLO leg), `Channel`, `RU` (resource unit), `Flow`, `ACL/Policy`, `Frame` (with subtype), `AttackEvent`, `Counter/MetricSnapshot`, `RegulatoryDomain`.
    
- **Relations (edges):**
    
    - `Station -[associatesTo]-> BSS`, `BSS -[operatesOn]-> Channel`, `MLD -[hasLink]-> Link`, `Link -[usesRU]-> RU`, `AccessPoint -[hosts]-> BSS`
        
    - `Flow -[forwardsVia]-> Link`, `AccessPoint -[enforces]-> ACL/Policy`
        
    - `AttackEvent -[targets]-> (BSS|Station|Channel)`, `AttackEvent -[observedAt]-> AccessPoint`
        
    - `MetricSnapshot -[observes]-> (Link|BSS|Station)`
        
- **Properties:** time window, MAC (media access control) addresses, PHY/MAC fields, RSSI/SNR, MCS, retry/error counts, frame types, anomaly scores.
    

This mirrors the paper’s examples (e.g., flow tables/rules, host/switch) but in Wi-Fi terms.

## 3) Write Templates (YAML is fine) to ingest and reason

Following the paper, each **Template** declares:

- **Variables / Mechanisms:** where to fetch data (your simulator output); how often; which fields map to which entities/edges. (Paper shows this pattern for topology, devices, flows, ports.)
    
- **Policies:** queries to answer questions or compute outputs.
    

**Example policy ideas (Wi-Fi 7):**

- **Physical Reachability (radio):** Is `StationA` physically reachable from `AccessPointX` on any MLO link given current channel/RU assignments and SNR threshold? (Analogous to Physical Reachability Check, but in wireless terms.)
    
- **Forwarding/Rule Reachability (control):** Do ACLs and WPA3/802.11 state allow data frames from `StationA` to `StationB` via `AccessPointX`? (Analogous to Flow Rule Reachability.)
    
- **Deauth attack detection:** Are there bursts of deauth frames targeting specific BSS/Stations with inconsistent source OUI? Attach an `AttackEvent` node and a threat score.
    
- **Jamming/DoS:** Is there a sustained rise in PER/retries and energy detect without corresponding frame counts on a channel/RU?
    
- **MLO consistency:** If one MLO link is attacked (jamming/deauth), does a viable alternate link exist that maintains target throughput/latency?
    

> Use **query depth** thoughtfully: deeper queries (more nodes/relations) cost more, but the paper’s results show millisecond-level times even at depth 5 with ~21k nodes.

## 4) Implement the DTN Manager pieces

- **KG store:** Neo4j (or another graph DB) to hold Wi-Fi entities/edges. The paper favors graph queries over SQL for efficiency and context representation.
    
- **Connectors:** small ETL scripts that read the simulator’s outputs and **CREATE/UPDATE** nodes/edges (remember, writes are slower than reads; batch wisely).
    
- **Policy runner:** executes Cypher queries for each Template policy, returns results to your app/UI.
    

## 5) Analytics & prediction loop (paper-aligned)

- **Feature extraction:** From the KG, pull features per `BSS`, `Link`, or `Station` (windowed RSSI/SNR, PER, retry rate, RU occupancy, frame distributions, graph centrality of targets, presence of suspicious frames).
    
- **Learning:** Train a **supervised** model to classify attacks or a **forecasting** model to predict risk per entity. The paper explicitly calls out **predictive analysis and causality analysis** on KG data as future scope.
    
- **Actuation (optional, carefully):** If you choose to “heal” by switching channels/links or tightening ACLs, follow the paper’s caution: verify state **before/after** to avoid inconsistencies between DTN decisions and the controller.
    

## 6) Performance guardrails (so it stays fast)

- **Re-use KG;** avoid full rebuilds (seconds-minutes); incremental updates are fast (~18 ms per node in their setup).
    
- **Constrain query depth** and **partition** per BSS/Channel if the KG grows huge—acknowledging the complexity and consistency overhead the paper flags.
    

# Concrete examples (adapting the paper’s patterns)

### Example 1 — “Who serves this station now?” (like Host→Switch)

> Paper pattern: **Host <isConnected> Switch**.

**Wi-Fi 7 KG:**  
`Station{mac} -[associatesTo]-> BSS{bssid} -[operatesOn]-> Channel{center, width}`

**Cypher idea:**  
Find the BSS and channel that a given station is currently associated with; include MLO link list if any.

### Example 2 — “Is A reachable to B under current rules?” (like Flow Rule Reachability)

> “Reachable … only if the intermediary switches have flow rules that allow the packets…”

**Wi-Fi 7 analogue:**  
`StationA -> (BSS/Link path) -> StationB` is allowed if: association states are OK, security policies allow data frames, and no ACL blocks; then return hop count as number of L2 forwarding steps (AP backhaul, if modeled).

### Example 3 — “Depth-aware anomaly propagation”

> Query time rises with “query depth.” Design policies to stay within a bounded depth for real-time checks.

**Wi-Fi 7 policy:**  
From an `AttackEvent` on `Channel X`, traverse at most **depth 3**: Channel → BSS → Stations to quickly tag likely impacted nodes, then schedule a deeper batch job for extended effects (neighbors via co-channel adjacency graph).

# What you should learn (concepts & skills checklist)

1. **Digital Twin Network (DTN):** a synchronized virtual representation of a live network, used for **validation**, **automation**, **optimization**, and **analytics**.
    
2. **Knowledge Graph (KG):** graph model of entities/relations/properties that enables **context-rich, efficient queries** and **causality analysis**.
    
3. **Templates:** human-editable specs for what to collect and what to compute; separate **domain intent** from implementation; support **policy lifecycle** updates.
    
4. **DTN Manager modules:** Template Parser, KG Initialiser/Connector (CRUD), Policy Deployer, Mechanism Executor, KG Data Modeller. Know each role.
    
5. **Query design:** structure **Cypher** queries with bounded **depth**; read-heavy checks are fast; batch writes; reuse KGs.
    
6. **Performance pragmatics:** expect seconds-to-minutes for initial KG build; milliseconds for reads; scale cautiously; consider partitioning.
    
7. **Safety & privacy:** verify before actuation; treat inputs as untrusted; protect user/device privacy.
    
8. **AI/ML on KG:** plan for **predictive** and **causal** inference over graph-structured data.
    

# Quick glossary (acronyms used)

- **DTN** (Digital Twin Network): virtual twin of a live network.
    
- **SDN** (Software-Defined Networking): separates control plane from data plane; controller programs the network.
    
- **KG** (Knowledge Graph): graph DB of entities/relations/properties for context and queries.
    
- **ONOS** (Open Network Operating System): open-source SDN controller used in the PoC.
    
- **Neo4j**: a popular graph database; queried with **Cypher**.
    
- **CRUD** (Create, Read, Update, Delete): basic data operations.
    
- **REST API** (Representational State Transfer): HTTP API style used for controller data.
    
- **PoC** (Proof-of-Concept): initial implementation to demonstrate feasibility.
    
- **BSS** (Basic Service Set): Wi-Fi coverage domain of an AP radio.
    
- **MLO** (Multi-Link Operation): Wi-Fi 7 feature to use multiple links simultaneously.
    
- **OFDMA** (Orthogonal Frequency-Division Multiple Access): multiple users share RU subcarriers.
    
- **RU** (Resource Unit): OFDMA sub-channel allocation unit.
    
- **PER** (Packet Error Rate), **MCS** (Modulation and Coding Scheme), **RSSI** (Received Signal Strength Indicator), **SNR** (Signal-to-Noise Ratio).
    

---

## Putting it all together for your project (concise recipe)

1. **Pick simulator/log streams** → export JSON every Δt with AP/STA states, PHY/MAC metrics, frames, and any synthetic “threat events.”
    
2. **Define a Wi-Fi 7 KG schema** (entities/relations above).
    
3. **Write Templates**:
    
    - **Mechanisms**: map simulator files → nodes/edges/properties (topology, links, policies, frames, metrics).
        
    - **Policies**: Cypher queries for: physical reachability, rule reachability, deauth bursts, jamming signals, MLO failover viability.
        
4. **Stand up DTN Manager** modules (parser, connector, modeller, policy runner).
    
5. **Evaluate**: check **query depth** and end-to-end **latency**; reuse KG; partition by channel if needed.
    
6. **Predict**: extract graph/time-window features; train models to flag emerging threats; (optional) **actuate** mitigations only after pre/post verification.