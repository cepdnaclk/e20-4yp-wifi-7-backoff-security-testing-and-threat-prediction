# Comprehensive Project Summary for Research Paper

## 1. Project Title

**A Network Digital Twin for Real-Time Backoff Manipulation Attack Detection in Wi-Fi 7 Multi-Link Operation (MLO)**

---

## 2. Introduction & Research Objectives

### 2.1. The Research Gap: From Performance Anomaly to Security Threat
The introduction of Wi-Fi 7 (802.11be) and its headline feature, Multi-Link Operation (MLO), marks a paradigm shift in wireless networking. However, existing academic literature is dangerously fragmented. One body of research focuses on optimizing MLO for performance, while a separate security community concentrates on legacy threats, largely ignoring the new, complex attack surface introduced by MLO's MAC-layer coordination logic.

This project addresses a critical blind spot identified in the literature: the weaponization of MLO performance-tuning mechanisms. Specifically, it reframes documented performance anomalies like **"backoff overflow"** and fairness issues from **"free rides"** not as simple bugs, but as sophisticated, state-based attack vectors for Denial of Service (DoS) or unfair channel acquisition.

### 2.2. Problem Statement: Detecting Backoff Manipulation
The central threat explored is the **backoff manipulation attack**. In this scenario, a malicious actor intentionally exploits the MLO backoff compensation rules to desynchronize its internal counters, repeatedly inducing backoff overflow and gaining perpetual "free rides." This allows the attacker to collapse the fairness of the network and dominate the channel, starving other legitimate users. Traditional Intrusion Detection Systems (IDS) and static analysis tools are ill-equipped to detect such state-based, logic-oriented exploits.

### 2.3. Proposed Solution: A Security-Focused Network Digital Twin (NDT)
To address this, the project implements a production-grade **Network Digital Twin (NDT)**. Unlike performance-oriented twins, this NDT is explicitly designed for security validation. It creates a continuously synchronized, high-fidelity replica of the Wi-Fi 7 MLO network, providing a safe and observable sandbox to:
1.  **Replicate and Model:** Accurately replicate the intricate state of multi-link contention and execute adversarial backoff manipulation scenarios that are too risky for a live network.
2.  **Generate High-Fidelity Data:** Create the crucial, labeled datasets of both benign and adversarial MLO behavior necessary for training robust machine learning models.
3.  **Detect and Predict:** Use the twin's data to train a **Graph Convolutional Network (GCN)** capable of identifying the subtle, temporal signatures of backoff attacks in real-time.

The core of the NDT's intelligence is the GCN, which is uniquely suited to model the temporal graph structure of network telemetry, making it ideal for this detection task.

### 2.4. Research Questions (from `docs/BLUEPRINT.md`)
The project was designed to answer the following research questions:
-   **RQ1:** Can a GCN-based NDT predict per-flow delay, loss, and jitter for Wi-Fi 7 MLO scenarios with acceptable error?
-   **RQ2:** Can security analytics reliably detect MLO backoff manipulation patterns in real-time?
-   **RQ3:** Can a closed-loop policy engine restore fairness under attack while maintaining stability? (Future Work)
-   **RQ4:** What is the end-to-end latency of the observe → decide → act → learn loop?

---

## 3. System Architecture

The platform is a multi-component, containerized system orchestrated by Docker, Docker Compose, and Containerlab. It follows a modular, streaming architecture.

### 3.1. High-Level Data Flow
The architecture can be summarized in the following flow diagram:

```
NS-3 Simulation (Physical/Simulated Layer)
      │
      ▼
telemetry.jsonl (Raw Data Artifact)
      │
      ▼
Exporter (Data Ingestion)
      │
      ▼
Redpanda (Kafka API - Message Bus)
      │
      ├──────────────────────────────┐
      ▼                              ▼
 Harmonizer (Raw Metrics Sink)  Windowizer (Real-time ML Preprocessing)
      │                              │
      ▼                              ▼
 TimescaleDB (UDR)          Kafka Topic: wifi7.ml.windowed_features.v1
(for historical analysis)          │
      │                              │
      │                              ▼
      │                       GCN Detector (AI/ML Inference)
      │                              │
      │                              ▼
      └──────────────┬───────────────┘
                     │
                     ▼
          TimescaleDB (UDR) - Table: gcn_predictions
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
 Grafana Dashboard       Custom Web Dashboard
(Analytics & Monitoring)   (Real-time UX & Control)
```

### 3.2. Component Breakdown

#### 3.2.1. Simulation (ns-3)
-   **Technology:** **ns-3 (v3.46.1)**, a discrete-event network simulator.
-   **Purpose:** To generate realistic Wi-Fi 7 MLO network traffic. It simulates various scenarios, forming the basis for the digital twin's data.
-   **Scenarios Simulated:**
    *   **Normal:** Baseline Wi-Fi 7 MLO behavior without any attacks.
    *   **Positive Attack:** A malicious node uses an artificially high backoff bias (e.g., +5000), leading to channel starvation and a significant drop in its own throughput (−84%).
    *   **Negative Attack:** A malicious node uses an artificially low backoff bias (e.g., -5000), leading to aggressive, unfair channel access and a drop in overall network throughput (−44%).
-   **Output:** Per-experiment telemetry data is written to a `telemetry.jsonl` file.

#### 3.2.2. Telemetry Pipeline (The Data Fabric)
-   **Exporter:** A Python service that reads the `telemetry.jsonl` file and publishes each line as a message to a Kafka topic. It maintains state to avoid duplicate processing.
-   **Redpanda (Kafka API):** A high-throughput, Kafka-compatible message broker that serves as the central nervous system for the real-time data flow.
-   **Harmonizer:** A service that consumes from the main telemetry topic and writes the raw metrics into a `metrics` table in TimescaleDB. This data is used for historical analysis and visualization in Grafana.
-   **Windowizer:** A crucial real-time preprocessing service. It consumes the raw telemetry stream, aggregates metrics into **256-sample windows**, converts cumulative counters into deltas, and publishes these fixed-size segments to a new Kafka topic for consumption by the GCN model.

#### 3.2.3. GCN Attack Detector (The "Twin's Brain")
-   **Purpose:** The core of the threat detection system. This service consumes the windowed segments from the Windowizer.
-   **Process:**
    1.  **Model Loading:** Loads a pre-trained GCN model from the Model Registry. It supports hot-reloading for zero-downtime model updates.
    2.  **Graph Construction:** For each 256-window segment, it constructs a **temporal chain graph**, where each window is a node and edges connect adjacent nodes in time (t ↔ t+1).
    3.  **Feature Processing:** Applies z-score normalization using a pre-fitted `StandardScaler`.
    4.  **Inference:** Executes the GCN model's forward pass on the graph to get a prediction (0 for Normal, 1 for Attack) and a confidence score.
-   **Output:** Predictions are written to the `gcn_predictions` table in TimescaleDB and also published to a dedicated Kafka topic for other real-time services.

#### 3.2.4. Data Storage (Unified Data Repository - UDR)
-   **Technology:** **TimescaleDB** (a PostgreSQL extension for time-series data).
-   **Schema:** Contains two primary hypertables:
    *   `metrics`: Stores the raw, harmonized telemetry data.
    *   `gcn_predictions`: Stores the output from the GCN Detector, including prediction, confidence, and model version.

#### 3.2.5. Visualization & User Interface
-   **Grafana:** A powerful analytics and monitoring dashboard. The project includes a pre-built, 38-panel unified dashboard that visualizes the entire pipeline, from raw metrics and experiment history to GCN model performance (F1, accuracy, etc.) and prediction timelines.
-   **Custom Web Dashboard:** A bespoke, full-stack application (React + FastAPI) providing a highly polished, real-time user experience on port 8888. It features a "Soft UI / Neumorphism" design and includes six sections for monitoring the pipeline, analyzing experiments, and assessing model intelligence.

#### 3.2.6. Orchestration & Tooling
-   **Containerlab:** Defines the core infrastructure topology, including the database, Kafka broker, and Grafana.
-   **Docker & Docker Compose:** All services are containerized for portability and consistent deployments.
-   **Makefile:** A comprehensive `Makefile` provides a high-level command interface for building, running, testing, and managing all components of the project (e.g., `make up`, `make run-mlo-exp`, `make gcn-up`).

---

## 4. The Graph Neural Network (GCN) Model

### 4.1. Model Architecture
-   **Type:** 2-layer Graph Convolutional Network (GCN).
-   **Input:** A temporal graph constructed from a segment of 256 consecutive time windows. Each node (window) has **13 features**.
-   **Output:** A binary classification (Normal/Attack) with an associated confidence score.
-   **Rationale:** A GCN is used because it can effectively learn from the graph structure of the data, capturing the temporal relationships between network metrics over time, which is essential for detecting subtle attack patterns.

### 4.2. Features
The model uses 13 key features extracted from the network telemetry for each time window:
1.  `backoff_slots` (Average)
2.  `throughput_mbps`
3.  `packet_loss_rate`
4.  `delay_ms` (Average)
5.  `channel_busy_ratio`
6.  `retry_count` (Delta)
7.  `link1_usage`
8.  `link2_usage`
9.  `mcs_index`
10. `rssi_dbm`
11. `snr_db`
12. `queue_depth`
13. `jitter_ms` (Average)

*Note: Cumulative counters like `retry_count` are converted to deltas by the Windowizer before being fed to the model.*

### 4.3. Training & Model Versioning
-   **Model v1.0.0 Issue:** The initial model suffered from a severe data distribution mismatch. It was trained on a dataset that did not reflect the characteristics of the live pipeline data, causing it to have a 100% false positive rate (classifying all traffic as attacks).
-   **Model v2.0.0 (Production):** To fix this, a new model was trained on a dataset generated directly from the project's own simulation pipeline.
    -   **Dataset:** A balanced set of **284 scenarios** (50% normal, 50% attack) covering a wide range of positive and negative backoff biases.
    -   **Result:** This model (`v2.0.0`) is the current production model and demonstrates accurate detection on pipeline-generated data.
-   **Model Registry:** A file-based registry at `twin/registry/gcn/` stores all model versions. Each version includes the PyTorch model file (`best_model.pt`), the scaler (`scaler.json`), and configuration files. A `current` symlink points to the active model, enabling hot-reloading.

---

## 5. Summary for a Research Paper Agent

For an AI agent tasked with writing a paper, here is the distilled information:

-   **Title:** "A Graph-based Digital Twin for Real-Time Detection of Backoff Manipulation Attacks in Wi-Fi 7"
-   **Novelty/Hook:** This research bridges a critical gap in wireless security by reframing MLO "performance anomalies" (like backoff overflow) as weaponizable, state-based security exploits. It pioneers the use of a security-focused Network Digital Twin to model and detect these novel threats, moving beyond the legacy threat analysis and performance optimization that currently dominate the literature.
-   **Abstract:** Proposes a Network Digital Twin (NDT) using a Graph Convolutional Network (GCN) to detect sophisticated backoff manipulation attacks in Wi-Fi 7 Multi-Link Operation (MLO) networks. By modeling and simulating the subtle MAC-layer coordination logic, the system learns to identify adversarial behavior that exploits MLO's backoff compensation mechanism. The system uses a real-time data pipeline with ns-3 simulations, Kafka, and TimescaleDB. The GCN model analyzes temporal graphs of network telemetry to achieve high-accuracy threat detection. This work contributes a complete, open-source, containerized platform for reproducible research into this new class of state-based, logical attacks.
-   **Methodology:**
    1.  **Threat Model:** Define the backoff manipulation attack, where an adversary exploits MLO's "free ride" and "backoff overflow" phenomena to gain unfair channel access.
    2.  **Simulation:** Use ns-3 to generate Wi-Fi 7 MLO data for normal traffic and two types of backoff attacks (positive and negative bias), explicitly simulating the threat model.
    3.  **Data Pipeline:** Stream telemetry through a Kafka-based pipeline. A "Windowizer" service segments the data into 256-sample temporal windows, creating fixed-size inputs for the ML model.
    4.  **Model:** Employ a 2-layer GCN. For each segment, construct a temporal chain graph where nodes are time windows and edges connect adjacent windows. The graph structure allows the model to learn the temporal signatures of the attack.
    5.  **Training:** Train the GCN as a binary classifier (Normal vs. Attack) on a balanced dataset generated by the ns-3 pipeline to ensure no data distribution mismatch.
    6.  **Inference & Detection:** Deploy the trained model as a real-time service that consumes windowed data and flags backoff manipulation attacks, storing predictions in a database and visualizing them on dashboards.
-   **Results:** The system successfully differentiates between normal traffic and backoff manipulation attacks. The positive attack (+5000 bias) resulted in a +285x increase in backoff slots and an 84% drop in throughput for the malicious node. The negative attack (-5000 bias) resulted in a 56% decrease in backoff slots, indicating aggressive channel capture. The GCN model, trained on pipeline-generated data, effectively identifies these anomalies in real-time. The end-to-end latency from event to prediction is under 40 seconds, dominated by the necessary windowing buffer.
-   **Conclusion:** The NDT approach, specifically one designed for security validation, is an effective and necessary method for detecting complex, logic-based attacks like backoff manipulation in Wi-Fi 7. The platform developed serves as a foundational tool for security research into the emerging threats of next-generation wireless protocols.
