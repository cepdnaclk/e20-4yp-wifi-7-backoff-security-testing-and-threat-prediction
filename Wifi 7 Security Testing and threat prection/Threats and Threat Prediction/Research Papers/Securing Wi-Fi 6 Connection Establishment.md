- **Title:** Securing Wi-Fi 6 Connection Establishment Against Relay and Spoofing Threats
    
- **Authors:** Naureen Hoque and Hanif Rahbari
    
- **Year:** 2025 (arXiv submission)
    
- **Summary:** This paper presents a novel, backward-compatible security scheme to protect the Wi-Fi 6 (802.11ax) connection establishment (CE) phase. It notes that even with WPA3, the initial "pre-authentication" frames are unprotected, leaving networks vulnerable to preamble spoofing, Man-in-the-Middle (MitM), and relay attacks. The proposed solution embeds slices of a digital signature into the Physical (PHY) layer preamble of the connection frames, combined with tight timing constraints. This allows a station to verify the Access Point's (AP's) authenticity at the hardware level _before_ the main authentication handshake, effectively defeating these attacks.
    
- **Important Points:**
    
    - The Wi-Fi CE phase is a major security gap, as WPA3 and 802.11w only protect management frames _after_ mutual authentication is complete.
        
    - The proposed defense works by slicing a MAC-layer signature and embedding it in the PHY-layer preamble, adding negligible overhead and requiring no extra frames.
        
    - A key part of the defense is using timing constraints to detect relay attacks. An attacker physically relaying a frame will always introduce a small, measurable delay (latency) that the station can detect.
        
    - The authors built a "fast relay attack" using USRPs (software-defined radios) to prove their time-bound defense works even in a worst-case scenario.
        
- **New Technologies, Findings & Aspects (Context: Wi-Fi 7 Security):**
    
    - **New Technologies:** The paper details a PHY-layer authentication mechanism, embedding signatures directly into the preamble signal. It also uses ML (Principal Component Analysis) to help stations identify the correct AP's frames at the PHY layer in crowded environments.
        
    - **Relevance to Wi-Fi 7:** This paper is **critically and directly relevant**. The authors explicitly state: "We have also verified that the current draft of IEEE 802.11be (the upcoming standard—Wi-Fi 7) **does not amend any CE components**".
        
    - **For Security Testing:** This means Wi-Fi 7 inherits all of Wi-Fi 6's connection establishment vulnerabilities. Security testing for Wi-Fi 7 _must_ include preamble spoofing, frame relaying, and MitM attacks on the pre-authentication phase.
        
    - **For Threat Prediction:** This paper not only predicts a major threat vector for Wi-Fi 7 (unsecured connection) but also proposes a viable solution.