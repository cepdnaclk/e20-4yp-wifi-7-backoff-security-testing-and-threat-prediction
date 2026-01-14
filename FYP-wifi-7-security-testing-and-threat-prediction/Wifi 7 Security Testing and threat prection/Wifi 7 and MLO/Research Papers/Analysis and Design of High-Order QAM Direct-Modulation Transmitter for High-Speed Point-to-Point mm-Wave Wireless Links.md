- **Title:** Analysis and Design of High-Order QAM Direct-Modulation Transmitter for High-Speed Point-to-Point mm-Wave Wireless Links
    
- **Authors:** Huan Wang, Hossein Mohammadnezhad, and Payam Heydari
    
- **Year:** 2019
    
- **Summary:** This paper presents a novel architecture for a high-speed wireless transmitter (TX) designed for point-to-point millimeter-wave (mm-wave) links, such as those needed for 5G wireless backhaul or data center networking. The key innovation is a "direct-modulation" scheme that creates high-order Quadrature Amplitude Modulation (QAM) signals by combining multiple simpler Quadrature Phase Shift Keying (QPSK) signals. This design completely avoids the need for costly, power-hungry high-speed digital-to-analog converters (DACs), which are a significant bottleneck in conventional transmitters. The authors built and tested a prototype chip that successfully demonstrated this concept, achieving a 20 Gb/s data rate at a 115-GHz carrier frequency.
    
- **Important Points:**
    
    - The primary goal is to solve the challenge of building transmitters for ultra-high-speed (tens of Gb/s) wireless links.
        
    - The paper's main argument is that traditional DAC-based transmitters are extremely difficult and expensive to implement at such high frequencies.
        
    - The proposed solution is a DAC-less "bits-to-RF" architecture.
        
    - The core idea is to construct a 16QAM signal by using the vector addition of two separate QPSK signals with an amplitude ratio of 2.
        
    - A prototype transmitter was fabricated using a 180-nm SiGe BiCMOS process.
        
    - The prototype was successfully tested, achieving a 20 Gb/s data rate over a 20-cm distance with a 15.8 dB Error Vector Magnitude (EVM).
        
- **New Technologies, New Findings, and Other Important Aspects:**
    
    - **New Technology:** The main innovation is the **DAC-less high-order QAM direct-modulation transmitter**. It generates complex modulation by adding simpler modulation signals in the RF domain.
        
    - **New Finding:** The paper demonstrates that this DAC-less architecture is a viable and highly integrated way to achieve multi-Gb/s data rates in the mm-wave F-band (90-140 GHz).
        
    - **Relevance to Wi-Fi 7 Security Testing:** This paper has **very low direct relevance** to Wi-Fi 7 (IEEE 802.11be) security.
        
        - **Different Spectrum:** The paper's technology operates at **115 GHz**, which is in the mm-wave/sub-terahertz range. Wi-Fi 7 operates at 2.4, 5, and 6 GHz.
            
        - **Different Application:** This design is for point-to-point backhaul links, not the point-to-multipoint wireless access (WLAN) that Wi-Fi 7 provides.
            
        - **Conceptual Link Only:** The only connection is that Wi-Fi 7 also uses high-order QAM (4096-QAM). The paper's discussion of transmitter imperfections (like EVM) is a general RF concept that also applies to Wi-Fi 7, but it does not offer specific insights into Wi-Fi 7's new security-relevant features (like MLO, Multi-RU, etc.).
[[4096-QAM Modulation]]
