**What it is:** attacker sends fake beacon frames advertising many SSIDs (or spoofed beacon info) to confuse clients or overwhelm wardriving tools.  
**Impact:** user confusion, client UI clutter, potential DoS of clients/AP scanning.  
**Indicators:** many transient SSIDs visible, logs with numerous beacon anomalies.  
**Mitigation:** client hardening, AP-side filtering, RF monitoring to detect beacon floods.