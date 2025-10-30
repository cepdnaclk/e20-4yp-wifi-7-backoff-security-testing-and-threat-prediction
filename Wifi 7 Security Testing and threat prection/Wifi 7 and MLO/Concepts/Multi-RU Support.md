## Multi-RU support

- **What it is:** "RU" stands for **Resource Unit**. This is the key feature of OFDMA (introduced in Wi-Fi 6). "Multi-RU" is its enhancement in Wi-Fi 7.
    
- **How it works:** OFDMA allows an AP to divide a single channel (e.g., 20 MHz) into many small RUs. The AP can then serve _multiple_ clients _at the same time_ by assigning a different RU to each one. Wi-Fi 7's "Multi-RU" allows for more flexible and numerous RU combinations, including "puncturing" (excluding) small RUs that have interference.
    
- **Security Relevance:** The primary threat is **resource fragmentation**. An attacker could try to "game" the RU scheduler by repeatedly connecting and disconnecting or sending traffic that requests specific, awkward RU sizes. This could "fragment" the channel, preventing the AP from scheduling RUs efficiently for legitimate users, thereby reducing everyone's performance.