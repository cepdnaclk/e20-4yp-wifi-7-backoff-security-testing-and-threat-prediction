# Beam hijacking & spoofed CSI feedback — high-level overview

**Beam hijacking / spoofed CSI feedback** refers to attacks or manipulations where an adversary **influences the AP’s beamforming decisions** by providing false or biased channel information (CSI), or by otherwise altering the perceived radio environment so that the AP forms beams that benefit the attacker’s goals (e.g., reduce throughput for the victim, increase interference, or steer energy toward/away from particular directions).

Two related vectors:

1. **Spoofed CSI feedback** — the STA sends falsified or tampered CSI reports (or the control plane conveying CSI is compromised), so the AP computes suboptimal or adversary-beneficial precoding weights.
    
2. **Beam hijacking (physical manipulation)** — the attacker manipulates the RF environment (reflections, jammers, directional transmissions, or fake sounding responses) so that the AP’s beamforming is steered incorrectly (toward an attacker, away from intended STA, or to create inter-user interference).
    

Both vectors can be used alone or combined; the core effect is **misdirecting spatial energy** and degrading link performance, fairness, QoS, or confidentiality.

---

# Why this matters in Wi-Fi 7 / MLO

- Wi-Fi 7 uses **denser antenna arrays, higher order modulations (4096-QAM)**, and **multi-link beam coordination** — all of which **increase reliance on accurate CSI**.
    
- MLO and APC (multi-AP coordination) may use CSI from multiple links and APs; falsified inputs can have **systemic impact across links**.
    
- Consequences include: throughput reduction, increased latency/jitter for real-time flows, unfair airtime allocation, reduced HARQ efficiency, or localized beamformed leakage enabling eavesdropping.
    

---

# Observable indicators (for detection & forensics)

Monitor for patterns across PHY/MAC telemetry that suggest inconsistent or adversarial CSI/beam behavior:

- **Sudden/abnormal throughput drops** for a STA despite stable PHY metrics (RSSI, SNR) reported by passive sniffers.
    
- **Frequent beam reconfigurations** or unexpected precoder changes shortly after sounding events.
    
- **Discrepancy between uplink and downlink performance**: e.g., uplink power and SNR look healthy but downlink throughput low.
    
- **CSI reports that diverge significantly** from passive channel estimates (sniffers, neighboring APs).
    
- **Asymmetric cross-link anomalies** in MLO (one link repeatedly shows many beam changes or NACKs while others do not).
    
- **Spatial anomaly**: AP forms a narrow beam that benefits a previously unseen/rogue direction or device.
    
- **Timestamped correlation**: beam changes occurring immediately after specific sounding/control frames or from particular STAs.
    

Collect and correlate: per-link CSI history, sounding/report timestamps, TX/RX MCS, PER, retransmission/HARQ counts, beamforming weight histories, and passive sniffer captures of the same frames.

---

# Defensive mitigations (engineering & policy)

Design defenses in multiple layers — protocol, control plane, PHY verification, and anomaly detection.

**Protocol & control-plane**

- **Authenticate CSI/control messages** between STA ↔ AP (use cryptographic integrity and replay protection for sounding/feedback when feasible).
    
- **Secure APC/control channels** (TLS or mutually authenticated control plane) to prevent man-in-the-middle of CSI reports.
    
- **Limit exposure** of raw CSI to unauthenticated parties; expose only aggregated/obfuscated metrics where possible.
    

**PHY verification & cross-validation**

- **Cross-validate CSI** with independent measurements: compare STA-reported CSI with AP’s received uplink pilots, passive sniffer estimates, or multi-AP correlated measurements.
    
- **Reciprocity checks** for TDD links: verify that downlink and uplink channel estimates are consistent when hardware and calibration permit.
    
- **Outlier detection**: flag CSI reports that deviate strongly from historical distributions or neighbors’ reports.
    

**Robust beamforming algorithms**

- Use **robust precoding** that is less sensitive to single erroneous CSI samples (e.g., regularization, smoothing, conservative weight updates).
    
- **Hysteresis & smoothing**: require multiple consistent sounding cycles before major beam changes.
    
- **Robust optimization**: design precoders that maximize worst-case guaranteed SNR (min-max formulations) rather than point estimates.
    

**Operational & network strategies**

- **Diversity**: exploit MLO to shift critical traffic across multiple links; don’t rely on a single beam/link for QoS flows.
    
- **Randomized sounding**: occasionally randomize sounding timing or include authenticated nonce to make spoofing harder to time.
    
- **Rate limits & failover**: throttle overly frequent sounding requests or unexpected feedback patterns; failover to safe beams or fall back to more robust MCS when anomalies are detected.
    

**Anomaly detection & response**

- Implement WIDS/WIPS rules for suspicious sounding patterns, CSI inconsistency, or beam-steering anomalies.
    
- Upon detection: isolate affected STA, reduce beamforming gains, increase monitoring, or move flows to alternate APs/links.
    

---

# Detection rules / heuristics (non-actionable examples)

These are defensive heuristics you can implement and tune in your testbed/digital twin:

- Alert if a STA’s CSI magnitude/phase deviates > Xσ from historical mean across Y consecutive soundings.
    
- Alert if AP changes precoding weights by > θ within T ms without corresponding large change in measured uplink pilot.
    
- Alert if downlink PER or HARQ retransmissions spike after a sounding event but uplink SNR remains stable.
    
- Correlate across APs: if one AP reports strong channel to a direction while neighboring APs or sniffers do not, flag as suspect.  
    (Choose X, Y, θ, T empirically in your environment; these are for calibration only.)
    

---

# How to model & evaluate in a digital twin (safe research approach)

Digital twins are ideal for safe experimentation — you can simulate both benign and adversarial conditions without impacting real users.

**Modeling recommendations**

- **Create realistic CSI generation models** (multipath, mobility, noise) for each link and STA.
    
- **Simulate the sounding-feedback-control loop**: sounding frames, CSI reports, precoder computation, and beam transmissions.
    
- **Inject anomalies** in a controlled way (e.g., corrupted CSI reports, delayed feedback, spurious reflectors) to test detector sensitivity.
    
- **Measure impact** on throughput, PER, HARQ retransmissions, latency, and beam patterns across links and APs.
    
- **Test mitigations**: cryptographic authentication of feedback, smoothing/hysteresis, cross-validation, robust beamforming — compare KPIs and false positive/negative rates.
    

**Evaluation metrics**

- True/false positive detection rates for CSI spoofing.
    
- Throughput and latency degradation under attack and with mitigations.
    
- Time to detect and time to recover (TTD, TTR).
    
- Resource overhead (CPU, memory, added signaling) of defenses.
    

---

# Research & practical considerations

- **CSI privacy vs utility**: tighter protection of CSI improves security but may reduce beamforming efficiency; explore tradeoffs.
    
- **Hardware limitations**: reciprocity checks and tight timing require calibrated hardware; not all devices can support them.
    
- **ML-based detectors**: promising but vulnerable to poisoning/adversarial ML — use robust training and explainability.
    
- **Standardization angle**: consider advocating authenticated feedback primitives and integrity protection in APC/control-plane extensions for future amendments.
    
- **Operational policies**: train network operators to treat rapid, localized beam changes as potential security events and include PHY telemetry in SIEMs.
    

---

# Ethics, legality, and disclosure

- Research into these threats should follow ethical guidelines: **do not perform live attacks on networks you do not own or have explicit permission to test**.
    
- Use digital-twin and lab testbeds for evaluation.
    
- When discovering vulnerabilities, follow responsible disclosure: notify vendors and standards bodies where appropriate.
    

---

## Short takeaway (one paragraph)

**Spoofed CSI feedback and beam hijacking are high-impact, PHY-level attack surfaces in Wi-Fi 7 MLO because beamforming decisions crucially depend on accurate channel information.** Defenders should focus on cryptographic protection of control/feedback channels, cross-validation of CSI with independent measurements, robust/regularized precoding that avoids overreaction to single samples, hysteresis and smoothing in beam updates, and anomaly detection informed by multi-link telemetry. Digital twins provide a safe and effective environment to model, test, and harden systems against these manipulations.