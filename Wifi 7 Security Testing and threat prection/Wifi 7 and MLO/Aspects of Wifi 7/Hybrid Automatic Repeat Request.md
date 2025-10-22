**major innovation** introduced in Wi-Fi 7 that significantly enhances reliability and throughput efficiency, especially in **high-speed multi-link and congested environments**.

---
[[High-level HARQ vulnerability categories (non-actionable)]]
## 🔹 **1. Background: Traditional ARQ vs HARQ**

### **Automatic Repeat Request (ARQ)**

- In older Wi-Fi versions (up to Wi-Fi 6/802.11ax), when a packet (MPDU) is **received in error**, the receiver discards it.
    
- The sender **retransmits the entire frame** until it’s correctly received or a retry limit is reached.
    
- Problem: Even if most of the frame was received correctly, it still needs to be retransmitted — **inefficient** for high-throughput channels.
    

### **Hybrid ARQ (HARQ)**

- **HARQ enhances ARQ** by combining **error detection and forward error correction (FEC)**.
    
- When a packet is received with errors:
    
    - The receiver **stores the soft information** (not just “correct” or “incorrect” bits).
        
    - When the retransmission arrives, the receiver **combines both transmissions** (original + retransmitted) to correct the errors.
        

In other words:

> Instead of throwing away corrupted data, HARQ “learns” from each retransmission.

---

## 🔹 **2. HARQ in Wi-Fi 7 (IEEE 802.11be)**

### **Introduction**

- HARQ is officially **introduced for the first time in the 802.11be amendment**.
    
- It works with **OFDMA and MU-MIMO**, enabling higher reliability over noisy or congested channels.
    

### **Core Concept**

Wi-Fi 7 HARQ operates using **soft combining** at the receiver:

1. **Transmission 1:**
    
    - Transmit MPDU block → receiver stores **soft bits** (probabilistic information).
        
2. **If errors detected:**
    
    - Receiver sends **NACK** (Negative Acknowledgement).
        
    - Soft bits are **cached** instead of discarded.
        
3. **Retransmission:**
    
    - AP retransmits the same MPDU (possibly with redundancy changes).
        
    - Receiver **combines both transmissions** to decode.
        
4. **If decoding succeeds:**
    
    - Receiver sends **ACK**, and both soft buffers are cleared.
        

This allows **incremental redundancy** — each retransmission contributes new information to correct the earlier errors.

---

## 🔹 **3. Key Features of HARQ in Wi-Fi 7**

|Feature|Description|
|---|---|
|**Soft Combining**|Receiver merges soft information from multiple transmissions (Chase combining or Incremental Redundancy).|
|**Low Latency Retransmission**|Faster recovery since fewer retransmissions are required.|
|**Increased Reliability**|Especially beneficial for long packets (A-MPDU) and high-QAM (4096-QAM) links.|
|**MAC-PHY Coordination**|HARQ requires tighter synchronization between MAC and PHY layers.|
|**HARQ Buffers**|Both transmitter and receiver must maintain **soft information buffers** for pending frames.|
|**Multi-Link Support**|HARQ can operate across multiple links — retransmissions can even occur on a different link if MLO is enabled.|

---

## 🔹 **4. HARQ Modes**

Wi-Fi 7 supports **two main HARQ schemes**:

### **a) Chase Combining**

- Retransmitted packet is **identical** to the original.
    
- Receiver **averages or sums** received soft bits to improve decoding probability.
    
- **Simple** but less efficient.
    

### **b) Incremental Redundancy (IR)**

- Retransmitted packets carry **different parity bits** (additional redundancy).
    
- Receiver combines all versions to reconstruct missing information.
    
- **More efficient**, but more complex and requires intelligent redundancy scheduling.
    

---

## 🔹 **5. HARQ in Multi-Link Operation (MLO)**

HARQ interacts tightly with **MLO features**:

- Retransmissions can be scheduled **on the same link** or **across links** (cross-link HARQ).
    
- If one link experiences interference or congestion, retransmission can occur on a **cleaner link**, improving reliability and throughput.
    
- HARQ in MLO must maintain **synchronization and buffer coherence** across all links.
    
- **Digital twins** of MLO can model HARQ buffer dynamics to test fault-tolerance and predict retransmission latency.
    

---

## 🔹 **6. Benefits of HARQ in Wi-Fi 7**

|Benefit|Explanation|
|---|---|
|**Improved Reliability**|Retains soft bits and reduces retransmission failures.|
|**Higher Spectral Efficiency**|Fewer retransmissions = better bandwidth use.|
|**Enhanced QoS**|Reduces jitter and delay for real-time traffic.|
|**Supports Higher Modulations**|Enables robust 4096-QAM performance even in noisy channels.|
|**Multi-Link Robustness**|Seamless operation across MLO links reduces packet loss.|

---

## 🔹 **7. Challenges and Limitations**

|Challenge|Description|
|---|---|
|**Memory Overhead**|Requires large soft buffers at both transmitter and receiver.|
|**Complexity**|PHY-MAC coordination and combining logic are complex.|
|**Cross-Link Synchronization**|In MLO, retransmission coordination across links adds delay.|
|**Energy Cost**|Continuous soft decoding increases power consumption.|
|**Security Implications**|Attackers might exploit buffer timing or HARQ feedback spoofing to trigger retransmission floods.|

---

## 🔹 **8. Security and Threat Implications (For Your Project)**

HARQ introduces **new attack surfaces** in Wi-Fi 7:

- **HARQ Feedback Spoofing** – Forging NACKs to trigger repeated retransmissions → DoS or congestion.
    
- **Buffer Overflow Exploit** – Overloading HARQ soft buffers to degrade system stability.
    
- **Timing Exploits in MLO** – Forcing asynchronous HARQ acknowledgements across links.
    

Digital twins can simulate these conditions for **threat prediction and security testing**, e.g., how **HARQ feedback manipulation** affects throughput or fairness under multi-link conditions.

---

## 🔹 **9. Summary**

|Aspect|Wi-Fi 6 (ARQ)|Wi-Fi 7 (HARQ)|
|---|---|---|
|Retransmission Type|Full packet|Soft-combined partial info|
|Efficiency|Low|High|
|Latency|Higher|Lower|
|Complexity|Simple|Complex (MAC-PHY integration)|
|MLO Support|N/A|Yes|
|Reliability|Moderate|High|
|Security Risks|Limited|New buffer & feedback-based threats|

---

## **10. Conclusion**

**Hybrid ARQ in Wi-Fi 7** represents a **paradigm shift** in wireless reliability and efficiency.  
By combining **error correction** and **intelligent retransmission**, HARQ enables:

- More resilient data delivery,
    
- Better QoS,
    
- And adaptive retransmission strategies across MLO links.
    

However, as HARQ adds **stateful buffers and real-time feedback loops**, it also opens **new vectors for performance degradation and security exploitation** — making it an essential component for **digital twin-based threat prediction and resilience testing** in next-generation Wi-Fi networks.