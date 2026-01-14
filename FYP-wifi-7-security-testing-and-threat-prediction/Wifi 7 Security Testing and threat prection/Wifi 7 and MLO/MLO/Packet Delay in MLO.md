## Packet delay in MLO

- **What it is:** A critical performance metric. MLO's goal is to provide ultra-low latency (delay).
    
- **How it works:** MLO can reduce delay by sending a packet on whichever link becomes free first. However, it can also _cause_ delay. If a data stream is split (packet 1 on link A, packet 2 on link B) and link A has sudden interference, packet 1 might arrive _after_ packet 2. The receiver must then re-order them, which adds "jitter" or delay.
    
- **Security Relevance:** This is a prime target for a **QoS (Quality of Service) degradation attack**. An attacker doesn't need to block _all_ links. They can apply intermittent, "bursty" jamming to just _one_ link of an MLO group. This forces the MLO device's reordering buffer to constantly work overtime, adding significant delay and jitter. This attack would be invisible to most users (their Wi-Fi icon would look fine) but would make video calls, gaming, and AR/VR completely unusable.