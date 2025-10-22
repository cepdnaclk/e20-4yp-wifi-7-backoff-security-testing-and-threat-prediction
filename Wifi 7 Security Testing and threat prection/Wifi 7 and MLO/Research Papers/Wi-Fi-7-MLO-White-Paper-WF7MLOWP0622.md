### High-Level Summary

This white paper from MediaTek introduces Multi-Link Operation (MLO) as a key feature of Wi-Fi 7 (IEEE 802.11be). MLO is a MAC-layer solution that aggregates multiple links across different bands (2.4GHz, 5GHz, 6GHz) to function as a single connection. The primary goals are to significantly increase throughput, lower latency, and improve reliability, especially in congested networks.

The paper defines and compares three main MLO operation modes:

1. **STR (Simultaneous Transmit and Receive):** For devices with well-isolated radios, allowing independent and simultaneous transmission/reception on different links. This mode provides the lowest latency.
    
2. **NSTR (Non-Simultaneous Transmit and Receive):** For devices where radios can interfere with each other (In-Device Coexistence - IDC). This mode cannot transmit and receive at the same time and must synchronize transmissions on its links, often by aligning packet end times.
    
3. **EMLSR (Enhanced Multi-Link Single Radio):** A dynamic mode that can switch all its radios and antennas to a single, available link to boost throughput in busy environments.
    

Simulations show that EMLSR offers the best throughput in heavily loaded networks (80% improvement at 70% loading), while STR provides the best latency (85% reduction at 70% loading compared to a single link). The paper concludes by discussing different MAC-level system architectures for implementing MLO.

---

### Key Important Points

- **Primary Goal:** MLO is designed to aggregate links to multiply throughput, enable load-balancing, and drastically reduce latency.
    
- **Core Concept:** A Multi-Link Device (MLD) combines multiple "affiliated" devices (radios) into one logical device for the upper layers.
    
- **Performance in Congested Networks:** MLO is not just about peak speed; it's about reliability in busy environments. EMLSR, for example, showed an 80% throughput improvement in a 70% loaded network.
    
- **Latency Reduction:** MLO is critical for real-time applications. In a 70% loaded network, MLO (specifically STR) reduced latency from 145ms (single link) to 18ms (an 85% reduction).
    
- **Hardware Dependency:** The choice between MLO modes is not just software; it's hardware-dependent. STR requires sufficient signal isolation between radios, which may be difficult in small devices. NSTR is a solution for devices _without_ this isolation.
    
- **Implementation Varies:** There are multiple ways to build an MLO device. The paper details four different system architectures (Arch#1-Arch#4), with "Arch#1" (a single MAC) being the preferred solution for low latency and simplicity.
    

---

### New Technical Concepts (Relevant for Threat Modeling)

This paper details several new mechanisms that are critical for building a threat model, as they introduce new states, dependencies, and control frames that could be exploited.

1. **Multi-Link Device (MLD) Identity:**
    
    - An MLD consists of multiple "affiliated" STAs (e.g., STA 1 on Link 1, STA 2 on Link 2) that are part of one logical device.
        
    - These affiliated STAs share a **common transmitter sequence number (SN)**.
        
    - **Threat Implication:** This shared SN is a new identity-linking feature. An attacker could potentially use this to fingerprint MLDs. It also raises questions about authentication: if an attacker spoofs one affiliated STA, can they gain trust for another affiliated STA on a different link?
        
2. **NSTR Synchronization Vulnerability:**
    
    - NSTR devices _cannot_ transmit and receive simultaneously due to In-device Coexistence (IDC) interference.
        
    - To compensate, they must **synchronize transmissions**. For an uplink, if Link 1 is ready to send but Link 2 is busy (e.g., its backoff counter is not 0), **Link 1 must wait** for Link 2.
        
    - **Threat Implication:** This creates a new cross-link dependency. An attacker could launch a **Denial of Service (DoS)** attack by targeting _only one link_. By sending minimal traffic to keep Link 2 "Busy", an attacker could theoretically stall transmissions on _both_ links, effectively halting the entire MLD.
        
3. **EMLSR "Blindness" Vulnerability:**
    
    - EMLSR works by dynamically switching all its resources (spatial streams, or Nss) to a single, available link.
        
    - When this happens, the _other_ link temporarily has **Nss=0** and enters a "state of blindness," unable to transmit or receive.
        
    - This switch is triggered by specific control frames, such as a **MU-RTS (Multi-User Request to Send)**.
        
    - **Threat Implication:** This is a new, state-based vulnerability. An attacker could potentially **spoof the MU-RTS trigger frame** to force a device into EMLSR mode. This would "blind" the device's other link, making it easier to attack or creating a novel DoS vector. The paper notes that "recovery procedures" are needed to handle this blindness.
        
4. **MAC Architecture Attack Surfaces:**
    
    - The paper details four different hardware/software implementations (Arch#1-Arch#4).
        
    - Arch#4 is a "distributed" solution that requires an **inter-chip bus** to connect different MACs. The performance of this architecture is bounded by the speed of this bus.
        
    - **Threat Implication:** These different architectures present different attack surfaces. A distributed solution (Arch#4) might be vulnerable to side-channel or fault-injection attacks on the physical "inter-chip bus", while a single-MAC (Arch#1) might have a single software point of failure. An attacker who can fingerprint the underlying architecture could tailor an exploit.