- **Title:** Detection of Rogue Access Point to Prevent Evil Twin Attack in Wireless Network
    
- **Authors:** Vishwa Modi
    
- **Year:** 2017
    
- **Summary:** This paper focuses on the threat of Evil Twin attacks in open public Wi-Fi networks. An Evil Twin is a Rogue Access Point (RAP) that spoofs a legitimate AP's parameters to act as a man-in-the-middle, stealing user information. The paper proposes a client-side detection solution that does not require any action from the network administrator. The method is designed to be robust by detecting inconsistencies even when the Evil Twin spoofs the legitimate AP's MAC address, and it also checks for anomalies in external IP addresses.
    
- **Important Points:**
    
    - The focus is on client-side detection, which empowers the user's device to protect itself in untrusted environments like public hotspots.
        
    - The proposed solution aims to detect RAPs by analyzing multiple parameters, including MAC addresses (both unique and spoofed) and external IP addresses.
        
    - The goal is to alert the user to the presence of an Evil Twin and warn them to disconnect.
        
- **New Technologies, New Findings, and Other Important Aspects:**
    
    - **Administrator-Independent Detection:** The key aspect is its client-side approach, removing reliance on a managed network infrastructure.
        
    - **Multi-Factor Detection:** The proposal to combine MAC address analysis with external IP address verification creates a more resilient detection method against sophisticated spoofing.
        
    - **Relevance to Wi-Fi 7:** This principle remains highly relevant. While Wi-Fi 7 mandates WPA3, attackers will still create "open" Evil Twin networks (e.g., "Free_Airport_WiFi_7") to lure users. Furthermore, downgrade attacks could try to force a Wi-Fi 7 client into an open mode. Testing how client devices (laptops, phones) running Wi-Fi 7 radios detect and respond to these client-side anomalies (like MAC or IP mismatches) is a crucial part of security validation.