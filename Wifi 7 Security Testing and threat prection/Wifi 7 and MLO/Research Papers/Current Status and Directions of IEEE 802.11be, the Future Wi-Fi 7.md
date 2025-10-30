This paper provides a comprehensive overview of the upcoming **IEEE 802.11be standard**, also known as **Wi-Fi 7**, which aims to deliver Extremely High Throughput (EHT) to support future demanding applications like 8K video streaming, cloud gaming, and virtual reality. The target is a maximum throughput of at least **30 Gbps**.

#### Key Features and Enhancements:

- **Expanded Bandwidth**: [[Ultra-Wide Channels]] Wi-Fi 7 will introduce **320 MHz channel widths** by aggregating available spectrum, doubling the maximum channel size of Wi-Fi 6. It will also support non-contiguous channel bonding to make better use of fragmented spectrum.
    
- **Higher-Order Modulation**: [[4096-QAM Modulation]] The standard will incorporate **4096-QAM**, which packs 12 bits per symbol compared to 10 bits in Wi-Fi 6's 1024-QAM. This results in a 20% increase in the physical data rate.
    
- **Increased Spatial Streams**:  [[Multi-User OFDMA & MU-MIMO Enhancements]] The number of MIMO (Multiple-Input Multiple-Output) spatial streams will be doubled from 8 to **16**, significantly increasing network capacity.
    
- **Multi-Link Operation (MLO)**: [[MLO]] This is a headline feature that allows devices to connect and exchange data across multiple frequency bands (2.4 GHz, 5 GHz, and 6 GHz) simultaneously. MLO enables higher throughput through link aggregation and improved reliability by allowing fast switching between links if one is congested.
    
- **Multi-Access Point (Multi-AP) Coordination**: [[APC]]  [[Multi-AP Coordination]] Wi-Fi 7 introduces native coordination between access points. This includes techniques like:
    
    - **Coordinated Spatial Reuse [[Coordinated Spatial Reuse]] (CSR)** and **Coordinated OFDMA (C-OFDMA)** to mitigate interference.
        
    - **Coordinated Beamforming [[Coordinated Beamforming]](CBF)** and **Joint Transmission (JXT)** where multiple APs can transmit data to a single device simultaneously, improving signal strength and reliability.
        
- **Hybrid Automatic Repeat Request (HARQ)**: [[High-level HARQ vulnerability categories (non-actionable)]] To reduce latency, Wi-Fi 7 plans to adopt HARQ. This mechanism allows a receiver to save parts of a corrupted packet and combine them with a retransmission, increasing the chances of successful decoding without having to re-send the entire packet.
    

#### Challenges:

The paper highlights significant challenges, such as the increased overhead from acquiring channel state information (CSI) for 16 MIMO streams and the complexity of implementing robust Multi-AP synchronization and HARQ protocols.