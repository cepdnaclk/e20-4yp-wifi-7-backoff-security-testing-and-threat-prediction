- **Title:** Practical Adversarial Attack on WiFi Sensing Through Unnoticeable Communication Packet Perturbation
    
- **Authors:** Changming Li, Mingjing Xu, Yicong Du, Limin Liu, Cong Shi, Yan Wang, Hongbo Liu, Yingying Chen
    
- **Year:** 2024
    
- **Summary:** This paper demonstrates the first _physical_ and _unnoticeable_ attack against **Wi-Fi sensing systems** that rely on **deep learning (DL)**. These systems use Wi-Fi signals (specifically **Channel State Information, or CSI**) for applications like human activity recognition (e.g., detecting a fall), user authentication, or vital sign monitoring. The attack works by having a transmitter (like a compromised AP) make tiny, "unnoticeable" modifications to the **pilot symbols** in the preamble of Wi-Fi packets. These subtle changes are enough to fool the DL models at the receiver, causing them to make wrong predictions (e.g., seeing a "fall" as "watching TV") without disrupting normal data communication. The attack proved highly successful in tests (e.g., 90.47% success rate against activity recognition).
    
- **Important Points:**
    
    - The attack is physical, meaning it's done over the air and doesn't require digital access to the victim's device.
        
    - It is "unnoticeable" because it doesn't interrupt Wi-Fi communication, making it extremely stealthy.
        
    - The attack vector is the manipulation of packet preambles (pilot symbols) to poison the CSI data used by sensing applications.
        
- **New Technologies, Findings, and Relevance to Wi-Fi 7 Security:**
    
    - **New Technology:** This paper targets **Wi-Fi Sensing**, a key application set to be unlocked by the high precision and wide channels (320 MHz) of Wi-Fi 7.
        
    - **New Finding (Threat Prediction):** This paper reveals a brand-new, critical vulnerability class for Wi-Fi 7. As Wi-Fi 7 enables more advanced sensing, it also becomes vulnerable to **adversarial attacks** that target the AI/ML models powering those sensing features. The threat is no longer just about data theft (breaking WPA3) but about **data poisoning** at the physical layer to manipulate real-world outcomes (e.g., disabling a security system, faking health data).
        
    - **Security Testing:** Wi-Fi 7 security testing must now expand to include **adversarial robustness testing** for any sensing (CSI-based) feature. Testers must simulate the injection of packets with perturbed preambles to see if they can fool the system's ML models.