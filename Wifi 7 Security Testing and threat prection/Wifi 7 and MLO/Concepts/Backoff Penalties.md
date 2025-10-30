## Backoff penalties

- **What it is:** "Backoff" is the core of Wi-Fi's "listen-before-talk" mechanism (CSMA/CA). When a device finds the channel busy, it waits for a random backoff period. A "penalty" refers to the fact that if a transmission fails (e.g., a collision), the _range_ of this random time (the Contention Window) increases, making the device wait longer, thus "penalizing" it to help reduce congestion.
    
- **How it works:** Each failed transmission attempt typically doubles the Contention Window, forcing the device to be "politer" and wait longer before its next attempt.
    
- **Security Relevance:** This mechanism can be exploited for a **Denial of Service (DoS) attack**. An attacker can repeatedly transmit signals that cause collisions or trick a victim device into thinking the channel is always busy. This forces the victim's backoff penalty to increase exponentially, effectively "starving" it and preventing it from ever getting a chance to transmit.

[[Backoff Compensation]]
[[Backoff in Wi-Fi]]
