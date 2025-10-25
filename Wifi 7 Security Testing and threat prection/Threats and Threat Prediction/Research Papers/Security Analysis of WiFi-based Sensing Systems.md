- **Title:** Security Analysis of WiFi-based Sensing Systems: Threats from Perturbation Attacks
    
- **Authors:** Hangcheng Cao, Wenbin Huang, Guowen Xu, Xianhao Chen, Ziyang He, Jingyang Hu, Hongbo Jiang, and Yuguang Fang
    
- **Year:** 2024
    
- **Summary:** This paper explores the security of Wi-Fi-based sensing systems, which use Channel State Information (CSI) and deep learning models for applications like gesture recognition and respiratory monitoring. The authors warn that these systems are vulnerable to adversarial perturbation attacks. They design and demonstrate an attack called **WiIntruder**, which is universal (black-box), robust (works over the air), and stealthy (avoids detection). The attack involves transmitting a specially crafted "perturbation" signal to contaminate the CSI data, tricking the AI model into making incorrect decisions.
    
- **Important Points:**
    
    - Wi-Fi sensing uses CSI and deep learning, but this combination is vulnerable to adversarial attacks.
        
    - The paper introduces **WiIntruder**, a practical attack that can mislead sensing systems without needing to know the specific AI model being used.
        
    - The attack is robust against real-world signal distortions and uses a Generative Adversarial Network (GAN) to create diverse attack patterns to remain stealthy.
        
    - A successful attack could reject a legitimate user's authentication or trigger false healthcare alerts.
        
- **New Technologies, Findings, and Relevance to Wi-Fi 7 Security:**
    
    - **New Technologies:** This paper details a cutting-edge attack on **Wi-Fi CSI sensing** systems that rely on **deep learning** , **GANs** , and particle swarm optimization.
        
    - **Threat Prediction:** This is **directly relevant to Wi-Fi 7 threat prediction**. Wi-Fi 7's advanced features (MLO, 320 MHz channels, more antennas) will _dramatically_ improve the accuracy and capability of Wi-Fi sensing. This paper predicts a sophisticated, hard-to-detect threat (WiIntruder) against this exact emerging use case.
        
    - **Security Testing:** This provides a clear blueprint for **security testing Wi-Fi 7 sensing applications**. Testers must go beyond network data security and actively attempt to launch over-the-air perturbation attacks to test the resilience of the AI models that interpret the Wi-Fi 7 CSI data.