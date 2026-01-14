## IEEE 802.11k

- **What it is:** A part of the Wi-Fi standard (an amendment) that enables **Radio Resource Measurement**.
    
- **How it works:** It allows a client to ask an AP for a "Neighbor Report." This report lists other nearby APs in the same network, their channels, and their signal strength. This helps the client make a fast and intelligent roaming decision _before_ it loses connection to its current AP.
    
- **Security Relevance:** The classic **"Evil Twin" attack** is amplified by 802.11k. An attacker can send a spoofed 802.11k Neighbor Report to a victim. This malicious report can trick the victim's device into "helpfully" roaming to the attacker's "evil twin" AP, which has the same name as the legitimate network. The victim connects, and the attacker now has a full Man-in-the-Middle (MITM) position.