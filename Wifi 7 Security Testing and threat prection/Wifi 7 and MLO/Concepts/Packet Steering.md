## **1. Introduction to Packet Steering**
[[Early steering and late steering and combined steering]]
**Packet Steering** refers to the process of **dynamically directing network packets from a single STA or AP across multiple available links** in a Wi-Fi 7 MLO setup.

- Goal: **maximize throughput, minimize latency, and maintain QoS**.
    
- Relevance: With **STR and Non-STR MLO**, STAs can transmit or receive on multiple frequency bands (e.g., 5 GHz + 6 GHz), and packets need intelligent allocation across these links.
    

---

## **2. Objectives of Packet Steering**

1. **Throughput Optimization**
    
    - Assign flows to the **best-performing links** based on real-time PHY rate, congestion, and interference.
        
2. **Latency and QoS Management**
    
    - Prioritize **AC_VO (Voice) or AC_VI (Video)** flows on low-latency links while lower-priority flows use remaining links.
        
3. **Load Balancing Across Links**
    
    - Prevent congestion on a single link and fully utilize available spectrum.
        
4. **Reliability and Redundancy**
    
    - Redirect packets from a failing or congested link to other links to **maintain connection continuity**.
        

---

## **3. Mechanisms of Packet Steering**

### **3.1 Link Selection**

- Based on **link metrics** such as:
    
    - SNR / RSSI
        
    - PHY rate / modulation and coding scheme (MCS)
        
    - Packet error rate (PER)
        
    - Current TXOP utilization
        
- Packet steering can be **per-frame** or **per-flow**, depending on latency and QoS requirements.
    

### **3.2 AC-Aware Steering**

- Each **Access Category (AC)** may be steered differently:
    

|AC|Steering Policy|
|---|---|
|AC_VO (Voice)|Pin to low-latency link, avoid reordering|
|AC_VI (Video)|Aggregate across multiple high-throughput links|
|AC_BE (Best Effort)|Use remaining capacity, can tolerate reordering|
|AC_BK (Background)|Opportunistic allocation, low priority|

### **3.3 STR vs Non-STR Steering**

- **STR (Simultaneous Transmit and Receive)**: Packets can be sent/received **simultaneously on multiple links**.
    
- **Non-STR**: Steering must **alternate packets between links**, introducing potential latency and reordering.
    

### **3.4 Scheduler Integration**

- The **AP or STA scheduler** uses packet steering to:
    
    - Decide which link a packet should traverse
        
    - Manage TXOPs and contention per link (EDCA)
        
    - Balance airtime fairness among STAs
        

---

## **4. Packet Steering Strategies**

### **4.1 Static Steering**

- Predefined mapping of flows to links.
    
- Simple, but does not adapt to **dynamic link conditions** or congestion.
    

### **4.2 Dynamic Steering**

- Decisions based on **real-time metrics** (SNR, PER, congestion).
    
- Adaptive to traffic bursts, interference, and link failures.
    

### **4.3 Intelligent / Predictive Steering**

- Uses **Markov chains, machine learning, or MAB models** to predict:
    
    - Future link quality
        
    - Scheduler behavior
        
    - Optimal flow allocation
        
- Minimizes latency, reordering, and potential for packet loss.
    

---

## **5. Challenges in Packet Steering**

1. **Dynamic Link Quality**
    
    - Unlicensed spectrum links can fluctuate due to interference.
        
2. **Packet Reordering**
    
    - Aggregating packets across links with different delays can cause TCP inefficiency or jitter-sensitive flow degradation.
        
3. **Scheduler Complexity**
    
    - Requires **real-time computation** of per-packet decisions across multiple ACs and links.
        
4. **Security Considerations**
    
    - Attacks can exploit steering policies:
        
        - Force high-priority traffic onto bad links
            
        - Induce naive splitting of flows
            
        - Manipulate scheduler perception via interference or congestion attacks
            
5. **STR Hardware Limitations**
    
    - Simultaneous transmission requires multiple RF chains and isolation, increasing device complexity.
        

---

## **6. Benefits of Packet Steering**

- **Throughput Maximization**: Fully utilize multiple links simultaneously.
    
- **QoS Compliance**: High-priority flows maintain low-latency and low-jitter paths.
    
- **Load Balancing**: Reduces congestion on individual links.
    
- **Resilience**: Improves reliability against link failure or interference.
    

---

## **7. Research Trends and Gaps**

- **Existing Research**:
    
    - Some work uses **dynamic steering with link-quality metrics**, but mostly theoretical.
        
    - Predictive steering using **Markov chains or MAB models** is emerging.
        
- **Gaps**:
    
    - Few studies consider **security implications of packet steering**, e.g., malicious link manipulation.
        
    - Limited integration of **digital twins** to safely simulate steering under adversarial conditions.
        
    - STR vs Non-STR performance optimization under realistic interference in **unlicensed spectrum** is underexplored.
        

---

## **8. Summary**

Packet Steering in Wi-Fi 7 MLO:

1. Dynamically directs packets across multiple links for **throughput, QoS, and reliability**.
    
2. Requires integration with **EDCA, link metrics, and intelligent scheduling**.
    
3. Faces challenges of **reordering, dynamic link quality, and security vulnerabilities**.
    
4. Research opportunities exist in **intelligent, secure, and predictive packet steering**, particularly with **digital twin-based modeling**.