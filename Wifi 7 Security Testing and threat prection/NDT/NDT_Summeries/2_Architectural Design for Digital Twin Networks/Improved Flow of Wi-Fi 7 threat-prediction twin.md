## 2.1 NetBox (inventory & topology “source of truth”)

- **Keep:** AP (Access Point) inventory, floors/rooms, channels, Tx limits.
    
- **Improve:** Treat NetBox as **part of the Data pillar** (configuration/state) and **seed your simulator** from it. Version every topology change to enable **historical replays** (“track data historically… highly beneficial… validate against the same datasets”) .
    
- **Add:** Export a **UDR (Unified Data Repository)** schema document: devices, radios, links, rooms, walls/attenuation, policies, labels for scenarios (benign/attack). This makes “Models ↔ Repository” interop easier, which the paper stresses (unified and efficient data gathering + storage) .
    

## 2.2 ns-3 (simulator for Wi-Fi 7 / 802.11be with MLO (Multi-Link Operation))

- **Keep:** PHY (physical layer) realism (EHT (Extremely High Throughput), puncturing), mobility, walls, attacks (deauth/disassoc floods, rogue beacons, jamming).
    
- **Improve:** Follow the paper’s **selective simulation** idea: don’t simulate _everything_ all the time. Run **fast coarse simulations** for continuous operation and **deeper “what-if” simulations** on demand. They highlight simulators are resource-intensive and limited for large real-time use; use them “surgically” .
    
- **Add:** A **graph side-model** for topology/roaming reasoning (paper used LEMON C++ graph lib; you can use NetworkX (Python) or a graph DB) to encode connectivity/context cheaply and continuously, reserving ns-3 for high-fidelity bursts .
    

## 2.3 Containerlab (emulated L2/L3 services)

- **Keep:** AAA (Authentication, Authorization, Accounting), controller, SIEM/IDS (Security Information/Event Management / Intrusion Detection System), firewall; **Kafka/MQTT** buses.
    
- **Improve:** Treat this as your **Application-facing & Internal Interfaces** fabric. The paper urges **open/standard interfaces** to avoid lock-in (“essential… to be open and standardized”) and highlights **MQTT/Kafka/REST** for modularity and scale .
    
- **Add:** A **southbound “config proxy”** service between DTN and simulator (the paper recommends an intermediate manager when update frequencies are high, or multiple DTNs share the same infrastructure) .
    
