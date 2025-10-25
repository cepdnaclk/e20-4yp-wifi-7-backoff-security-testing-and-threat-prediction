---
layout: home
permalink: index.html

### Please update this with your repository name and title
repository-name: e20-4yp-wifi7-dt-security
title: Digital twins for Security testing and threat prediction for wifi 7 MLO operations
---

[comment]: # "This is the standard layout for the project, but you can clean this and use your own template"

# Project Title
Digital twins for Security testing and threat prediction for wifi 7 MLO operations

## Team Members

* **Dissanayake P.D.**
    * E/20/084
    * Email: e20084@eng.pdn.ac.lk
* **Nanayakkara A.T.L.**
    * E/20/262
    * Email: e20262@eng.pdn.ac.lk
* **Nilupul D.R.P.**
    * E/20/266
    * Email: e20266@eng.pdn.ac.lk


#### Supervisors

## Supervisor
* **Dr. Upul Jayasinghe**
    * Email: upuljm@eng.pdn.ac.lk
 
* **Dr. Suneth Namal**
    * Email: namal@eng.pdn.ac.lk

#### Table of content

1. [Abstract](#abstract)
2. [Related works](#related-works)
3. [Methodology](#methodology)
4. [Experiment Setup and Implementation](#experiment-setup-and-implementation)
5. [Results and Analysis](#results-and-analysis)
6. [Conclusion](#conclusion)
7. [Publications](#publications)
8. [Links](#links)

---

## Abstract

WiFi 7 (IEEE 802.11be) introduces Multi-Link Operation (MLO) as a cornerstone feature, enabling devices to aggregate bandwidth and switch seamlessly across multiple frequency bands (2.4 GHz, 5 GHz, and 6 GHz). While MLO promises unprecedented speed and reliability, it also introduces significant complexity and a new attack surface. Traditional security testing methods, which rely on physical hardware, are expensive, difficult to scale, and insufficient for modeling the dynamic, multi-link nature of MLO. This project proposes the development of a **Digital Twin (DT)** framework to address this challenge. We are creating a high-fidelity virtual representation of a WiFi 7 MLO network environment. This DT will serve a dual purpose: first, as a scalable and flexible testbed for **simulating and testing novel security threats** (such as link-specific jamming, MLO synchronization attacks, and resource exhaustion DoS); second, as a data-generation engine for **training Machine Learning (ML) models**. These models will be designed for **real-time threat prediction**, identifying anomalous MLO behavior and forecasting potential attacks before they can significantly impact the network. Our goal is to provide a robust platform for proactively securing the next generation of wireless networks.

---

## Related works

Our research builds upon three primary domains:

1.  **WiFi Security:** We review the evolution of WiFi security from WEP to WPA3, including known vulnerabilities in link aggregation, channel switching, and management frame protection. We investigate existing research on attacks against 802.11ax (WiFi 6) and how they might be adapted to exploit MLO's multi-link dependencies.
2.  **Digital Twin Technology in Networking:** We analyze the application of Digital Twins in other complex network systems, such as 5G/6G cellular networks and large-scale IoT deployments. This includes examining different DT architectures, data synchronization techniques (physical-to-virtual), and their use in 'what-if' scenario analysis.
3.  **ML for Network Intrusion Detection (NIDS):** This section explores the use of machine learning (e.g., LSTMs, GRUs, Anomaly Detection algorithms) for identifying security threats in wireless networks. We focus on models trained on time-series data (like packet flow, signal strength, and link states), which are highly relevant for predicting threats in the dynamic MLO environment.

A significant gap exists in the literature specifically addressing the unique security challenges of WiFi 7 MLO. Existing network simulators lack the fidelity to model MLO-specific attacks, and no comprehensive framework for predictive security in this context currently exists.

---

## Methodology

Our methodology is divided into four key phases:

1.  **Phase 1: DT Framework and MLO Modeling:** We will first define the essential parameters of a WiFi 7 MLO network to be twinned. This includes modeling the MLO discovery and setup process, link-state transitions (e.g., adding/dropping links), traffic splitting/aggregation logic, and QoS management across links. We will utilize a network simulator (such as **ns-3**) as the core engine, extending its 802.11be module to achieve high-fidelity MLO behavior.
2.  **Phase 2: Security Testbed Integration:** We will design and implement a suite of novel attack vectors specifically targeting MLO. Examples include:
    * **MLO De-synchronization Attack:** Spoofing management frames to force a client to drop a high-speed link.
    * **Selective Link Jamming:** Targeting a specific link (e.g., the 6 GHz link) with interference to test the network's resilience and link-switching response.
    * **MLO Resource Exhaustion:** Flooding MLO setup requests to overwhelm an Access Point's multi-link management capacity.
3.  **Phase 3: Threat Prediction Model Development:** Using the DT, we will run thousands of simulation-hours, capturing both benign traffic patterns and data from the aforementioned attack scenarios. This rich, labeled dataset (packet traces, link latency, throughput, retransmission rates) will be used to train an ML model (likely a Recurrent Neural Network or a Transformer-based model) to identify subtle precursors to an attack.
4.  **Phase 4: Validation and Analysis:** The DT's behavior and the prediction model's accuracy will be validated. We will first compare the DT's performance under benign and attack conditions against a small-scale physical testbed (using WiFi 7-capable hardware) to validate its fidelity. Second, we will evaluate the ML model's performance using standard metrics (Precision, Recall, F1-Score) on a hold-out test dataset generated by the DT.



---

## Experiment Setup and Implementation

* **Simulation Environment:** The core of our Digital Twin will be implemented using **ns-3 (Network Simulator 3)**. We will leverage and extend the existing `wifi` module to accurately model MLO features defined in IEEE 802.11be.
* **Digital Twin Interface:** A data pipeline (using **Kafka** or **MQTT**) will stream key performance indicators (KPIs) from the ns-3 simulation in real-time. A dashboard (using **Grafana**) will visualize the state of the digital twin, showing link status, throughput per link, and client distribution.
* **ML Framework:** The threat prediction models will be developed using **Python**, **TensorFlow**, and **Keras**. The models will be trained on data exported from the simulation (e.g., PCAP files, CSV logs).
* **Test Scenarios:** We will define three primary scenarios for evaluation:
    1.  **Baseline:** A 10-client, 1-AP network with mixed traffic (video, web, IoT) operating in MLO mode under normal conditions.
    2.  **Attack Scenario A (DoS):** The baseline scenario subjected to a selective link jamming attack.
    3.  **Attack Scenario B (Spoofing):** The baseline scenario subjected to an MLO link teardown spoofing attack.
* **Metrics:**
    * **Network Performance:** Aggregate Throughput, Per-Link Latency, Packet Delivery Ratio.
    * **Model Performance:** Attack Detection Accuracy, False Positive Rate, Time-to-Detect (TTD).

---

## Results and Analysis

*(This section will be populated as experiments are completed. We anticipate the following results.)*

We expect our results to demonstrate two key findings. First, the Digital Twin will accurately replicate the performance degradation of a physical WiFi 7 MLO network under various attacks. For example, we hypothesize that our selective link jamming simulation will show a 70-80% drop in aggregate throughput, forcing all MLO clients to downgrade to a single, congested 5 GHz link, a result we will aim to validate physically.

Second, we anticipate our ML-based threat prediction model will achieve high accuracy (e.S., >95% F1-score) in identifying MLO-specific attacks from the simulated time-series data. We will analyze the model's feature importance to understand *which* MLO parameters (e.g., abnormal link-switching frequency, sudden changes in one link's RSSI) are the strongest predictors of an impending attack. This analysis will not only validate our model but also provide valuable insights for developing new, proactive MLO-specific security rules and heuristics.

---

## Conclusion

This project aims to deliver a novel Digital Twin framework specifically designed for securing WiFi 7 MLO operations. By creating a high-fidelity, scalable, and safe environment, our DT enables the rigorous testing of MLO-specific vulnerabilities that are impractical to explore on physical hardware. Furthermore, the data generated by the DT proves to be a powerful asset for training advanced ML models for predictive threat analysis. Our work provides a clear pathway for network administrators and equipment vendors to proactively identify, test, and mitigate security risks in the next generation of wireless networks.

Future work will focus on expanding the DT's fidelity to include more advanced 802.11be features (like EMLSR) and exploring the use of federated learning to train threat models across multiple, distributed DT instances without sharing sensitive network data.

---

## Publications
[//]: # "Note: Uncomment each once you uploaded the files to the repository"

## Links

[//]: # ( NOTE: EDIT THIS LINKS WITH YOUR REPO DETAILS )

- [Project Repository](https://github.com/cepdnaclk/e20-4yp-wifi7-dt-security)
- [Project Page](https://cepdnaclk.github.io/e20-4yp-wifi7-dt-security)
- [Department of Computer Engineering](http://www.ce.pdn.ac.lk/)
- [University of Peradeniya](https://eng.pdn.ac.lk/)

[//]: # "Please refer this to learn more about Markdown syntax"
[//]: # "https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet"
