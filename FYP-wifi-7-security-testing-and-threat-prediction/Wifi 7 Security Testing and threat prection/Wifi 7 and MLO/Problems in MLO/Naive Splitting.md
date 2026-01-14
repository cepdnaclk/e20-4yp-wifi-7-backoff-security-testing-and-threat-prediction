# Naïve splitting in MLOs — what it is, why it’s bad, how it happens, and what to do about it

Short definition — **naïve splitting**: sending traffic across an MLO device’s multiple links using a simple, non-adaptive rule (e.g., equal packet split, pure round-robin, or fixed per-link fraction) without regard to per-link congestion, capacity, or latency. It treats links as identical resources even when they’re not.

---

## Why it matters

- MLO’s benefit comes from _using multiple links intelligently_. Naïve splitting wastes capacity: it can overload a congested link while leaving other links under-utilized, raise packet reordering and retransmissions, hurt TCP performance, and increase latency for delay-sensitive flows.
    
- In heterogeneous real deployments links differ (bandwidth, interference, load, PER, MCS). Blind splitting ignores that.
    

---

## How naïve splitting shows up (signs / symptoms)

- One or two links show high airtime/busy ratio while others are largely idle.
    
- Increased retransmissions and PER on overloaded links.
    
- Higher packet reordering at receiver (if packet-level split) and worse TCP throughput.
    
- Flow completion times for short flows rise; tail latency worsens.
    
- Controller or STA telemetry shows equal allocation weights despite different link metrics.
    

---

## Why naïve splitting happens (root causes)

1. **Simple scheduler design** — easiest implementation: equal or RR scheduling for fairness or simplicity.
    
2. **Lack of measurement inputs** — no airtime/queue/per-link metrics available to steering logic.
    
3. **Poorly tuned controller policies** — controller uses stale or averaged metrics, or applies uniform policy for all clients.
    
4. **Failures / security issues** — spoofed telemetry, jamming, or resource exhaustion can make good links appear bad (leading to a fallback to naive behavior).
    
5. **Resequencing / complexity limits** — to avoid reordering complexity, designers choose flow-level equal split as a practical compromise.
    
6. **Legacy/compatibility mode** — devices that fall back to simpler behavior for interoperability.
    

---

## Concrete impacts (technical)

- **Throughput loss**: aggregate throughput can be ≤ best single-link capacity when traffic piles onto a congested link.
    
- **Higher latency and jitter**: congested queues increase queuing delay and jitter, harming real-time traffic.
    
- **TCP inefficiency**: out-of-order and loss trigger congestion control backoff; flow throughput degrades.
    
- **Unfairness**: MLO device might monopolize airtime in ways that harm other STAs.
    

---

## How to measure and detect naive splitting

- Per-link metrics: airtime occupancy (%) over sliding window; queue depth; retransmission rate; MCS distribution; per-link throughput.
    
- Compare observed link usage to capacity estimates: if usage fraction ≠ capacity fraction and busy_ratio high on some links, suspect naive split.
    
- Correlate flow assignment with link conditions: many flows stuck on a low-capacity link is a red flag.
    
- Use IDS/WIPS rules: alert when controller weights are uniform but physical metrics differ significantly.
    

---

## How to prevent or fix naïve splitting (design recommendations)

### A. Collect better telemetry

- Measure airtime occupancy, PER, queue depth, instantaneous MCS and throughput per link at short intervals (e.g., 20–100 ms), with EWMA smoothing.
    

### B. Use congestion-aware weights (instead of naive equal split)

- **Airtime-proportional**: weight traffic by remaining airtime (1 − busy_ratio).
    
- **Capacity-weighted**: weight by estimated link capacity (BW × MCS).
    
- **Queue/latency-aware**: bias away from links with high delay/queues for latency-sensitive flows.
    

### C. Hybrid steering (packet + flow)

- **Packet-level** for best-effort bulk traffic (with resequencing buffer at MLD).
    
- **Flow-level** (affinity/stickiness) for TCP/real-time flows; reassign only after hysteresis and when imbalance persists.
    

### D. Conservative migration rules

- Use hysteresis thresholds, minimum dwell times, and grace periods to avoid thrashing on transient spikes.
    

### E. Resequencing support

- If you do packet-level splitting, implement an MLD resequencing buffer and bounded reordering windows to avoid breaking TCP.
    

### F. Secure & validate control plane

- Authenticate controller/MLD telemetry and commands; cross-validate telemetry with independent measurements to reduce spoofing risk.
    

---

## Simple scheduler sketch to avoid naive splitting

High level algorithm (run every epoch T ms):

1. For each link lll read busy_ratio[l], queue_len[l], est_capacity[l].
    
2. Smooth metrics: busy_smooth[l] = α·busy_smooth + (1−α)·busy_ratio.
    
3. Compute avail[l] = max(ε, 1 − busy_smooth[l]).
    
4. Compute weight[l] = avail[l] × est_capacity[l] (or normalize to sum=1).
    
5. For arriving packet:
    
    - If flow is latency-sensitive or TCP (flow affinity), enqueue to link with highest weight among allowed links, with migration only if imbalance > threshold.
        
    - Else (bulk): probabilistically assign packet to links according to weight[], or use token buckets per link proportional to weight[].
        

Add: resequencing at receiver for packet-level splits; min share per link to avoid starvation.

---

## Attack surface — can naive splitting be forced?

Yes — an attacker can _induce_ naive splitting indirectly by selectively jamming or spoofing metrics so the scheduler loses accurate info and reverts to simple allocation. Defenses: metric validation, anomaly detection, secure control plane, hysteresis.

---

## Quick checklist for implementers / researchers

- Don’t implement equal/round-robin as the default steering for MLO unless you have measured homogeneity.
    
- Add per-link airtime telemetry and smooth it.
    
- Implement flow stickiness + controlled migration.
    
- Provide resequencing if doing packet-level splitting.
    
- Secure and audit control/telemetry channels.
    

---

## Example illustrative numbers (intuition)

- Two links: Link A busy_ratio=0.75 (75% busy), Link B busy_ratio=0.10.
    
- Naïve split (50/50) will push half packets to Link A — causing queueing and loss.
    
- Airtime-proportional: availA=0.25, availB=0.90 → weights ≈ {A:0.22, B:0.78} → far better balance and lower loss.