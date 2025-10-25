- **Title:** Wi-Fi Security Threats - an Integrative Review
    
- **Authors:** Mario Burger, Alice Glaus
    
- **Year:** 2024 (December 17, 2024)
    
- **Summary:** This is a very recent and highly relevant integrative literature review that answers the question, "What are possible threats against Wi-Fi infrastructure?". It synthesizes findings from scientific papers published between 2017 and 2024 , categorizing modern Wi-Fi attacks like KRACK, Dragonblood (WPA3), SSID Forgery, and fragmentation attacks. The review concludes that many threats are enabled by inherent protocol vulnerabilities or, just as importantly, _implementation flaws_. It also notes that many vulnerabilities persist due to the need for backward compatibility.
    
- **Important Points:**
    
    - This review is extremely current (Dec 2024).
        
    - It summarizes and categorizes a wide range of modern attacks directly relevant to WPA2 and WPA3, including:
        
        - **Key Reinstallation Attacks (KRACK)**
            
        - **Dragonblood** (vulnerabilities in the WPA3 Dragonfly handshake)
            
        - **Fragment and Forge** (attacks on frame aggregation/fragmentation)
            
        - **Preamble Injection Attacks**
            
        - **Attacks on Protected Management Frames (PMF)**
            
        - **Side-Channel Attacks against WPA3**
            
    - **Key Finding:** Many attacks succeed due to "inherent vulnerabilities in Wi-Fi protocols or implementation flaws".
        
    - **Key Finding:** "Backward compatibility requirements" are a source of persistent vulnerabilities.
        
- **New Technologies, New Findings, and Other Important Aspects:**
    
    - **Synthesis of Modern Threats:** The paper's main finding is its comprehensive synthesis of the current Wi-Fi threat landscape, connecting the dots between multiple advanced attacks discovered in recent years.
        
    - **Call for Implementation Testing:** It makes a strong recommendation for "more rigorously defined standards," "formally verified" implementations, and "expanded testing," especially of "vendor-specific features".
        
    - **Relevance to Wi-Fi 7:** This paper is the most directly relevant to your context. It essentially provides a "to-do list" for Wi-Fi 7 security testing and threat prediction. It tells you to:
        
        1. **Test WPA3 Vigorously:** Wi-Fi 7 uses WPA3, so all known WPA3 vulnerabilities (Dragonblood, side-channel attacks) must be tested.
            
        2. **Test for Implementation Flaws:** Do not just test for protocol compliance. Actively test for "implementation flaws" and bugs in "vendor-specific features", as this is where new vulnerabilities will be found.
            
        3. **Test Backward Compatibility:** This is a critical area for threat prediction. Test all transition modes and how Wi-Fi 7 devices interact with older devices, as this is a known weak point.
            
        4. **Test New Attack Vectors:** Include tests for advanced attacks like fragmentation exploits and Preamble Injection, as these target fundamental mechanisms that also exist in Wi-Fi 7.