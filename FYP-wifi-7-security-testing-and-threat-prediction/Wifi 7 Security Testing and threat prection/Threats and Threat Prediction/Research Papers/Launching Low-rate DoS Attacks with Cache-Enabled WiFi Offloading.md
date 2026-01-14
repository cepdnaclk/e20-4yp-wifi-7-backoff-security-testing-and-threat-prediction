- **Title:** Launching Low-rate DoS Attacks with Cache-Enabled WiFi Offloading
    
- **Authors:** Zhicheng Liu and Junxing Zhang
    
- **Year:** 2018
    
- **Summary:** This paper presents a new method for a **Low-rate Denial of Service (LDoS) attack**. The attack targets **cache-enabled WiFi offloading**, a feature where mobile data is offloaded from cellular to Wi-Fi and cached to improve speed and save energy. The authors found that this efficiency-focused feature creates a new vulnerability. Their attack works by inserting small amounts of attack traffic into the normal data transmission, making it subtle and hard to detect compared to a typical flood-based DoS attack. Simulations confirmed that this LDoS attack is feasible and can effectively degrade service.
    
- **Important Points:**
    
    - It highlights a common theme: new features designed for efficiency often create new, unforeseen security vulnerabilities.
        
    - The attack is a **Low-rate DoS (LDoS)**, which is stealthy and targets protocol or queueing weaknesses rather than just brute-force bandwidth saturation.
        
- **New Technologies, Findings, and Relevance to Wi-Fi 7 Security:**
    
    - **Threat Prediction (New Feature, New Threat):** This paper is a perfect case study for Wi-Fi 7. Wi-Fi 7 is defined by its new efficiency features, such as **MLO**, **Multi-RU**, and **Preamble Puncturing**. Each of these complex new mechanisms for managing and scheduling traffic is a potential target for a novel LDoS attack.
        
    - **Security Testing:** Wi-Fi 7 is being marketed for its ultra-low latency and high reliability (URLLC). An LDoS attack, as described, is the perfect weapon to break these guarantees. A "low-rate" attack might not stop a video stream, but it could introduce just enough jitter and latency to render an industrial robotics or AR/VR application unusable.
        
    - **Security Testing:** Wi-Fi 7 security testing must therefore go beyond standard penetration testing and include **protocol fuzzing** of the new MLO and Multi-RU scheduling mechanisms. Testers should try to inject subtle, malformed, or "low-rate" junk data onto one or more links to see if they can disrupt the core scheduling algorithms and break Wi-Fi 7's low-latency promises.