#### **Summary**

This article argues that the next generation of Wi-Fi, IEEE 802.11be (Wi-Fi 7), is being designed to move beyond just high throughput and will incorporate **Time-Sensitive Networking (TSN)** capabilities. The goal is to make Wi-Fi 7 a viable technology for low-latency, high-reliability applications (like industrial IoT, healthcare, and multimedia) that were previously only possible with wired Ethernet. It introduces the key features of Wi-Fi 7 and discusses how they create a foundation for implementing TSN functionalities over wireless.

#### **Important Points & Pointers**

- **Wi-Fi's New Goal:** Wi-Fi 7's primary objective is not just higher speed, but also supporting **low-latency and ultra-reliability** to compete with wired TSN.
    
- **The Problem with Wi-Fi:** Traditional Wi-Fi (even Wi-Fi 6) struggles with latency-sensitive applications because its core access method, CSMA/CA (Carrier Sense Multiple Access with Collision Avoidance), is inherently contention-based and non-deterministic. This leads to unpredictable delays.
    
- **The Solution (TSN):** TSN is a set of IEEE 802.1 standards that provide deterministic connectivity (guaranteed low latency and reliability) over wired Ethernet. This paper explores how to bring TSN's _functionality_ to 802.11be.
    
- **Wi-Fi 7 as the Enabler:** The paper states that key Wi-Fi 7 features are the building blocks that make wireless TSN possible. These features are:
    
    1. **Multi-Link Operation (MLO):** [[MLO]]Allows a device to use multiple links in different bands (2.4, 5, 6 GHz) simultaneously. This is the **most critical feature** for reliability. If one link is congested or experiences interference, latency-sensitive traffic can be instantly moved to another, clearer link.
        
    2. **320 MHz Channels:** [[Ultra-Wide Channels]]Wider channels for extremely high throughput (EHT).
        
    3. **4096-QAM:** Higher-order modulation for more data per signal.[[4096-QAM Modulation]]
        
    4. **Multi-AP Coordination:** [[Multi-AP Coordination]]Multiple Access Points coordinate to reduce interference and improve efficiency, especially at the cell edge.
        
- **Use Cases:** The paper explicitly links these new capabilities to specific IoT scenarios:
    
    - **Multimedia:** 4K/8K streaming, VR/AR, cloud gaming.
        
    - **Healthcare:** Real-time patient monitoring and remote surgery (telesurgery).
        
    - **Industrial:** Real-time control of robotics, factory automation (Industry 4.0).
        
    - **Transport:** Vehicle-to-everything (V2X) communications.
        

#### **New Terms & Technologies**

- **IEEE 802.11be (Wi-Fi 7):** The upcoming Wi-Fi standard, also known as Extremely High Throughput (EHT).
    
- **Time-Sensitive Networking (TSN):** [[Time-Sensitive Networking (TSN)]] A set of IEEE 802.1 standards to make Ethernet deterministic. This paper is about applying its _principles_ to Wi-Fi.
    
- **Ultra-Reliability:** A new design goal for Wi-Fi, meaning the network must deliver data consistently with very low packet loss.
    
- **Low-Latency Communications:** The other key design goal, aiming to significantly reduce the delay (latency) in data transmission to support real-time applications.
    
- **Multi-Link Operation (MLO):** The landmark feature of Wi-Fi 7. It allows a single device (a Multi-Link Device or MLD) to establish multiple links with an AP, aggregating them for higher throughput and/or using them for seamless switching to improve reliability and reduce latency.
    
- **Multi-AP Coordination:** A feature where multiple Wi-Fi 7 APs work together. This can include Coordinated OFDMA (C-OFDMA) or Coordinated Beamforming (CBF) to manage interference and improve network performance for all users.