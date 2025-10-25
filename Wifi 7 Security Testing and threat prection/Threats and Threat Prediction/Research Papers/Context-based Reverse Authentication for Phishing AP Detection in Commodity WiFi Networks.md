### Context-based Reverse Authentication for Phishing AP Detection

- **Title:** Trident: Context-based Reverse Authentication for Phishing AP Detection in Commodity WiFi Networks
    
- **Authors:** Peng Zhao, Kaigui Bian, Ping Chen, Tong Zhao, Yichun Duan, and Wei Yan
    
- **Year:** Not specified (appears to be mid-2010s, as it references 802.11a/g/n)
    
- **Summary:** This paper presents "Trident," a novel software-based method for a client device (like a laptop or phone) to detect a phishing (rogue) Access Point (AP). Instead of the AP authenticating the user, Trident allows the user's device to "reversely authenticate" the AP. It uses a challenge-response protocol based on shared context (like time, location, or traffic patterns) that only the legitimate AP and user would know. This avoids costly hardware sensors or periodic network measurements.
    
- **Important Points:**
    
    - Phishing APs that spoof a legitimate AP's name (SSID) are a major security threat.
        
    - Trident is a lightweight solution that requires no special hardware.
        
    - The client "challenges" the AP with questions about shared context (e.g., "When did we last connect?" "What was our data usage?").
        
    - The AP's answers determine its legitimacy.
        
    - The method achieved a 98% detection rate for rogue APs in experiments.
        
- **New Technologies, Findings, and Important Aspects:**
    
    - **New Technology:** Trident, a context-based reverse authentication protocol for rogue AP detection.
        
    - **Relevance to Wi-Fi 7 Security Testing:** While not designed for Wi-Fi 7, the _concept_ is highly relevant. Wi-Fi 7's MLO introduces a new attack vector: "multi-link phishing," where an attacker might spoof only one link (e.g., the 5 GHz link) of a 3-link MLO connection to intercept traffic. Security testing should include scenarios to see if client devices can detect this partial spoofing.
        
    - **Relevance to Threat Prediction:** This paper helps predict how rogue AP attacks will evolve. Instead of just spoofing one SSID, attackers will attempt to spoof MLO "identities." Threat prediction must model these advanced rogue APs. The Trident concept could be adapted to create client-side defenses, e.g., by having the client verify context _across all links_ ("Is the signal strength on the 6 GHz link consistent with the 5 GHz link?").