Lets break down the **PHY and MAC layer changes in Wi-Fi 7 (IEEE 802.11be)** compared to Wi-Fi 6/6E. I’ll explain **what’s new, how it works, and why it matters**.

---

# 🔹 PHY Layer Amendments (Physical Layer)

The PHY layer handles **modulation, coding, channel usage**, and actual signal transmission. Wi-Fi 7 introduces several big changes:

|Feature|Description|How it works / Advantage|
|---|---|---|
|**320 MHz channels**|Channel bonding up to 320 MHz|Combines two 160 MHz channels → higher peak throughput (~46 Gbps theoretical)|
|**4096-QAM (4K-QAM)**|Higher-order modulation than 1024-QAM in Wi-Fi 6|Encodes 12 bits per symbol instead of 10 → increases data rate, but requires high SNR (good link quality)|
|**Multi-Link Operation (MLO)**|Use multiple bands (2.4, 5, 6 GHz) simultaneously|Increases throughput and reliability; can transmit/receive across multiple links in sync or async mode|
|**Multi-RU OFDMA enhancements**|Supports multi-user allocation across wide RUs|Improves spectral efficiency, reduces latency in multi-user scenarios|
|**Preamble enhancements**|New puncturing and flexible preambles|Allows partial channel use if parts of the spectrum are busy → better coexistence and efficiency|
|**Improved MIMO**|Up to 16 spatial streams (vs 8 in Wi-Fi 6)|Increases simultaneous multi-user throughput|
|**Channel puncturing / partial spectrum reuse**|Skip busy sub-channels during wideband operation|Enables coexistence with legacy devices or radar systems in DFS bands|

---

# 🔹 MAC Layer Amendments (Medium Access Control)

The MAC layer handles **how devices access the medium**, manage contention, schedule transmissions, and coordinate multi-link operation. Key Wi-Fi 7 changes:

|Feature|Description|How it works / Advantage|
|---|---|---|
|**Multi-Link MAC (Sync & Async)**|Supports synchronous or asynchronous MLO|Allows aggregated or independent transmission across multiple links; improves reliability and throughput|
|**Backoff Compensation**|Compensates for “free riding” in synchronous FT|Ensures fairness among links and devices even if one link finishes earlier|
|**Link Aggregation & Striping**|Data frames can be split across multiple links|Increases peak throughput and reduces latency|
|**Enhanced OFDMA scheduling**|More flexible resource unit allocation|Multiple users can share the same channel efficiently|
|**Frame preemption**|Supports sending urgent frames while lower-priority frames are paused|Improves QoS for latency-sensitive traffic (AR/VR, gaming)|
|**Preamble puncturing coordination**|MAC aware of partial channel availability|Ensures devices only transmit on available spectrum, improving coexistence with legacy or DFS users|
|**Target Wake Time (TWT) for multi-link devices**|Devices can schedule sleep/wake across multiple links|Saves power in IoT/STA scenarios while keeping high throughput possible|

---

# 🔹 Key Takeaways

1. **PHY changes → higher raw speed and better spectral efficiency**
    
    - Wider channels, higher QAM, more spatial streams, smarter use of partial spectrum.
        
2. **MAC changes → smarter, fairer, multi-link coordination**
    
    - Free ride compensation, multi-link scheduling, OFDMA improvements, preamble puncturing.
        
3. **Combined Effect**
    
    - Higher throughput (up to ~46 Gbps)
        
    - Lower latency (synchronous multi-link + OFDMA)
        
    - Better reliability and coexistence (partial channels, multi-link)
        
    - Fairer access for mixed environments (backoff compensation, frame preemption)
        

---

✅ **In short:**

- **PHY = faster pipes, more lanes, and smarter channel usage**
    
- **MAC = traffic cop + scheduler that coordinates multi-lane use fairly and efficiently**
    

---






#### Physical Layer (PHY) Enhancements:

- **Expanded Bandwidth:** Wi-Fi 7 will support wider bandwidth modes, including contiguous 240 MHz and 320 MHz, and non-contiguous modes like 160+80 MHz and 160+160 MHz. This is made possible by leveraging the newly available 6 GHz band.
    
- **Multi-RU Support:** Unlike Wi-Fi 6, where a user is assigned a single Resource Unit (RU), Wi-Fi 7 will allow the assignment of multiple RUs to a single user, enhancing spectral efficiency and flexibility.
    
- **4096-QAM:** The introduction of 4096-QAM (Quadrature Amplitude Modulation) will allow for a 20% increase in data rate compared to the 1024-QAM used in Wi-Fi 6.
    
- **Enhanced Preamble Design:** New preamble formats and improved preamble puncturing mechanisms are being designed to support the new features of Wi-Fi 7 while ensuring backward compatibility with legacy devices.
    

#### Medium Access Control (MAC) Layer Enhancements:

- **Multi-link Operation:** A significant innovation in Wi-Fi 7 is the ability to aggregate multiple frequency bands (2.4 GHz, 5 GHz, and 6 GHz) for simultaneous data transmission, a feature termed "multi-link" operation. This will significantly increase throughput and improve network flexibility.
    
- **MIMO Enhancements:** Wi-Fi 7 will increase the maximum number of spatial streams to 16, up from 8 in Wi-Fi 6. This requires the development of more efficient Channel State Information (CSI) feedback mechanisms to manage the increased overhead.
    
- **Multi-AP Coordination:** To improve spectrum efficiency and reduce latency, Wi-Fi 7 will introduce coordination among neighboring Access Points (APs). This includes features like Coordinated Spatial Reuse (CSR), Coordinated OFDMA (C-OFDMA), Coordinated Beamforming (CBF), and Joint Transmission (JXT).
    
- **Hybrid Automatic Repeat Request (HARQ):** The implementation of HARQ will enhance transmission reliability and lower latency by allowing the receiver to store and combine incorrectly decoded packets with their retransmissions, improving the chances of successful decoding.
    

