1. **Selective congestion / interference**
    
    - Raise airtime occupancy or noise on one or more links (e.g., targeted interference, heavy legitimate traffic injection), causing scheduler to avoid those links → traffic concentrates on remaining links or falls back to naïve splitting.
        
2. **Spoofed telemetry / false reports**
    
    - Forge or tamper with reported link metrics (RSSI, airtime, PER) sent from AP or STA to the controller so the controller believes links are balanced (or alternate links are bad), inducing wrong splits.
        
3. **Control-plane manipulation (APC/Controller spoofing)**
    
    - If APC/central controller messages can be spoofed or replayed, attacker might push bad weight settings or force simplistic policies across APs.
        
4. **Beacon / management frame abuse**
    
    - Create misleading environment info (fake beacons, bogus BSS load indicators) so that distributed MLD logic misestimates congestion and chooses a naive policy.
        
5. **Resource exhaustion on resequencing / buffering**
    
    - Cause resequencing buffers to overflow (e.g., by flooding), forcing the device to prefer flow-level or equal-split modes to avoid out-of-order handling.
        

_(Note: the above are conceptual attack surfaces — I’m not giving implementation steps.)_

---

# What you would observe (indicators)

- Sudden concentration of traffic on a subset of links despite available capacity on others.
    
- Per-link airtime/collision metrics showing one link persistently busy/noisy while others idle.
    
- Controller/MLD telemetry that changes abruptly or inconsistently with physical measurements.
    
- Increased packet reordering, retransmissions, or queue drops.
    
- Correlated anomalies across clients (many STAs shifting flows the same way).
    

---

# Defenses / mitigations (practical)

1. **Validate telemetry**
    
    - Cross-check reported metrics with independent measurements (local PHY readings, passive sniffers, TRP readings). Use multiple indicators (airtime + PER + queue length) before changing steering.
        
2. **Conservative/hysteresis policies**
    
    - Avoid aggressive immediate rebalancing. Use EWMAs, thresholds, minimum dwell times and hysteresis for flow migration to prevent reacting to short transients or falsified spikes.
        
3. **Secure control plane & authentication**
    
    - Sign/Encrypt APC/controller messages and telemetry. Authenticate MLD↔controller communication to prevent spoofing.
        
4. **Anomaly detection / WIDS rules**
    
    - Detect targeted jamming or floods (sudden noise floor rise localized to a band). Trigger alerts and failover strategies.
        
5. **Diversity in decision inputs**
    
    - Use out-of-band or long-term statistics (history, geography, other APs) alongside instantaneous metrics to avoid single-point manipulation.
        
6. **Rate-limit management/control messages**
    
    - Protect against flood/spoofing of association/auth frames and telemetry.
        
7. **Graceful fallback behavior**
    
    - If link quality abruptly degrades, use controlled throttling or gentle migration rather than instant naive split; maintain fairness among STAs.
        

---

# For defenders / researchers

- In lab, you can **simulate** selective-link degradation (legitimate research only, on your own gear) to test scheduler robustness — but don’t use it on real-world networks without permission.
    
- Useful defense experiments: simulate spoofed telemetry and verify whether the controller trusts it blindly; test IDS alerts for airtime anomalies; measure how much hysteresis reduces mis-steering.