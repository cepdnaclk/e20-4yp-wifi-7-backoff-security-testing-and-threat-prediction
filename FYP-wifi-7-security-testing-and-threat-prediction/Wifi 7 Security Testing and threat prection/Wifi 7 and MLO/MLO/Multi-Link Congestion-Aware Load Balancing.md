# 1) What it is — short definition

**Multi-link congestion-aware load balancing** is the set of policies and mechanisms that distribute traffic (flows or packets) over the multiple PHY links available in an MLO Multi-Link Device (MLD) so that throughput/latency/reliability are maximized while avoiding congestion on any single link. It adapts allocations based on measured congestion indicators (airtime usage, queue sizes, PER, latency) rather than naive round-robin or equal splitting. [arXiv+1](https://arxiv.org/pdf/2201.07499?utm_source=chatgpt.com)

---

# 2) Why it matters

- MLO gives multiple parallel transmission opportunities (2.4/5/6 GHz or multiple channels) — but naive splitting can overload a congested link and waste capacity on under-utilized links. Congestion-aware steering improves throughput, latency and reliability. [MediaTek+1](https://www.mediatek.com/hubfs/MediaTek_Mar_2024/pdf/Wi-Fi-7-MLO-White-Paper-WF7MLOWP0622.pdf?hsLang=en&utm_source=chatgpt.com)
    
- Empirical/simulation studies show congestion-aware strategies outperform uniform or static splitting under heavy loads and in dense deployments. [arXiv+1](https://arxiv.org/pdf/2201.07499?utm_source=chatgpt.com)
    

---

# 3) Key measurements / inputs for decisions

Use these real-time metrics per link (measured at AP or MLD):

- **Airtime occupancy** (fraction of time channel is busy) — primary indicator of congestion. [gnan.ece.gatech.edu](https://gnan.ece.gatech.edu/archive/ching_lun_icmlcn24.pdf?utm_source=chatgpt.com)
    
- **MAC/PHY data rate & MCS**, and **estimated link capacity**. [MediaTek](https://www.mediatek.com/hubfs/MediaTek_Mar_2024/pdf/Wi-Fi-7-MLO-White-Paper-WF7MLOWP0622.pdf?hsLang=en&utm_source=chatgpt.com)
    
- **Queue length / buffer occupancy** (packets/bytes waiting to transmit).
    
- **Packet error rate (PER)** or retransmission count.
    
- **One-way latency / RTT** (for delay-sensitive traffic).
    
- **Active flows / flow sizes** (for flow-level steering).
    
- **Link availability / channel conditions** (rapid fading, interference spikes).
    

---

# 4) Classes of load-balancing policies

(ordered roughly from simplest → most complex)

1. **Uniform (Equal split)**
    
    - Split packets/MPDUs evenly across active links. Simple but insensitive to congestion. (Baseline) [arXiv](https://arxiv.org/pdf/2304.01693?utm_source=chatgpt.com)
        
2. **Round-Robin / Packet-level round robin**
    
    - Cyclically send packets on links. Low overhead; can cause reordering and poor performance if links differ.
        
3. **Capacity-weighted split**
    
    - Assign fraction proportional to estimated raw link capacity (MCS × bandwidth). Good when capacity differences dominate.
        
4. **Airtime-proportional (congestion-aware)** — common effective policy
    
    - Allocate traffic proportionally to each link’s **remaining available airtime** (or inversely to measured occupancy). Popular in MCAB/MCAB-like proposals: if link l has remaining airtime R_l, send fraction ∝ R_l. This directly targets medium congestion. [gnan.ece.gatech.edu+1](https://gnan.ece.gatech.edu/archive/ching_lun_icmlcn24.pdf?utm_source=chatgpt.com)
        
5. **Queue-aware / delay-aware**
    
    - Prefer links with lower queueing delay; useful for low-latency flows.
        
6. **Flow-level steering with affinity & stickiness**
    
    - Assign entire flows to particular links (to avoid reordering) using congestion signals; reassign when imbalance detected.
        
7. **Learning / Adaptive (DRL, model-free)**
    
    - Train policy to maximize long-term utility (throughput, latency fairness). Good in complex, variable environments but heavier runtime and training cost. [gnan.ece.gatech.edu](https://gnan.ece.gatech.edu/archive/ching_lun_icmlcn24.pdf?utm_source=chatgpt.com)
        

---

# 5) Packet- vs Flow-level steering (tradeoffs)

- **Packet-level** (fine granularity): better load balancing and link utilization, but causes **out-of-order delivery** at receiver and higher reassembly complexity (may require resequencing at MLD layer). Good for bulk traffic where order not critical (or when MLD handles resequencing).
    
- **Flow-level** (per 5-tuple): avoids reordering, simpler TCP behavior, but can create imbalance when many large flows map to the same link — needs reassign triggers and flow migration logic.  
    Many practical designs use **hybrid**: packet-level for best-effort/bulk, flow-level for latency-sensitive/TCP flows. [arXiv](https://arxiv.org/pdf/2201.07499?utm_source=chatgpt.com)
    

---

# 6) Simple congestion-aware algorithm (airtime-proportional) — explanation + pseudocode

Idea: each scheduling epoch (e.g., every 10–50 ms), measure per-link **busy_ratio** (airtime occupancy). Compute **remaining airtime fraction** and allocate next N packets proportionally.

Pseudocode (packet scheduler at AP or MLD transmitter):

`Inputs per link l: busy_ratio[l] in [0,1]  (measured) Compute avail[l] = max(ε, 1 - busy_ratio[l])   # remaining airtime sum_avail = Σ_l avail[l]  For each packet arrival:   For each link l: weight[l] = avail[l] / sum_avail   # To avoid per-packet float ops, maintain probabilistic or token buckets:   Enqueue packet to link with probability weight[l]`

Improvements:

- Use **exponential smoothing** for busy_ratio to avoid oscillation.
    
- Reserve minimum share per link to prevent starvation.
    
- For TCP/latency flows, bias weight by RTT or queue depth.
    

This policy is essentially the **MCAB / MCAB-like** approach in literature (traffic steering proportional to remaining channel airtime). [gnan.ece.gatech.edu+1](https://gnan.ece.gatech.edu/archive/ching_lun_icmlcn24.pdf?utm_source=chatgpt.com)

---

# 7) Flow migration & stickiness rules

When reassigning a flow from link A to B, use:

- **Min flow duration** (don't move short flows).
    
- **Hysteresis thresholds** (only migrate when imbalance exceeds threshold).
    
- **Grace period** for TCP to avoid thrashing.
    
- **Seamless migration** requires sequence number / resequencing support or per-flow tunneling between MLD endpoints.
    

---

# 8) Centralized vs Distributed decision points

- **AP-centric / Central controller** (e.g., in enterprise or APC): controller aggregates per-AP/link airtime stats and computes steering for multiple APs and clients. Easier global optima, but needs low-latency control plane. [Cisco Meraki Documentation](https://documentation.meraki.com/MR/Wi-Fi_Basics_and_Best_Practices/Wi-Fi_7_%28802.11be%29_Technical_Guide?utm_source=chatgpt.com)
    
- **Client/MLD-local** (distributed in STA/MLD): each device makes decisions from local link measurements — faster, but less global view and potential oscillation.
    
- **Hybrid**: controller suggests long-term weights; MLD adjusts locally for short term.
    

---

# 9) Metrics to evaluate

- **Aggregate throughput** (sum over links / flows).
    
- **Per-flow latency / 95th percentile** (for interactive flows).
    
- **Packet loss / retransmissions (PER)**.
    
- **Fairness index** (Jain’s fairness).
    
- **Airtime utilization** (how well idle airtime is used).
    
- **Flow completion time (FCT)** for short flows.  
    Research papers use these to compare uniform vs congestion-aware policies. [arXiv+1](https://arxiv.org/pdf/2201.07499?utm_source=chatgpt.com)
    

---

# 10) Practical considerations & pitfalls

- **Measurement noise & reaction speed**: airtime and PER fluctuate; over-reactive steering causes oscillations. Use smoothing and conservative migration.
    
- **Out-of-order & TCP performance**: packet-level splitting may harm TCP unless resequencing is supported. Ensure MLD resequencing buffer or use flow affinity for TCP. [arXiv](https://arxiv.org/pdf/2201.07499?utm_source=chatgpt.com)
    
- **Hidden terminals & cross-link interference**: links may not be independent; airtime on one link can affect another via cross-channel interference — need joint-awareness or APC.
    
- **Fairness across STAs**: maximizing a single STA’s multi-link throughput must not starve others; include fairness constraints.
    
- **Control overhead**: per-link telemetry and steering commands add control traffic; design lightweight signalling.
    

---

# 11) Advanced directions (research / state of art)

- **Model-free dynamic traffic steering** (reinforcement learning) that adapts to unknown environments and traffic patterns. Promising but needs training and safety/hardness mitigations. [gnan.ece.gatech.edu](https://gnan.ece.gatech.edu/archive/ching_lun_icmlcn24.pdf?utm_source=chatgpt.com)
    
- **Joint APC + MLO optimization**: coordinate across APs to achieve system-wide load balancing (especially in dense deployments). [arXiv+1](https://arxiv.org/pdf/2201.07499?utm_source=chatgpt.com)
    
- **Airtime fairness + congestion awareness**: combine airtime budgeting with congestion metrics to maintain fairness among legacy and MLO STAs. [arXiv](https://arxiv.org/pdf/2304.01693?utm_source=chatgpt.com)
    

---

# 12) Quick example: simulation/experiment setup you can run

- Topology: 1 AP (MLO AP with 2 links) + 10 STAs (MLO capable).
    
- Compare policies: Uniform, Capacity-weighted, Airtime-proportional (congestion-aware), Flow-level sticky.
    
- Traffic: mix of long TCP bulk flows + short web-like flows + UDP real-time flows.
    
- Metrics: aggregate throughput, 95th latency, FCT, retransmissions.  
    Expected: airtime-proportional policy gives higher aggregate throughput and lower tail latency under heavy load. [arXiv+1](https://arxiv.org/pdf/2304.01693?utm_source=chatgpt.com)
    

---

# 13) Short checklist to implement this in firmware/software

1. Collect per-link metrics (airtime occupancy, queue depth, PER) every T ms (e.g., 20–100 ms).
    
2. Smooth metrics (EWMA).
    
3. Compute link weights (avail airtime or capacity-normalized).
    
4. Scheduler: probabilistic packet assignment or token bucket per link using weights.
    
5. Handle flow affinity for TCP: per-flow assignment + migration triggers.
    
6. Add hysteresis and minimum allocation to avoid oscillation.
    
7. Monitor KPIs and adapt T and smoothing constants.
    

---

# 14) References & further reading (selected)

- López-Raventós et al., _Multi-link Operation in IEEE 802.11be WLANs_ — review & load balancing discussion. [arXiv](https://arxiv.org/pdf/2201.07499?utm_source=chatgpt.com)
    
- Alsakati et al., _Performance of 802.11be with MLO_ — compares congestion-aware and uniform policies. [arXiv](https://arxiv.org/pdf/2304.01693?utm_source=chatgpt.com)
    
- Tai et al., _Model-Free Dynamic Traffic Steering for MLO_ — RL/ model-free steering approaches. [gnan.ece.gatech.edu](https://gnan.ece.gatech.edu/archive/ching_lun_icmlcn24.pdf?utm_source=chatgpt.com)
    
- MediaTek / vendor whitepapers on MLO basics and capacity claims. [MediaTek+1](https://www.mediatek.com/hubfs/MediaTek_Mar_2024/pdf/Wi-Fi-7-MLO-White-Paper-WF7MLOWP0622.pdf?hsLang=en&utm_source=chatgpt.com)