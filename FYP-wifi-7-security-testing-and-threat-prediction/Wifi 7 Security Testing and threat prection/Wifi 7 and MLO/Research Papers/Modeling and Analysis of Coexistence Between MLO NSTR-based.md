
### Paper: "Modeling and Analysis of Coexistence Between MLO NSTR-based.pdf"

- **Authors**: Suhwan Jung, Seokwoo Choi, Youngkeun Yoon, Ho-kyung Son, Hyoil Kim
- **Source**: arXiv:2509.01201v1 [cs.NI] 1 Sep 2025 (Note: Date seems futuristic; possibly a typo in arXiv)

#### Summary

This paper models coexistence between Wi-Fi 7's MLO (Non-STR based) and legacy Wi-Fi using novel Markov chains for AP/non-AP MLDs. It derives transmit/collision probabilities and closed-form throughput expressions under saturated traffic. Validated via ns-3 simulator implementing STR/NSTR MLO, it reveals dynamics in inter-WLAN scenarios, showing MLO's potential but need for accurate modeling of multi-link backoff.

#### Important Points

- Wi-Fi 7 introduces MLO for higher rates/lower latency; MLDs use multiple links.
- Non-STR (NSTR) for non-AP MLDs avoids IDC interference by aligning Tx times.
- Separate Markov chains for AP/non-AP MLDs model channel access.
- Derives throughput for AP MLD, non-AP MLD, legacy devices in coexistence.
- ns-3 simulations validate model; compares STR/NSTR.
- Existing studies overlook MLO aspects; this provides standards-compliant framework.
- Focus on saturated traffic; reveals coexistence dynamics.

#### New Terms and Technologies

- **Multi-Link Operation (MLO)**: [[MLO]]Wi-Fi 7's multi-link Tx/Rx for enhanced performance.
- **Multi-Link Device (MLD)**: Device with affiliated STAs sharing upper MAC.
- **Non-STR (NSTR)**: [[STR and Non STR]]Non-simultaneous Tx/Rx mode for non-AP MLDs to avoid IDC.
- **In-Device Coexistence (IDC) [[In-Device Coexistence (IDC)]] Interference**: Self-interference in MLDs from proximate transceivers.
- **Single-Link Device (SLD)/Operation (SLO)**: Legacy Wi-Fi using one link.
- **Markov Chains (MC)**: [[Markov Chain]]cModels for MLO backoff/transmit probabilities.
- **EDCA [[Enhanced Distributed Channel Access]] (Enhanced Distributed Channel Access)**: QoS-based access in Wi-Fi.
- **ns-3 Simulator**: Tool extended for STR/NSTR MLO validation.