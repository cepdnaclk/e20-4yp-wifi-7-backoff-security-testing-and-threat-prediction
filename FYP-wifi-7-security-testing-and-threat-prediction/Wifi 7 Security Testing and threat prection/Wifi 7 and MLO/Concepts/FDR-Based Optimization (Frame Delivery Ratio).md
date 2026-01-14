**efinition:**  
FDR (Frame Delivery Ratio) measures the **probability of successful frame transmission** between a station and an access point.

**Why it’s important:**  
Traditional Wi-Fi roaming uses **RSSI (signal strength)**, which doesn’t always reflect real communication reliability.  
FDR provides a **direct, application-relevant metric**—especially for time-sensitive or industrial use cases.

**Optimization logic:**  
WiTwin uses FDR to decide when to trigger roaming:
![[Pasted image 20251025112150.png]]


This selects the AP with **highest aggregate FDR** across all channels, minimizing packet loss and delay.

**Benefits:**

- Reduces latency spikes during handovers.
    
- Avoids unstable or oscillating connections.
    
- Reflects **real network performance**, not just signal strength.
    

---

### 🔁 **3. Sequential MLD Reassociation**

**Definition:**  
A **multi-link device (MLD)** can connect to multiple APs or channels simultaneously.  
Sequential MLD reassociation means **migrating one link at a time** during roaming instead of switching all links simultaneously.

**Process:**

1. WiTwin detects that another AP offers better quality.
    
2. It instructs the STA to move links sequentially (e.g., l₂ → l₃ → l₁).
    
3. While one link migrates, others remain active, ensuring continuous communication.
    

**Result:**

- The STA is momentarily connected to both APs (old and new).
    
- The **U-MAC** layer chooses the best path per frame.
    
- No interruption in data flow — crucial for **time-sensitive control systems**.
    

**Benefits:**

- **Seamless handover** with near-zero packet loss.
    
- Maintains bounded latency during roaming.
    
- Supports industrial-grade reliability for moving robots or machines.