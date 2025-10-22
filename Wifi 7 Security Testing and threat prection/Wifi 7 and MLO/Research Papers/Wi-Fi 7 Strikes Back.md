This paper (from August 2020) positions IEEE 802.11be (Wi-Fi 7) as a revolutionary step to meet the demands of data-hungry and latency-sensitive applications. It provides a digest of Wi-Fi 7's essential features and makes a strong argument that **Multi-AP (Multi-Access Point) coordination** is a "must-have" feature, especially for critical applications. The authors use simulations of **Coordinated Beamforming (CBF)**—a key Multi-AP technique—to prove that it can lead to a near ten-fold (10x) reduction in worst-case delays, directly addressing the latency problem of previous Wi-Fi generations.

#### **Important Points & Pointers**

- **The Problem:** Current Wi-Fi is challenged by "hordes of data-hungry devices" and cannot support critical, low-latency applications effectively.
    
- **Wi-Fi 7's Promise:** The 802.11be amendment is described as a "(r)evolution" of unlicensed wireless connectivity.
    
- **The "Must-Have" Feature:** The authors single out **Multi-AP coordination** as the most critical feature for supporting latency-sensitive applications. While MLO (Multi-Link Operation) is a key feature, this paper's focus is on how multiple APs work together.
    
- **Simulation Proof:** The paper's core contribution is a simulation of Coordinated Beamforming (CBF). The results show that CBF can "steer" nulls in the signal (areas of no interference) towards neighboring devices, dramatically reducing interference and thereby lowering delay.
    
- **Key Result:** The simulations confirmed a **near-tenfold (10x) reduction in worst-case delays** for devices, which is a massive improvement for real-time applications like VR/AR or industrial control.
    

#### **New Terms & Technologies**

- **IEEE 802.11be (Wi-Fi 7):** The standard is positioned as the "strike back" against the challenges facing current Wi-Fi.
    
- **Multi-AP Coordination:** This is the flagship concept of the paper. It's a set of techniques that allow multiple APs on the same network to coordinate their transmissions. This is a significant change from traditional Wi-Fi where APs mostly ignore each other (or just try to avoid transmitting at the same time).
    
- **Coordinated Beamforming (CBF):** This is a specific _implementation_ of Multi-AP coordination. With CBF, multiple APs (e.g., in an office) can transmit at the same time to their respective devices. To prevent their signals from interfering with each other, they "coordinate" to form their transmission beams in a way that creates a "null" (an area of destructive interference, or a signal-dead-zone) precisely in the direction of the _other_ AP's client. This massively reduces inter-network interference.
    
- **Worst-Case Delays:** This is a key metric for latency-sensitive applications. It's not just about _average_ speed; it's about guaranteeing that the _longest_ delay a packet might experience is still very short. The paper's 10x reduction in this metric is highly significant.