## 1) Executive summary

This paper proposes **MLPL** (Machine-Learning-based Propagation Loss) for ns-3: a plug-in propagation-loss model that learns from real wireless traces and reproduces that environment inside ns-3, effectively enabling a **digital twin** of wireless conditions】. MLPL separates radio loss into (i) a **deterministic path-loss** piece predicted by an ML model and (ii) a **stochastic fast-fading** piece sampled from a fitted probability distribution】. It integrates Python ML (e.g., **TensorFlow** (DL library), **PyTorch** (DL library), **SciPy** (scientific Python)) into ns-3 via **ns3-ai** (ns-3 ↔ Python shared-memory bridge)】, so you can train with your traces and run ns-3 simulations that mirror real-world signal behavior. In validation, MLPL reproduces **goodput** (useful bits/sec at the application layer) more realistically than Friis or Log-distance across distances, with ML errors **< 5 dB** vs ~**15 dB** for classic models when trained on full data】.

> “The MLPL module enables the creation of a digital twin of the original wireless network environment.”】

---

## 2) What exactly MLPL is and how it works (plain English, with acronyms explained)

- **Goal.** Run ns-3 in _conditions like your real site_ by learning the environment from traces (distance, **SNR** (signal-to-noise ratio), etc.)】.
    
- **Two components.**
    
    1. **Deterministic path-loss** model: predicts average loss vs distance using **XGBoost** (gradient-boosted trees) or **SVR** (support-vector regression)】.
        
    2. **Fast-fading** model: fits **Normal/Rayleigh/Rician** distributions (statistical PDFs (probability density functions)) to the residuals; then at runtime draws random fades from a **CDF** (cumulative distribution function) via ns-3’s **EmpiricalRandomVariable**】】.
        
- **Why ns3-ai matters.** ML models live in Python, ns-3 calls them through shared memory; random sampling stays inside ns-3’s **RNG** (random-number generator) so runs are reproducible with seeds】.
    
- **Datasets you can feed it.**  
    • **Simple**: {(distance, path-loss)} after you remove fast-fading】.  
    • **Raw**: {Tx power, SNR, coordinates, antenna gain, frequency…} with pre-processing to make the model independent of Tx power】.
    

> “The module has two main components… MlPropagationLossModel in ns-3 and ns3-ai scripts to interact with external ML libraries.”】

---

## 3) Experimental setup used in the paper (so you can mirror it)

- **Data source.** Traces from the **SIMBED** project on **Fed4FIRE+** warehouse testbeds (one fixed AP, one moving station) logging distance, **SNR**, and **goodput** across multiple Tx powers】.
    
- **Training/testing runs.** Train on run **08022019_11.04.35** at **1 dBm**; test on **07022019_02.49.27** at **7 dBm**. Both at **5220 MHz/20 MHz**, with **-7 dBi** effective antenna gain (3 dBi antennas + 10 dB attenuators)】.
    
- **ns-3 validation config (Table 1).** **ns-3 3.35**, **802.11a**, Tx **7 dBm**, **5220 MHz**, **20 MHz**, **UDP** (user datagram protocol) CBR at 54 Mbit/s, pkt size 1400 B, distances 2.07–24.09 m, 404 s runtime】.
    

> “The simulation set-up is in line with the experimental set-up… two nodes – one fixed and one mobile.”】

---

## 4) Results you should internalize (what works, what doesn’t)

**A. Extrapolation (train < 10 m, test > 10 m).**  
When faced with distances it hasn’t seen, the ML curve goes almost **constant**; extrapolation is **limited**】】.

> “Both ML trace-based models predict virtually a constant value.”】

**B. Interpolation (train with gaps).**  
Even with “knowledge gaps,” ML stays within the real-data “shadow” and performs well】】.

> “Knowledge gaps were not a problem… able to learn from the previous and following values.”】

**C. Full-set (train on all).**  
ML (SVR/XGBoost) tracks real path-loss closely and captures local spikes. Classic models are “too optimistic.” ML error **< 5 dB** vs classics ~**15 dB**】】.

> “Friis and Log-distance models show a maximum error around 15 dB, while ML models have errors below 5 dB.”】

**D. End-to-end goodput in ns-3.**  
With MLPL, simulated goodput matches the distribution/spread of the real experiment better than Friis/Log-distance, which tend to condense/spike unrealistically】.

> “Neither Friis nor Log-distance… accurately reproduce the observed goodput.”】

---

