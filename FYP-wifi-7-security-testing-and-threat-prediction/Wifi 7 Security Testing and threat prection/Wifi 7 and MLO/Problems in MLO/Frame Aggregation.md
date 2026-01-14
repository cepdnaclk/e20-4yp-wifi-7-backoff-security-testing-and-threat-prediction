### **Frame Aggregation in Wi-Fi 7 (802.11be)**

#### **1. Concept Overview**

Frame aggregation is a **MAC layer technique** used in modern Wi-Fi standards (starting from 802.11n) to **improve throughput efficiency** by reducing protocol overhead. Instead of sending one frame per transmission, multiple frames are **combined (aggregated)** and transmitted together in a single Physical Layer Protocol Data Unit (PPDU).

In Wi-Fi 7, frame aggregation is further enhanced to support the **Extremely High Throughput (EHT)** goals and to integrate with **Multi-Link Operation (MLO)** — allowing parallel transmissions across multiple links.

---

#### **2. Why Frame Aggregation Matters**

Each Wi-Fi frame typically includes significant overhead — MAC headers, inter-frame spaces, acknowledgments, etc. When small payloads are transmitted (e.g., TCP ACKs, IoT updates), this overhead can dominate, limiting effective throughput.

Frame aggregation reduces this overhead by:

- Combining multiple MAC frames into one transmission burst.
    
- Sharing PHY-level overhead (like preamble and inter-frame space).
    
- Allowing acknowledgment of multiple frames at once (Block ACK).
    

The result: **higher throughput**, **lower channel contention**, and **reduced latency** per data byte delivered.

---

#### **3. Types of Frame Aggregation**

##### **a) A-MSDU (Aggregated MAC Service Data Unit)**

- Combines multiple MSDUs (payloads from higher layers) into a single MPDU (MAC Protocol Data Unit).
    
- All subframes share the same MAC header and destination address.
    
- Simpler but less flexible — since all aggregated frames must go to the same receiver and use the same QoS parameters.
    

**Structure:**

`+-------------------+ | Common MAC Header | +-------------------+ | MSDU #1           | +-------------------+ | MSDU #2           | +-------------------+ | MSDU #n           | +-------------------+ | FCS               | +-------------------+`

##### **b) A-MPDU (Aggregated MAC Protocol Data Unit)**

- Aggregates multiple MPDUs (each with its own MAC header and FCS).
    
- Allows mixing frames to different receivers or TIDs (Traffic Identifiers).
    
- More robust — because even if one subframe fails, others may succeed (thanks to per-frame CRCs).
    

**Structure:**

`+------------------+ +------------------+ ... +------------------+ | MPDU #1 (FCS)    | | MPDU #2 (FCS)    |     | MPDU #n (FCS)    | +------------------+ +------------------+ ... +------------------+`

##### **c) Two-Level Aggregation (A-MSDU inside A-MPDU)**

Wi-Fi 7 allows nesting: multiple A-MSDUs can be grouped inside an A-MPDU.  
This combines the efficiency of A-MSDU with the robustness of A-MPDU.

---

#### **4. Frame Aggregation in Wi-Fi 7 (802.11be) Context**

Wi-Fi 7 extends frame aggregation mechanisms with:

- **Larger aggregation limits** (up to 8,192 frames per A-MPDU).
    
- **Shorter inter-frame spacing (SIFS)** to support ultra-low latency.
    
- **Improved Block ACK policies** for MLO coordination.
    
- **Multi-Link Frame Aggregation:** Frames can now be aggregated **across multiple links** (e.g., 5 GHz + 6 GHz), managed by an MLD (Multi-Link Device).
    
    - The scheduler decides how frames are distributed and acknowledged across links.
        
    - Aggregation decisions must synchronize with **link-level channel conditions** and **traffic steering** logic.
        

---

#### **5. Interaction with MLO**

In Multi-Link Operation, frame aggregation becomes more complex but more powerful:

- Each link can perform its own aggregation independently or cooperatively.
    
- Aggregated frames can be transmitted **simultaneously on multiple links** to improve parallelism.
    
- Coordinated acknowledgments (per link or unified block ACK) must ensure **ordering and fairness**.
    
- If aggregation decisions are manipulated or desynchronized, it could lead to **frame reordering, DoS, or QoS degradation**, forming part of potential **MLO exploits**.
    

---

#### **6. Security Implications (in context of your project)**

Frame aggregation introduces **logic-level vulnerabilities** in Wi-Fi 7 when used with MLO:

- Attackers can exploit **aggregation scheduling** to delay or reorder critical traffic (e.g., XR or AR streams).
    
- Malicious manipulation of link conditions or ACK timing could cause **aggregation failures** or **trigger retransmissions**, degrading service.
    
- The Digital Twin model can simulate such anomalies to detect if **aggregation imbalance** or **fragmentation misuse** arises from malicious influence rather than benign interference.
    

---

#### **7. Summary**

|Aspect|A-MSDU|A-MPDU|Wi-Fi 7 Extension|
|---|---|---|---|
|**Granularity**|MSDUs aggregated into one MPDU|MPDUs aggregated at PHY level|Multi-link, large-scale aggregation|
|**Efficiency**|High (low overhead)|Medium|Very high|
|**Robustness**|Low (single CRC)|High (per-frame CRC)|Enhanced with multi-link ACKs|
|**Use Case**|Same receiver, QoS|Multiple TIDs|Multi-Link operations, EHT|
|**Security Concern**|Timing abuse|ACK spoofing|Cross-link coordination exploit|

---

Would you like me to add a short **"Frame Aggregation Exploit Scenario"** section — showing _how_ an attacker could manipulate aggregation timing or ACK coordination under MLO (for your threat prediction section)?