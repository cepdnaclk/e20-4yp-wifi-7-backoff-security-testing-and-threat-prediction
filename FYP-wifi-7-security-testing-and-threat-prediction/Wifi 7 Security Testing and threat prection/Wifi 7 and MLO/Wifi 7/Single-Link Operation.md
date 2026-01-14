## Single-Link Operation (SLO)

- **What it is:** This is the name for how Wi-Fi has always worked before MLO. A device connects to an AP on a _single channel_ in a _single band_ (e.g., 5 GHz, channel 44).
    
- **How it works:** If the device wants to change bands (e.g., move from 5 GHz to 2.4 GHz), it must completely disconnect and re-authenticate.
    
- **Security Relevance:** This is the "fallback" state. A key **security test** for Wi-Fi 7 is to see if an attacker can force a **downgrade attack**. By jamming or spoofing MLO setup frames, an attacker might be able to force a Wi-Fi 7 device to give up on MLO and fall back to SLO, thus stripping it of all its next-generation performance benefits.