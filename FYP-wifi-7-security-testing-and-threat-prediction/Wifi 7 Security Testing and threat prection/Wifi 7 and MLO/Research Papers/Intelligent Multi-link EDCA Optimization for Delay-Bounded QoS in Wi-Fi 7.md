### **`Intelligent Multi-link EDCA Optimization for Delay-Bounded QoS in Wi-Fi 7`**

#### **Summary**

This paper (from September 2025) tackles a major challenge for Wi-Fi 7: guaranteeing strict, low-latency **Quality of Service (QoS)** for applications like AR/VR. The authors argue that MLO by itself is not enough, because the standard Wi-Fi QoS mechanism, **EDCA**, uses _static_ parameters (fixed priorities for Voice, Video, etc.) that cannot adapt to the complex, dynamic nature of an MLO network.

The paper proposes an "intelligent" solution that uses a **Genetic Algorithm (GA)** to _jointly_ and _dynamically_ optimize two things at once:

1. **AC-to-Link Allocation:** Intelligently deciding which MLO link (e.g., 5 GHz or 6 GHz) should handle which traffic type (e.g., Voice vs. Video).
    
2. **EDCA Parameters:** Dynamically changing the priority parameters (like wait times) for _each_ traffic type on _each_ link.
    

This creates a highly adaptive system that can meet strict "delay-bounded" requirements (e.g., 99% of packets arrive in <10ms) even under high network load.

#### **Important Points & Pointers**

- **The Problem:** Using MLO with _static_ EDCA (the default QoS) is inefficient. A link that is good for one traffic type might be bad for another, and fixed priorities can't adapt to changing network congestion or interference.
    
- **The Goal:** To satisfy **"Delay-Bounded QoS,"** which is a strict promise on latency (e.g., minimizing the "delay violation probability").
    
- **The Solution:** An "intelligent" system using a **Genetic Algorithm (GA)**, which is an AI optimization technique.
    
- **Joint Optimization:** This is the key. The GA doesn't just manage traffic (item 1) or just tweak parameters (item 2); it does _both at the same time_ to find the best possible combined configuration.
    
- **Adaptive & Dynamic:** Unlike static EDCA, this solution constantly adapts the network's QoS rules based on real-time traffic and link quality.
    
- **Hardware Focus:** The model is designed for MLO devices operating in **STR (Simultaneous Transmit and Receive)** mode, meaning they can transmit and receive at the same time on different links.
    

#### **New Terms & Technologies**

- **EDCA (Enhanced Distributed Channel Access):** The standard Wi-Fi QoS mechanism that prioritizes traffic. It separates data into four **Access Categories (ACs)**: Voice (AC_VO), Video (AC_VI), Best Effort (AC_BE), and Background (AC_BK).
    
- **Delay-Bounded QoS:** A strict performance guarantee that a packet will arrive within a certain maximum time (e.g., under 10ms).
    
- **Delay Violation Probability:** The percentage of packets that _fail_ to meet the delay bound (the goal is to get this as close to 0% as possible).
    
- **Genetic Algorithm (GA):** A type of AI optimization algorithm inspired by natural selection. It "evolves" a solution by testing many configurations, "breeding" the best ones, and "mutating" them to find an optimal result.
    
- **AC-to-Link Allocation:** The _strategy_ for assigning specific QoS traffic types (Access Categories) to specific physical radio links.[[Qos in MLOs and Wifi 7]] [[AC to channel Allocation]]
- 