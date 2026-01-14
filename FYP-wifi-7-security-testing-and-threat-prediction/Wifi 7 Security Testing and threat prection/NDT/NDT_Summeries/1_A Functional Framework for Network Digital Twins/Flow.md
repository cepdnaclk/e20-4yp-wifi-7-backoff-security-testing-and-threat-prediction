  **Start from a real physical network**

- The system begins with a _real 6G network_ — this includes **RAN (radio)**, **core**, **transport**, and **edge** devices.
- These physical components continuously send **telemetry data** (performance, latency, usage, failures, etc.) to the twin.

  **Data Collection Framework**

- This layer gathers and harmonizes all network data from different domains (cloud → edge).
- It ensures the data is **secure, synchronized, and structured** for analysis.

  **Unified Data Repository**

- All collected data is stored here in a single, well-organized database.
- It provides consistent information for both AI models and simulations.

  **Simulation Framework**

- Multiple simulators (like **ns-3**, **OMNeT++**, and **MATLAB**) recreate the real network’s behavior virtually.
- These simulators allow safe **“what-if” testing** — trying new settings, predicting failures, or testing performance without touching the real network.

  **AI Workflow Management**

- AI engines use **Deep Learning (DL)** and **Reinforcement Learning (RL)** to analyze data.
- They train predictive models to forecast issues and optimize resources.
- The AI learns from both _real network data_ and _simulated scenarios_.

  **Federated MANO (F-MANO) Layer**

- Manages and coordinates multiple NDT instances across distributed sites.
- Handles **lifecycle management**, **AI model deployment**, and **API connections** between all layers.
- Supports **MLOps** (automated AI training/updates).

  **Zero-Touch Service & Network Management (ZSM)**

- Uses AI to automatically manage, configure, and heal the network without human intervention.
- This achieves **self-optimization** and **self-healing** — the system reacts to issues in real time.

  **Feedback Loop (Closed Loop)**

- The digital twin continuously compares **real network status** with **simulated and predicted behavior**.
- If the twin detects potential issues, it sends optimized **control decisions** back to the real network (e.g., allocate resources, change routing, adjust beamforming).
- This creates a **live synchronization** between virtual and physical worlds.

  **Dashboard and Visualization**

- A unified dashboard lets operators monitor both the physical and digital networks, view AI predictions, and visualize performance metrics.