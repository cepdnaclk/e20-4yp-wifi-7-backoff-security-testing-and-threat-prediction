---
### layout: home
### permalink: index.html

### Please update this with your repository name and title
repository-name: e20-4yp-wifi7-dt-security
title: Digital twins for Security testing and threat prediction for wifi 7 MLO operations
---

[comment]: # "This is the standard layout for the project, but you can clean this and use your own template"

# Digital Twins for Security Testing and Threat Prediction for WiFi 7 MLO Operations

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

* **Dr. Upul Jayasinghe**
    * Email: upuljm@eng.pdn.ac.lk
* **Dr. Suneth Namal**
    * Email: namal@eng.pdn.ac.lk

#### Table of Contents

1. [Abstract](#abstract)
2. [Related Works](#related-works)
3. [Methodology](#methodology)
4. [Experiment Setup and Implementation](#experiment-setup-and-implementation)
5. [Results and Key Findings](#results-and-key-findings)
6. [How to Use](#how-to-use)
7. [Conclusion](#conclusion)
8. [Links](#links)

---

## Abstract

WiFi 7 (IEEE 802.11be) introduces Multi-Link Operation (MLO) as a cornerstone feature, enabling devices to aggregate bandwidth and switch seamlessly across multiple frequency bands (2.4 GHz, 5 GHz, and 6 GHz). While MLO promises unprecedented speed and reliability, it also introduces significant complexity and a new attack surface. Traditional security testing methods, which rely on physical hardware, are expensive, difficult to scale, and insufficient for modeling the dynamic, multi-link nature of MLO. 



This project proposes the development of a **Digital Twin (DT)** framework to address this challenge. We have created a high-fidelity virtual representation of a WiFi 7 MLO network environment using **ns-3**. This DT serves a dual purpose: first, as a scalable testbed for simulating novel security threats—specifically **backoff manipulation** and **DoS attacks**; second, as a data-generation engine for training **Graph Neural Network (GNN)** models. These models are designed for real-time threat prediction, identifying anomalous MLO behavior and forecasting potential attacks before they can significantly impact the network.

---

## Related Works

Our research builds upon three primary domains:

1.  **WiFi Security:** We review the evolution of WiFi security from WEP to WPA3, investigating existing research on attacks against 802.11ax (WiFi 6) and how they adapt to MLO's multi-link dependencies.
2.  **Digital Twin Technology in Networking:** We analyze the application of Digital Twins in complex network systems (5G/6G, IoT), focusing on different DT architectures and data synchronization techniques.
3.  **ML for Network Intrusion Detection (NIDS):** We explore the use of machine learning for identifying security threats. While traditional research focuses on LSTMs or RNNs, our work specifically leverages **Graph Neural Networks (GNNs)** to model the complex temporal relationships in network packet flows and link states.

---

## Methodology

Our methodology is divided into two primary stages: **Data Generation** and **Machine Learning Modeling**.

### Phase 1: DT Framework and MLO Modeling (Data Generation)
We utilize a custom simulation environment built using **ns-3** to model a Wi-Fi 7 MLO network.
* **Simulation Scripts:** C++ scripts define the network topology, traffic patterns, and core experimental logic.
* **Attack Vector (Backoff Manipulation):** We introduced a `bias` parameter to manipulate the minimum contention window (`minCw`) of nodes:
    * **Normal (`bias = 0`):** Baseline performance.
    * **Positive Bias (`bias > 0`):** Simulates passive, less aggressive nodes.
    * **Negative Bias (`bias < 0`):** Simulates an aggressive "attack" scenario where a node monopolizes channel access.
* **KPI Collection:** A sophisticated `Tracer` collects Key Performance Indicators (KPIs) across Network, MAC, and PHY layers, saving data in a time-windowed JSON format.

### Phase 2: Anomaly Detection with Graph Neural Networks
The generated data drives a GNN-based anomaly detection model.
* **Graph Representation:** Time-series sequences of network KPIs are transformed into graphs, where nodes represent time windows and edges represent temporal relationships.
* **Model Architecture:** We implemented a custom Graph Convolutional Network (**`AttackGCN`**) in PyTorch. The model uses GCN layers to learn complex relationships between metrics over time.
* **Classification:** The model classifies network behavior into three categories: `Normal`, `Positive Bias Attack`, and `Negative Bias Attack`.

---

## Experiment Setup and Implementation

The project is engineered with a clear separation of concerns:

* **Simulation Core:** **ns-3 (Network Simulator 3)** with extended `wifi` modules for IEEE 802.11be features.
* **Data Pipeline:**
    * `backoff_dataset.py`: Handles data loading and preprocessing.
    * JSON-formatted time-series datasets containing packet traces, link latency, and throughput.
* **ML Framework:**
    * **PyTorch** and **PyTorch Geometric** for the GNN implementation.
    * `attack_model.py`: Defines the `AttackGCN` architecture.
    * `train_attack.py` & `eval.py`: Scripts for training and evaluating the model.

---

## Results and Key Findings

Our experiments have generated a high-quality dataset that exhibits clear, statistically significant differences between normal and attack scenarios.

### Quantifiable Impact of Attacks
The analysis reveals that backoff manipulation attacks have a severe and measurable impact on network performance. The most prominent indicators identified by our Digital Twin include:
* **Network Delay:** A massive increase in average network delay (`net_avg_delay_ms`).
* **Packet Loss:** Significant increase in packet loss ratio (`net_packet_loss_ratio`).
* **Throughput:** A drastic drop in aggregate network throughput (`net_throughput_mbps`).
* **Backoff Slots:** An anomalous decrease in average backoff slots (`avg_backoff_slots`), directly correlating to the aggressive nature of the attack.

### Model Performance
The GNN model demonstrates high accuracy in distinguishing between normal operations and bias-based attacks, validating the effectiveness of using graph-based learning for time-series network data.

---

## How to Use

1.  **Understand the Data:** Review `01_Data_Profiling_Report.md` and `02_Summary_Statistics.md` in the repository to understand the dataset structure.
2.  **Train the Model:**
    ```bash
    python train_attack.py
    ```
    Refer to `04_Modeling_Guide.md` for environment setup.
3.  **Evaluate Performance:**
    ```bash
    python eval.py
    ```
    This assesses the model's ability to detect attacks on unseen test data.
4.  **Extend the Research:** Modify the ns-3 scripts in the `scratch/` directory to simulate new attack vectors or network topologies.

---

## Conclusion

This project delivers a novel Digital Twin framework specifically designed for securing WiFi 7 MLO operations. By combining detailed ns-3 simulations with advanced Graph Neural Networks, we moved beyond theoretical analysis to provide a practical framework for threat detection. Our work provides a clear pathway for network administrators to proactively identify, test, and mitigate security risks in the next generation of wireless networks.

Future work will focus on expanding the DT's fidelity to include more advanced 802.11be features (like EMLSR) and exploring Federated Learning.

---

## Publications
[//]: # "Note: Uncomment each once you uploaded the files to the repository"

## Links

- [Project Repository](https://github.com/cepdnaclk/e20-4yp-wifi7-dt-security)
- [Project Page](https://cepdnaclk.github.io/e20-4yp-wifi7-dt-security)
- [Department of Computer Engineering](http://www.ce.pdn.ac.lk/)
- [University of Peradeniya](https://eng.pdn.ac.lk/)
