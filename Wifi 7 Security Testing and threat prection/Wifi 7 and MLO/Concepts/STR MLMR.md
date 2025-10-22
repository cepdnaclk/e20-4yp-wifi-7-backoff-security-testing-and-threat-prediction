## 1. **STR (Simultaneous Transmit and Receive)**

- **Definition:** A device can **transmit and receive at the same time** on **one or multiple links**.
    
- **Implications:**
    
    - Requires either multiple radios or full-duplex capability.
        
    - Reduces latency for bidirectional traffic.
        
    - Increases aggregate throughput in MLO.
        
- **Relation to MLO:**
    
    - STR allows a multi-link device to schedule **overlapping transmissions** across links asynchronously.
        
    - Non-STR devices must schedule Tx/Rx sequentially (synchronous mode).
        

---

## 2. **MLMR (Multi-Link Multi-Radio)**

- **Definition:** A **multi-link device architecture** where **each link has its own dedicated radio**.
    
- **Key points:**
    
    - Each link is **independent** (different channels, potentially different bands).
        
    - MLO scheduling can fully exploit **simultaneous transmissions** across links if STR is supported.
        
    - Helps avoid **self-interference** compared to multi-link single-radio devices.
        

---

## 3. **STR vs MLMR**

|Feature|STR|MLMR|
|---|---|---|
|What it describes|Capability to Tx & Rx simultaneously|Hardware architecture (multi-radio)|
|Purpose|Increase throughput, reduce latency|Enable independent link operation|
|Dependency|Can exist on single-radio or multi-radio devices|Usually used with STR for max performance|
|Scheduling|Asynchronous across links|Each radio can be scheduled independently|

---

## 4. **Putting it together in Wi-Fi 7**

- **STR + MLMR = Maximum MLO efficiency**:
    
    - Device has multiple radios (MLMR).
        
    - Each radio can transmit/receive simultaneously (STR).
        
    - Scheduler can exploit **all links concurrently**, achieving very high throughput and low latency.
        
- **STR without MLMR:**
    
    - Single-radio STR is difficult; usually requires full-duplex PHY.
        
- **MLMR without STR:**
    
    - Multiple radios, but each operates in **half-duplex**, so links are still coordinated synchronously.
        

---

✅ **Summary:**

- **STR** = simultaneous Tx/Rx capability (duplex behavior).
    
- **MLMR** = multiple radios supporting multiple links (hardware architecture).
    
- Together, they define how MLO can achieve **high throughput, low latency, and efficient spectrum use** in Wi-Fi 7.