## Congestion aware policies

- **What it is:** These are advanced rules that go beyond simple prioritization. They allow the network to react intelligently to real-time network congestion.
    
- **How it works:** Instead of just dropping packets, a congestion-aware MLO policy might dynamically move a high-bandwidth video stream from a congested 5 GHz link to a clear 6 GHz link, or even split it across both.
    
- **Security Relevance:** This logic can be "gamed." A **threat prediction** is an attacker sending bursts of traffic to "trick" the congestion-aware policy. By manipulating the network's perception of congestion, the attacker could "push" a victim's traffic onto a specific link that the attacker is prepared to jam or intercept, all without the victim knowing.