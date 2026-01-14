## Coordinated Beamforming

- **What it is:** A key feature of 802.11ax and enhanced in 802.11be (Wi-Fi 7). It involves _multiple_ APs coordinating with each other to transmit _at the same time_ towards a _single_ client.
    
- **How it works:** By synchronizing their transmissions, the APs can shape a combined signal beam. This dramatically increases the signal strength (SNR), data rate, and range for that client, especially at the edge of the cell.
    
- **Security Relevance:** This creates a new, complex trust relationship between APs. **Security testing** must focus on the coordination protocol. If an attacker can inject fake coordination messages, they could de-synchronize the beams, causing destructive interference instead of constructive. This would instantly kill the client's connection (a highly targeted DoS).