### "Multi-Link Operation with Enhanced Synchronous Channel.pdf"

- **Authors**: Wisnu Murti, Ji-Hoon Yun
- **Source**: Sensors 2021, 21, 7974

#### Summary

This paper examines Multi-Link Operation (MLO) with Enhanced Synchronous Channel Access (ESCA) in IEEE 802.11be, identifying coexistence issues with legacy devices and proposing solutions. It describes asynchronous/synchronous schemes, design variants, and challenges like unfairness. Five solutions (e.g., penalties like repicking backoff) are proposed and evaluated via simulations in dense scenarios, showing throughput/latency gains but varying coexistence. A metric evaluates both gains and coexistence.

#### Important Points

- MLO in Wi-Fi 7 targets 30 Gbps throughput and low latency for gaming/VR.
- ESCA variants [[ESCA Variant (Enhanced Spatial Channel Access)]] cause coexistence issues (e.g., MLO devices dominate legacy).
- Proposes penalties: repick backoff[[Backoff in Wi-Fi]] , double CW[[Contention Window]] , switch CW set, compensate backoff [[Backoff Compensation]] .
- Five solutions from combinations; compensating backoff best for coexistence with marginal MLO throughput loss.
- Simulations: dense single-spot/indoor; MLO gains vary; STR capability impacts coexistence.
- Metric for throughput/latency gains + coexistence in one value.
- Mobile data traffic growth (46% CAGR by 2022) drives Wi-Fi evolution.

#### New Terms and Technologies

- **Extremely High Throughput (EHT)**: Wi-Fi 7's high-throughput/low-latency goal.
- **Multi-Link Operation (MLO)**: [[MLO]] Uses multiple links for simultaneous Tx/Rx.
- **Enhanced Synchronous Channel Access (ESCA)**: Synchronous MLO variant for coordinated access.
- **Asynchronous/Synchronous Channel Access**: [[Sync vs. Async Operation]] Async: independent links; Sync: coordinated to avoid issues.
- **Coexistence Challenge**: [[Coexistence Challenge]] MLO devices unfairly accessing medium vs. legacy.
- **Backoff Penalties**: [[Backoff Penalties]]Mechanisms like repicking count, doubling CW (Contention Window) for fairness.
- **Simultaneous Transmission and Reception (STR)**: MLO capability for concurrent Tx/Rx on links.