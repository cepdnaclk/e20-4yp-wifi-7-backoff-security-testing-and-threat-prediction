## Cyber-Threat Modeling (packet-level + fingerprinting)

1. **Model assets & topology** (NetBox → basic models).
    
2. **Enumerate attack surfaces** (AP beacons/probes, auth/assoc, data plane, control plane).
    
3. **Simulate attacks** (ns-3: deauth/jam/flood sources; containerlab: rogue DHCP/DNS/HTTP, lateral movement).
    
4. **Collect telemetry/pcaps** → feature extraction (PHY/MAC counters, timing, sizes, SNR/RSSI).
    
5. **Train DL models** (supervised anomaly classification) and/or **RL agents** (adaptive defense: channel reassign, power change, MLO rebalance).
    
6. **Closed loop**: deploy mitigations (e.g., tell the controller to **preamble-puncture**, **drop to cleaner channel**, or **steer clients**) and verify outcome in twin; later, push to real APs.