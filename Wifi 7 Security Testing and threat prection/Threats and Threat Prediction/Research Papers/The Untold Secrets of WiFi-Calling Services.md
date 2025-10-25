- **Title:** The Untold Secrets of WiFi-Calling Services: Vulnerabilities, Attacks, and Countermeasures
    
- **Authors:** Tian Xie, Guan-Hua Tu, Bangjie Yin, Chi-Yu Li, Chunyi Peng, Mi Zhang, Hui Liu, and Xiaoming Liu
    
- **Year:** 2020
    
- **Summary:** This paper investigates the security of Wi-Fi Calling (VoWiFi) services, which route cellular calls over untrusted Wi-Fi networks. The authors demonstrate that even with standard security like IPSec and SIM-based authentication , these services are not "bullet-proof". The study uncovers three major vulnerabilities related to insecure network selection, traffic analysis side-channels, and service continuity failures. The researchers used these to create two proof-of-concept attacks: one for telephony denial of service and one for user privacy leakage.
    
- **Important Points:**
    
    - Wi-Fi Calling exposes 3GPP IMS services to threats from the public internet.
        
    - The paper identifies three key vulnerabilities:
        
        1. **V1:** Devices connect to Wi-Fi networks based on signal quality, not security.
            
        2. **V2:** Encrypted IPSec traffic is vulnerable to side-channel inference attacks, allowing an attacker to determine calling events (e.g., ringing, talking).
            
        3. **V3:** The service continuity mechanism to switch back to cellular during poor Wi-Fi quality can fail to trigger during an attack.
            
    - The researchers built a "User Privacy Inference System (UPIS)" that could link a user's identity to their call statistics and IP address.
        
- **New Technologies, Findings, and Relevance to Wi-Fi 7 Security:**
    
    - **New Technologies:** The paper analyzes the security of VoWiFi, 3GPP IMS , EAP-AKA authentication , and IPSec tunnels.
        
    - **Threat Prediction:** This paper is extremely relevant for **threat prediction**. It provides a clear example of how vulnerabilities can exist at the _application and protocol-interaction layer_, even when the underlying Wi-Fi link is secure.
        
    - **Security Testing:** This paper provides a template for testing services that will run _over_ Wi-Fi 7. Security testers should not stop at validating WPA3. They must also perform traffic analysis and side-channel attacks (like V2) on encrypted application traffic. The new MLO feature in Wi-Fi 7 could create new, more complex side-channels for this type of traffic analysis.