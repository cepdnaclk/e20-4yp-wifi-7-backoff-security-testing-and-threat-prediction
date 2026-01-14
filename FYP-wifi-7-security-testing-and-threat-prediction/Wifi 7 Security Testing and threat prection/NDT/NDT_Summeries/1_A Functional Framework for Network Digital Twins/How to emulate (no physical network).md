**How to emulate (no physical network yet):**

- **ns-3** (with 802.11 modules) is the right tool to **simulate PHY/MAC** behavior including RSSI, SNR, collisions, channel use, and interference. (Paper lists ns-3 explicitly.)
    
- **Containerlab** is great for **L2/L3 control/data-plane topologies** (routers/switches/VNFs), not radio. Use it to emulate **security middleboxes** (e.g., firewalls, IDS) and collectors.
    
- **NetBox** is an **inventory/SoT** tool; use it to define **topology/locations/channels/AP inventory** feeding your **basic models** in the twin.
    
- Combine: **NetBox** (topology) → **ns-3** (Wi-Fi PHY/MAC & RF) → **Containerlab** (IP paths, security VNFs) → **Kafka/TSDB** (telemetry sink). This mirrors the paper’s **multi-simulator** and **interoperability** vision.