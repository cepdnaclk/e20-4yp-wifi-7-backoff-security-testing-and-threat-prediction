### Paper 1: Survey on Intrusion Detection Systems Based on Machine Learning

- **Title:** Survey on Intrusion Detection Systems Based on Machine Learning Techniques for the Protection of Critical Infrastructure
    
- **Authors:** Andrea Pinto, Luis-Carlos Herrera, Yezid Donoso, and Jairo A. Gutierrez
    
- **Year:** 2023
    
- **Summary:** This paper surveys the latest research on Intrusion Detection Systems (IDSs) that utilize machine learning (ML) to defend Critical Infrastructure (CI). It highlights that as industrial systems (like SCADA) become more connected to the internet and the Industrial Internet of Things (IIoT), their attack surface expands significantly. The article reviews different ML approaches—supervised, unsupervised, and reinforcement learning—used to detect sophisticated cyber-attacks. It also points out that a major challenge remains in detecting zero-day attacks and in the practical implementation of these complex models in real-world scenarios.
    
- **Important Points:**
    
    - The paper frames security as a response to the "expanded attack surface" caused by new connection technologies (like IIoT).
        
    - It categorizes ML-based IDS approaches:
        
        - **Supervised Learning:** Effective at detecting known attacks with high accuracy but poor at finding new, "zero-day" threats.
            
        - **Unsupervised Learning:** Better at identifying unknown anomalies and zero-day attacks but typically suffers from a higher rate of false positives.
            
        - **Reinforcement Learning:** A newer technique that can adapt to complex threats but requires significant learning time.
            
    - A significant problem in the field is that many ML models are trained on outdated datasets (e.g., KDD 99) that do not represent modern attack scenarios.
        
- **New Technologies, Findings & Aspects (Context: Wi-Fi 7 Security):**
    
    - **New Technologies:** The core technology discussed is the application of advanced ML and deep learning models to network traffic for intrusion detection.
        
    - **Relevance to Wi-Fi 7:** This paper is highly relevant to **threat prediction**. Wi-Fi 7's new features (Multi-Link Operation, 320 MHz channels, 4K-QAM) create a new, more complex attack surface, just as IIoT did for critical infrastructure.[[4096-QAM Modulation]]
        
    - **For Security Testing:** This suggests that Wi-Fi 7 security testing should not just look for known vulnerabilities but must also include **anomaly-based threat detection**.
        
    - **For Threat Prediction:** An ML-based IDS, particularly one using unsupervised learning, will be essential for identifying novel attacks that exploit Wi-Fi 7's new protocols. The challenge will be to create new, relevant datasets that capture Wi-Fi 7-specific traffic and attacks.