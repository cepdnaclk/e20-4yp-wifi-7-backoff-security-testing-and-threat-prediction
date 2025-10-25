- **Title:** Security Enhancements in Wi-Fi 7
    
- **Authors:** Arista Networks (White Paper)
    
- **Year:** 2025
    
- **Summary:** This white paper details the specific, mandatory security upgrades introduced in the Wi-Fi 7 (802.11be) standard. It explains how authentication and encryption have been strengthened to secure the new high-performance features of Wi-Fi 7, namely the Extremely High Throughput (EHT) physical layer and Multi-Link Operation (MLO). The paper also discusses the importance of backward compatibility and the challenges this poses for the client ecosystem.
    
- **Important Points:**
    
    - Wi-Fi 7 mandates new Authentication and Key Management (AKM) suites.
        
    - **SAE (Simultaneous Authentication of Equals)** authentication will use AKM 24, and **Fast Transition (FT)** authentication will use AKM 25.
        
    - These new AKMs provide authentication for a **Multi-Link Device (MLD)** as a whole, rather than for each link separately. They use a single Pairwise Master Key (PMK) across all links to keep key management synchronized.
        
    - The encryption standard is upgraded from AES CCMP-128 to **GCMP-256** (Galois/Counter Mode Protocol with 256-bit keys) for stronger data confidentiality and integrity.
        
    - To support older devices, Wi-Fi 7 Access Points will advertise support for both the new (AKM 24/25, GCMP-256) and old (AKM 8/9, CCMP-128) security protocols.
        
- **New Technologies, Findings, and Important Aspects:**
    
    - **New Technologies:** Wi-Fi 7 (802.11be), Multi-Link Operation (MLO), AKM 24, AKM 25, and GCMP-256 encryption.
        
    - **Relevance to Wi-Fi 7 Security Testing:** This paper is a foundational guide for security testing. Testers must validate the correct implementation of the new AKMs (24 and 25) and the GCMP-256 cipher. A primary focus should be on **MLO security**, ensuring that authentication is robust across all links and that the single PMK is managed securely.
        
    - **Relevance to Threat Prediction:** The paper highlights backward compatibility as a key risk. Threat prediction models should focus on **downgrade attacks**, where an attacker forces a Wi-Fi 7 client to use the older, weaker Wi-Fi 6 (AKM 8/9) security protocols to make attacks easier.