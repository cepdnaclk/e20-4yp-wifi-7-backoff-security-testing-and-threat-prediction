- **Title:** Security Threats of Wireless Networks: A Survey
    
- **Authors:** Akhil Gupta
    
- **Year:** 2015
    
- **Summary:** This paper provides a general survey of security threats in wireless networks, with a focus on 3G and 4G as the contemporary technologies. It classifies attacks into five main categories: Access Control, Authentication, Availability, Confidentiality, and Integrity. It also identifies what it calls "next generation attacks," which include Man-in-the-Middle (MitM), Denial of Service (DoS), and Eavesdropping. The paper serves as a high-level overview of the fundamental security challenges inherent in wireless communication.
    
- **Important Points:**
    
    - Provides a foundational classification of wireless attacks.
        
    - Identifies the "classic" wireless attacks: DoS, MitM, and Eavesdropping.
        
    - The context is pre-Wi-Fi 6, so it does not discuss any modern protocol-specific vulnerabilities.
        
- **New Technologies, Findings & Aspects (Context: Wi-Fi 7 Security):**
    
    - **New Technologies:** This paper discusses foundational wireless networking concepts from the 2015 era.
        
    - **Relevance to Wi-Fi 7:** This paper provides the _baseline foundation_ for any security testing. While Wi-Fi 7 is new, it is still vulnerable to these fundamental attack classes.
        
    - **For Security Testing:** Wi-Fi 7 security testing must still include test cases for all these classic attacks. The goal is to determine if Wi-Fi 7's new features (Multi-Link Operation, Preamble Puncturing, 4K-QAM) make these old attacks easier or harder to execute, or if they create new variations.
        
    - **For Threat Prediction:** "Threat prediction" for Wi-Fi 7 involves asking new questions about these old attacks. For example:
        
        - **DoS:** Can an attacker launch a more effective DoS attack by just targeting one link of a Multi-Link Operation (MLO) device?
            
        - **Eavesdropping:** Does the complexity of 320 MHz channels or MLO make eavesdropping harder or provide new ways to capture fragmented data?
            
        - **MitM:** Do the new MLO link-switching mechanisms open new opportunities for an attacker to insert themselves as a MitM? This paper provides the "what to test," while the newer papers provide the "how" and "where" (e.g., in the CE phase, in coexisting spectrum, or on the IoT device itself).