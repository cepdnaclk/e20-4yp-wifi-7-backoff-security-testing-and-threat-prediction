- **Title:** ETGuard: Detecting D2D attacks using wireless Evil Twins
    
- **Authors:** Vineeta Jain, Vijay Laxmi, Manoj Singh Gaur, Mohamed Mosbah
    
- **Year:** 2019
    
- **Summary:** This paper introduces ETGuard, a real-time system to detect and prevent Evil Twin (ET) attacks. It demonstrates a novel Device-to-Device (D2D) attack where an ET can infect an Android device _before_ the device fully associates or relays any network traffic. ETGuard works as a client-server mechanism that passively fingerprints beacon frames from access points to identify ETs. Once detected, it actively prevents clients from connecting by sending deauthentication frames.
    
- **Important Points:**
    
    - It identifies a new pre-association D2D attack vector targeting Android devices via Evil Twins, a shift from traditional post-association attacks like sniffing.
        
    - The proposed ETGuard system is designed to be practical: it's passive, automated, requires no special hardware or protocol changes, and doesn't rely on network-specific parameters like RTT.
        
    - Detection is based on constructing fingerprints from the beacon frames that APs transmit periodically.
        
    - The system was validated with high accuracy and no false negatives against 12 different ET scenarios (hardware, software, and mobile hotspot-based).
        
- **New Technologies, New Findings, and Other Important Aspects:**
    
    - **ETGuard System:** This is the new technology proposed—a pre-association, fingerprinting-based ET detection and prevention system.
        
    - **Pre-association D2D Attack:** The identification of this new attack vector, where a device is compromised before the network connection is even established, is a significant finding.
        
    - **Relevance to Wi-Fi 7:** Evil Twin attacks remain a severe threat. Wi-Fi 7's complexity (e.g., Multi-Link Operation, 320 MHz channels) may offer new avenues for fingerprinting. A system like ETGuard could be adapted to fingerprint the unique radio characteristics of a legitimate Wi-Fi 7 AP, making spoofing more difficult. The concept of _pre-association detection_ is vital for testing, as it aims to stop an attack before any sensitive data (like a WPA3 handshake) is exchanged.