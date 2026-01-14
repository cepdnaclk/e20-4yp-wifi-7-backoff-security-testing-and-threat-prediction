## Channel allocation strategy

- **What it is:** This refers to the algorithm an AP uses to select which channels to operate on. In Wi-Fi 7, this is far more complex than before. An MLO AP must select _multiple_ channels in _multiple_ bands (e.g., an 80 MHz channel in 5 GHz and a 320 MHz channel in 6 GHz) that it will use simultaneously.
    
- **How it works:** The strategy aims to pick channels with the least interference. It also incorporates "puncturing," where it can use a wide 320 MHz channel but "puncture out" (not use) a 20 or 40 MHz segment within it that has interference (e.g., from a legacy device).
    
- **Security Relevance:** An attacker can perform a **resource exhaustion attack**. By spoofing radar signals (on DFS channels) or generating targeted noise on specific 6 GHz channels, an attacker can trick the AP's allocation strategy into choosing suboptimal channels or avoiding wide channels altogether, severely degrading the entire network's performance.