## Channelization and tone plan

- **What it is:** "Channelization" is the process of dividing the available spectrum into usable channels (e.g., 20, 40, 80, 160, 320 MHz wide). The "tone plan" is how each channel is subdivided into hundreds or thousands of tiny subcarriers, or "tones," using OFDMA (Orthogonal Frequency-Division Multiple Access).
    
- **How it works:** The tone plan defines which tones carry data, which are "pilot tones" (for synchronization), and which are "guard tones" (to prevent interference). Wi-Fi 7 defines new tone plans for 320 MHz channels and for the new "punctured" Resource Units (RUs).
    
- **Security Relevance:** This is a very low-level (Physical Layer) concept. A highly sophisticated **threat** would be a signal-injection attack that targets the pilot tones. By corrupting these specific tones, an attacker could cause receivers to lose synchronization, leading to massive packet loss that is very difficult to diagnose.