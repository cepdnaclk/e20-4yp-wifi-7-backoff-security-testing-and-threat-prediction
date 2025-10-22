# MLO threat-model table (Wi-Fi 7 / 802.11be)

Below is a compact, actionable threat-model table you can use for study, research, or to include in a report. Each row gives the attack, how it’s done, its likely impact, suggested likelihood/severity (relative), mitigations, and practical detection signals.

|#|Attack (short)|Exploit method|Impact|Likelihood / Severity|Mitigation (practical)|Detection / Indicators|
|--:|---|---|---|--:|---|---|
|1|**Backoff manipulation / BO spoofing**|Malicious STA manipulates observed channel state or timings to desynchronize/force unfair backoff compensation (e.g., transmit short pulses to appear as busy).|Unfair medium access, throughput reduction, longer latency, possible DoS for MLO groups.|Likely / High|Validate per-link backoff behavior at AP (consistency checks); rate-limit/penalize clients that repeatedly force compensations; MAC-layer anomaly detection.|Unusual per-link BO stalls, repeated compensation events, sudden throughput drops when particular STA is present.|
|2|**Cross-link jamming / selective interference**|Jam or generate spurious signals on one link’s band (or create intermodulation) to break one stripe of an aggregated transmission.|Aggregated frame failure → wasted airtime, retransmissions; effective throughput collapse for victim MLD.|Medium / High|PHY isolation in radio hw; adaptive scheduling that can fall back to asynchronous mode; detect and avoid congested bands; directional antennas.|One link high PER / CRCs while other links OK; sudden asymmetry in SNR/RSSI across links.|
|3|**RF leakage / crosstalk exploitation**|Deliberate transmissions that exploit poor RF isolation to cause false CCA busy on other links.|Backoff misbehavior, misalignment for sync transmissions, reduced MLO gains.|Medium / Medium|Robust RF design, filtering, DPD on PAs; AP-side CCA tuning; per-link CCA validation (don’t trust single-channel CCA blindly).|Frequent false busy events, CCA inconsistencies between spectrum sensor and expected usage.|
|4|**Striped-frame targeted attack**|Interfere with or inject errors on only one link of a striped transmission so the multi-link aggregate fails.|Whole aggregated frame lost → throughput loss; attackers need only target one band.|Medium / High|FEC / per-link redundancy; ability to reassemble across remaining links or fall back to async. Per-link integrity checks and retransmit strategies.|Higher retransmit counts correlated to specific link; retransmit storms at aggregation boundaries.|
|5|**Multi-link association hijack / management-frame abuse**|Spoof/forge multi-link management frames to tear down links, force re-association, or split MLD.|Session disruption, forced re-auth, traffic interception during re-association windows.|Medium / High|Use robust management-frame protection (MFP / 802.11w+ improvements), per-link authentication, strict replay protection, signed ML association elements.|Unexpected link teardown requests, repeated association attempts, mismatched association elements across links.|
|6|**Resource-allocation flooding / QoS abuse**|Flood AP with bogus scheduling/resource requests (e.g., trigger frequent multi-link resource reservations).|Starvation of legitimate clients, scheduling overhead, AP CPU exhaustion.|Likely / Medium|Throttle/sanitize requests, quota per STA, validate resource requests, CAP (admission control).|Excessive scheduling requests from few STAs; queue/backlog spikes on AP.|
|7|**Timing / coordinate desync attack**|Create timing jitter (e.g., by injecting short pulses) that disrupts synchronization between links during compensation/alignment.|Missed sync windows, failed joint transmissions, latency spikes.|Medium / Medium|Tighter timestamping, cross-link time validation, fallback procedures when sync fails.|Increased sync failures, jitter in PHY timestamps across links.|
|8|**Side-channel / leakage data exfiltration**|Use RF leakage or out-of-band emissions to infer activity/state of other devices (covert channel).|Privacy breach, metadata leakage (who talks when); low-bandwidth exfiltration.|Low–Medium / Medium|Reduce unintended emissions (filtering/shielding), limit sensitive signaling over easily correlated patterns.|Correlation between device activity and external emissions measured by spectrum sensors.|
|9|**Firmware / driver MLO logic bugs**|Exploit implementation bugs in MLO synchronization/backoff compensation code (e.g., edge cases causing crash or privilege escalation).|Device compromise, persistent DoS, misbehavior of AP/STA.|Medium / High|Secure development, firmware signing, vulnerability scanning, fast OTA updates, fuzzing of MLO paths.|Crashes, reboots, abnormal logs; inconsistent MLO state transitions after specific frames.|
|10|**Downgrade / capability mismatch attacks**|Force MLD to drop to single-link mode or to an older standard (e.g., by spoofing capability info).|Loss of MLO performance, possibly exposing older weaker security modes.|Medium / Medium|Strict validation of capability negotiation, require authenticated capability exchange, avoid fallback without integrity checks.|Sudden shifts to single link or older rates; capability field changes during association.|

---

## Quick prioritized recommendations (practical)

1. **Per-link telemetry & cross-link consistency checks** — log per-link BO events, SNR, PER, CCA busy/idle traces; correlate to detect misbehavior.
    
2. **Treat per-link anomalies as first-class security signals** — e.g., persistently stalling BO on link X when others are idle → flag/penalize.
    
3. **Robust management-frame protection & strict association validation** — sign and validate ML association and capability elements.
    
4. **Design-in RF hygiene** — good PA linearization, band-pass filters, board-level isolation to lower attack surface for RF-based exploits.
    
5. **Fallback & resilience strategies** — allow graceful fallback from synchronous MLO to asynchronous or single-link operation when anomalies are detected, while maintaining availability.
    
6. **Testing & hardening** — fuzz MLO sequences, emulate selective jamming, and test compensation edge cases in lab.
    

---

## Detection checklist (what to monitor on AP / controller)

- Per-link BO counts, frequency of compensation events.
    
- Per-link PER/CRC and retransmission rates vs other links.
    
- Sudden asymmetry in RSSI/SNR across links of same MLD.
    
- Spike in management-frame association/teardown attempts.
    
- Unusual scheduling/resource-request patterns from single clients.
    
- PHY spectrum sensor logs showing spurious energy or narrow pulses.
    

---

## How to use this table

- For a security report: include the top 3–5 risks for your deployment and map them to concrete mitigations you can implement on APs/firmware.
    
- For testing: pick attacks 1–4 to implement in lab (backoff pulses, selective jamming, spoofed management frames) and validate detection & fallback.
    
- For design: require vendors to provide per-link telemetry and confirm RF isolation numbers (ACLR, adjacent channel leakage).
    
