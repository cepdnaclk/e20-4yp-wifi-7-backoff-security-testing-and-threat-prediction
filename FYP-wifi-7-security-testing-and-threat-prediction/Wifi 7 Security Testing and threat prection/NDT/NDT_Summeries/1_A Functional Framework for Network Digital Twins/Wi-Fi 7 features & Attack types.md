tag:Wifi_7_DT
## Wi-Fi 7 features

- **MLO (Multi-Link Operation):** a single device uses **multiple links (bands/channels)** simultaneously (e.g., 5 GHz + 6 GHz) to increase throughput/reliability.
    
- **Preamble puncturing:** transmit on a **partial channel** when part of a wide channel is busy (more flexible spectrum use).
    
- **EHT scheduling:** **Extremely High Throughput** MAC scheduling features introduced in 802.11be to coordinate multi-RU, multi-link, and OFDMA resources efficiently.
    

You will want to parameterize these in **ns-3 or OMNeT++** to test resilience under threat scenarios (e.g., jamming one link while MLO keeps session alive).

## Attack types you mentioned

- **Deauth**: sending spoofed deauthentication frames to drop clients.
    
- **Flooding**: generating excessive management/data frames to exhaust airtime/CPU (DoS).
    
- **Jamming**: emitting RF noise to reduce SNR and break comms (broadband or tone jamming).  
    In the twin, you simulate them as **interference sources**, **traffic floods**, or **malicious event generators**, then see how KPIs shift.
    

## Traffic fingerprinting

- Extracting patterns from traffic (timing, sizes, burstiness, frame types/MCS sequences) to **identify device/app behaviors** or **malicious signatures** without payload inspection. Useful for **anomaly detection** and **threat intel**.