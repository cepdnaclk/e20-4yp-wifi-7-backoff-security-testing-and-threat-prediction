## Dynamic policies in MLO

- **What it is:** This refers to the real-time, intelligent decision-making engine of Multi-Link Operation (MLO). These policies decide, on a packet-by-packet or flow-by-flow basis, how to use the available links.
    
- **How it works:** The policy engine constantly analyzes link quality, congestion, latency, and application requirements to make decisions like:
    
    - "This packet is for a game; send it on the lowest-latency link."
        
    - "This packet is for a file download; split it across all links."
        
    - "This packet is for a VoIP call; _duplicate_ it on two links to ensure it arrives."
        
- **Security Relevance:** The policy engine itself is a target. **Threat prediction** models must account for attacks that try to _influence_ this engine. By sending carefully crafted traffic, an attacker could "poison" the policy's decision-making, leading to massive packet reordering (which adds latency) or forcing critical traffic onto a single, vulnerable link.