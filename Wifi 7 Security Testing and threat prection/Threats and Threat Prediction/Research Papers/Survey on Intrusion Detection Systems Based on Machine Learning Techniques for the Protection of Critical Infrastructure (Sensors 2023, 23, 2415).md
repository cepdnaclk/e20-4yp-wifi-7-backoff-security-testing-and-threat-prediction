
**Title:** Survey on Intrusion Detection Systems Based on Machine Learning Techniques for the Protection of Critical Infrastructure (Sensors 2023, 23, 2415)


- **Authors:** Andrea Pinto, Luis-Carlos Herrera, Yezid Donoso, Jairo A. Gutierrez.
    
    
- **(Year):** 2023 (Published 22 February 2023).
    
    
- **Summary:**  
    A systematic survey (last five years) of **machine-learning-based intrusion detection systems (IDS)** for **Critical Infrastructure (CI)**—ICS/SCADA/DCS and IIoT contexts. It explains why CI is uniquely challenging (continuous operation, tight latency/jitter, cyber-physical coupling) and reviews ML approaches (supervised, unsupervised, reinforcement, hybrids/meta-learning), **datasets** used to train/evaluate them, and **metrics** beyond accuracy. Core message: ML-IDS are promising but evidence is often inflated by **outdated or non-representative datasets**; future work must emphasize **CI-realistic data**, **latency-aware evaluation**, and **robustness to zero-day/adversarial attacks**.
    
    
- **Important Points:**
    
    - **CI context & risks:** CI sectors (energy, water, transport, health, ICT) are mission-critical; connecting ICS to TCP/IP and IIoT expands the attack surface and raises national-security stakes.
        
        
    - **IDS taxonomy:** Host- vs network-based; signature-, anomaly-, rule-, and **hybrid** methods; ML increasingly used to improve detection quality and scalability.
        
        
    - **ML trade-offs:**
        
        - _Supervised_ → high accuracy on known attacks, weak on zero-day;
            
        - _Unsupervised_ → better on unknowns, more false positives;
            
        - _Reinforcement learning_ → promising for adaptive/real-time defense but data/time-hungry.
            
            
    - **Datasets are the bottleneck:** Heavy reliance on KDD-99/NSL-KDD or generic IT traffic hurts real-world validity; newer sets for CI/IIoT exist (e.g., SWAT, TON_IoT, Edge-IIoTset) but still suffer imbalance, limited physical-process coverage, and documentation gaps.
        
        
    - **Metrics that matter:** Accuracy alone is insufficient; emphasize **precision/recall/F1, MCC, confusion matrices, and especially detection latency** for CI operations.
        
        
    - **Design constraints for CI IDS:** Continuous availability, strict timing, protocol stability, and protection of sensors/actuators mean IDS must be lightweight, low-latency, and cyber-physically aware.
        
        
- **New Technologies, Findings, and Relevance to Wi-Fi 7 Security:**
    
    - **Foundational relevance:** Although the survey targets CI networks, its conclusions generalize to **modern Wi-Fi (including Wi-Fi 7/802.11be) industrial deployments**: do not trust headline accuracy without **CI-like datasets** and **latency-aware tests**; prefer **hybrid pipelines** and strong feature selection to balance false alarms vs. zero-day coverage.
        
        
    - **Dataset guidance for Wi-Fi 7 testbeds:** Build or adopt **RF+network+physical** datasets capturing traffic/features unique to Wi-Fi 7 (e.g., **MLO** flows, deterministic latency targets) and industrial Wi-Fi sensors/actuators; otherwise models won’t transfer from lab to plant.
        
        
    - **Evaluation upgrades:** Include **detection latency** and **jitter impact** when benchmarking IDS over high-throughput, low-latency Wi-Fi 7 links, and report **F1/MCC** rather than accuracy alone to avoid skew from class imbalance.
        
        
    - **Adversarial robustness:** Account for **adversarial ML** threats to IDS (evasion via input perturbations, model poisoning); defenses like **data augmentation, loss/architecture tweaks, and auxiliary generative models** are suggested directions. This is pertinent as Wi-Fi 7 increases bandwidth for both benign and malicious traffic.
        
        
    - **Operational guidance:** For industrial Wi-Fi (incl. Wi-Fi 7), favor **layered/hierarchical IDS** designs that combine lightweight anomaly screens at the edge with deeper analysis upstream, tuned to **CI protocol semantics** and **real-time constraints**.
        