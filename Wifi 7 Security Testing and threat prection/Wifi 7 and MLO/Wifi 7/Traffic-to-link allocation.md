## Traffic-to-link allocation

- **What it is:** This is the _policy_ and _algorithm_ that an MLO device uses to decide which link (or links) to use for a specific traffic flow. It's a more granular version of "AC to link allocation."
    
- **How it works:** The policy might map a specific _application_ (like Zoom or Netflix) to a specific link based on its needs (e.g., low latency for Zoom, high bandwidth for Netflix).
    
- **Security Relevance:** This is a key target for **algorithmic complexity attacks**. If an attacker can reverse-engineer (or guess) this allocation algorithm, they can "game" it. For example, they could send traffic that looks like "Best Effort" but is designed to trick the algorithm into giving it the same priority and link access as a high-priority video call, effectively "stealing" resources from legitimate users.