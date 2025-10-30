**Title:** Securing Commercial Wi-Fi-Based UAVs from Common Security Attacks


- **Authors:** Michael Hooper, Yifan Tian, Runxuan Zhou, Bin Cao, Adrian P. Lauf, Lanier Watkins, William H. Robinson, Wlajimir Alexis.
    
    
- **(Year):** 2016 (MILCOM 2016).
    
    
- **Summary:**  
    The paper shows that a popular consumer drone (Parrot Bebop) can be disrupted mid-flight via basic network attacks that exploit the **ARDiscovery** connection process and the drone’s **open Wi-Fi AP**. The authors demonstrate three **zero-day** issues—(1) buffer overflow in ARDiscovery JSON parsing, (2) denial-of-service via parallel handshake floods, and (3) **ARP cache poisoning** to sever control—then propose a **defense-in-depth** framework: OS watchdog scheduling for flight-critical tasks, strict input length filtering, and AP-level anti-spoofing for ARP.
    
    
- **Important Points:**
    
    - **Threat model:** DoS, buffer overflow, and ARP cache poisoning—each reproducibly affects in-flight behavior.
        
        
    - **Root cause:** Unauthenticated, open Wi-Fi with a discovery handshake (TCP/UDP on **port 44444**) that accepts unaudited JSON from any nearby client.
        
        
    - **Empirical evidence:** Fuzzing large JSON fields (~>931 chars) and launching hundreds of concurrent handshakes crash flight control; ARP spoofing drops the phone controller and triggers auto-land.
        
        
    - **Fix direction:** Prioritize navigation tasks (watchdog), cap/validate all inbound fields (λₐ), and bind controller/UAV IP↔MAC at the AP to drop spoofed ARP.
        
        
- **New Technologies, Findings, and Relevance to Wi-Fi 7 Security:**
    
    - **Foundational vulnerabilities still matter:** The exploits ride **classic L2/L3 issues** (ARP spoofing, resource floods) and weak input validation—attack classes that remain relevant for any Wi-Fi stack, including modern WPA3/802.11be deployments, unless explicitly mitigated. For Wi-Fi 7 testbeds, include **regression tests** against ARP spoofing, deauth/FILS abuse, and handshake flooding of app-layer discovery channels.
        
        
    - **Control-plane hardening over radio upgrades:** Even if Wi-Fi 7 improves throughput/latency, **controller↔UAV protocols** (like ARDiscovery) must add **authentication, rate-limits, and parsing guards**; otherwise higher bandwidth just amplifies DoS potential. Map their defenses to Wi-Fi 7: (i) **watchdog + QoS** to reserve CPU/network for flight loops, (ii) **strict parsers** with length/structure checks, (iii) **L2 protections** (static bindings, ARP inspection, PMF) during a bound session.
        
        
    - **Downgrade & multi-link awareness:** With Wi-Fi 7 **MLO**, ensure binding and anti-spoofing are **per-link and synchronized**; otherwise attackers may poison one link’s ARP/neighbor table to desynchronize control. Incorporate **downgrade-path tests** so older 802.11 modes can’t re-expose these Bebop-style weaknesses.
        
        
    - **Security testing implications:** Besides WPA3 correctness, test **application-layer discovery** under fuzzing and **parallel session floods**, verify **auto-land behavior** can’t be trivially induced by link tampering, and implement **AP-side filters** that drop spoofed ARP for bound peers.