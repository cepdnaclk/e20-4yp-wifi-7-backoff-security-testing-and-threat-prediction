**What it is:** capturing legitimate frames and retransmitting them later to repeat actions or bypass certain protections.  
**Impact:** replayed control or data frames can cause unintended behavior; depending on protections, may be mitigated by replay counters.  
**Indicators:** duplicate frames with older timestamps or sequence numbers.  
**Mitigation:** ensure protocol uses nonces/replay counters (WPA2/3 do), apply patches.