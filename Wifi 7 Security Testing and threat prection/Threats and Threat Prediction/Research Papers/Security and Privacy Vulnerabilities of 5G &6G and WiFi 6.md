- **Title:** Security and privacy vulnerabilities of 5G/6G and WiFi 6: Survey and research directions from a coexistence perspective
    
- **Authors:** Keyvan Ramezanpour, Jithin Jagannath, and Anu Jagannath
    
- **Year:** 2023 (Available online 2022)
    
- **Summary:** This survey paper explores the new security and privacy vulnerabilities that emerge from the _coexistence_ of 5G/6G cellular and Wi-Fi 6 networks. As spectrum scarcity forces these different technologies to share unlicensed bands (like 5G NR-U and Wi-Fi 6/6E in the 6 GHz band), new security challenges arise. The paper notes that current standards focus on performance (Quality of Experience) and fail to address the security implications of this shared environment, which broadens the attack surface.
    
- **Important Points:**
    
    - The main driver for these new vulnerabilities is spectrum sharing between different Radio Access Technologies (RATs), e.g., 5G NR-U and Wi-Fi 6E in the 6 GHz band.
        
    - The paper identifies a major research gap: standards are focused on _performance_ optimization (coexistence for speed) but are "ignoring" the _security_ challenges this creates.
        
    - The coexistence itself can create new threats or broaden the attack surface for existing ones.
        
- **New Technologies, Findings & Aspects (Context: Wi-Fi 7 Security):**
    
    - **New Technologies:** The paper focuses on the coexistence of 5G New Radio Unlicensed (NR-U) and Wi-Fi 6 in shared spectrum.
        
    - **Relevance to Wi-Fi 7:** This is **extremely relevant**. Wi-Fi 7 (802.11be) is designed to be the _primary_ technology operating in the 6 GHz band, which it will share with Wi-Fi 6E and potentially 5G/6G cellular technologies.
        
    - **For Security Testing:** Wi-Fi 7 security testing must therefore include "coexistence scenarios." Testers must simulate and analyze the impact of having 5G NR-U devices operating in the same band. This includes testing for cross-technology interference attacks, resource starvation, or new vectors for DoS and MitM attacks that exploit the coexistence mechanisms.
        
    - **For Threat Prediction:** The key prediction is that new, hybrid attacks will emerge. An attacker might use a 5G device to launch an attack on a Wi-Fi 7 network, or vice-versa, by exploiting the protocols that are supposed to allow them to share the spectrum fairly.