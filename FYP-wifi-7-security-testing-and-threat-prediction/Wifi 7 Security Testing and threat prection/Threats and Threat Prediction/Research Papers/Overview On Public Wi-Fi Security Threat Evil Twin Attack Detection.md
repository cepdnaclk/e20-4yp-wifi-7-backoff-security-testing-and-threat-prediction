- **Title:** Overview On Public Wi-Fi Security Threat Evil Twin Attack Detection
    
- **Authors:** Said Abdul Ahad Ahadi, Nitin Rakesh, Sudeep Varshney
    
- **Year:** 2020
    
- **Summary:** This paper reviews the **Evil Twin Attack (ETA)**, a classic and dangerous attack on public Wi-Fi. An attacker sets up a rogue AP with the same name (SSID) and MAC address (BSSID) as a legitimate AP. By using a stronger signal, the attacker tricks users into connecting to their rogue AP. Once connected, the attacker is in a **Man-in-the-Middle (MitM)** position, allowing them to intercept all traffic, steal passwords and financial data, or block services. The paper surveys and compares various methods to detect these attacks, including techniques based on Round-Trip Time (RTT), IP address analysis, Intrusion Detection Systems (IDS), and **Machine Learning (ML)**.
    
- **Important Points:**
    
    - An Evil Twin attack involves spoofing both the SSID and BSSID of a legitimate AP.
        
    - The primary goal is to conduct MitM attacks for data theft.
        
    - The paper provides a comprehensive overview of detection techniques, including modern ML-based approaches.
        
- **New Technologies, Findings, and Relevance to Wi-Fi 7 Security:**
    
    - **Persistent Threat:** This paper confirms that Evil Twin is a persistent threat that Wi-Fi 7 must address. While Wi-Fi 7 (with WPA3) is much more resistant to these attacks than WPA2, no system is perfect, and downgrade attacks may still be possible.
        
    - **New Finding (ML Detection):** The paper's focus on **ML for detection** is highly relevant. Centralized Wi-Fi 7 controllers (like the WiTwin in Paper 1) will almost certainly use ML-based IDS to detect threats.
        
    - **Threat Prediction (MLO Evil Twin):** Wi-Fi 7's MLO feature creates a new, unexplored vector for this old attack. An attacker could create a **"Multi-Link Evil Twin"** that spoofs all links of a legitimate MLO device. More subtly, they could create a **"Partial Evil Twin"** that _only_ spoofs one link (e.g., the 5 GHz link) of a legitimate AP (which is also on 6 GHz).
        
    - **Security Testing:** Testing must explore this "Partial Evil Twin" scenario. How does a Wi-Fi 7 MLO client respond if one of its links is hijacked? Does it drop the entire connection? Does it silently continue, feeding data to an attacker on one link? This is a critical, new test case for Wi-Fi 7.