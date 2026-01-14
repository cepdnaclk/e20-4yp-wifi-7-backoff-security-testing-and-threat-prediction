- **Title:** ActListener: Imperceptible Activity Surveillance by Pervasive Wireless Infrastructures
    
- **Authors:** Li Lu, Zhongjie Ba, Feng Lin, Jinsong Han, and Kui Ren
    
- **Year:** 2022
    
- **Summary:** This paper demonstrates a passive surveillance attack called "ActListener". An attacker can compromise a single, seemingly harmless WiFi device (like a smart plug) and use it to monitor human activity (like walking or gestures) in a room. This works by eavesdropping on the ambient WiFi signals from a nearby AP and analyzing how those signals are disturbed by a person's body. The attack is "imperceptible" and "black-box," meaning it works without any knowledge of the victim's device locations or security.
    
- **Important Points:**
    
    - The broadcast nature of WiFi signals leaks information about the physical environment.
        
    - This leaked "activity semantic" data can be used for surveillance.
        
    - The attack uses a neural network to "clean up" the eavesdropped signal and convert it into a high-quality data stream for activity recognition, achieving over 90% accuracy.
        
    - This threat is especially relevant as official WiFi Sensing (IEEE 802.11bf) becomes a standard.
        
- **New Technologies, Findings, and Important Aspects:**
    
    - **New Threat:** ActListener, a passive, side-channel attack that uses ambient WiFi signals for physical surveillance.
        
    - **Relevance to Wi-Fi 7 Security Testing:** Wi-Fi 7's MLO (using 2.4, 5, and 6 GHz bands simultaneously) creates a _much richer_ and more detailed signal environment for an attacker to "sense." This could make ActListener-style attacks far more accurate. Security testing for Wi-Fi 7 IoT devices and APs should investigate this side channel. Can an AP's MLO data be "listened" to for surveillance? Testers should check for information leaks in Channel State Information (CSI) or other link-management frames.
        
    - **Relevance to Threat Prediction:** This paper shifts the threat model from _data theft_ to _physical privacy theft_. Threat prediction for Wi-Fi 7 in smart homes or offices must include this class of surveillance threat. The multi-band nature of Wi-Fi 7 could be exploited to create high-resolution "WiFi radar," and this paper proves the concept is feasible.