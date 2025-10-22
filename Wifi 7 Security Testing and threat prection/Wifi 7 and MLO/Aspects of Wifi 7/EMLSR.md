In the context of **Wi-Fi 7 / MLO**, **EMLSR** stands for **Enhanced Multi-Link Single Radio**. Let me explain carefully:

---

## 1. **Definition**

- **EMLSR** = a device architecture where a **single radio** is capable of **operating multiple links** across different channels or bands, but **only one transmission or reception can happen at a time per radio**.
    
- It is the **“enhanced” version of legacy single-radio multi-channel operation**, designed to support **MLO features** even with **hardware limitations**.
    

---

## 2. **How EMLSR Works**

- **Single radio** can **hop between multiple links** or use multiple links in a time-division manner.
    
- **Cannot transmit and receive simultaneously on multiple links** (Non-STR).
    
- Supports features like:
    
    - **Channel bonding / puncturing** on wide channels.
        
    - **Multi-link scheduling**, but sequentially.
        
    - **Fallback when secondary channels are busy**.
        

---

## 3. **STR vs EMLSR**

|Feature|STR (Simultaneous Tx/Rx)|EMLSR (Single Radio)|
|---|---|---|
|Radios|1+ radios|1 radio|
|Tx & Rx|Simultaneous possible|Sequential only|
|Links|Multiple links active simultaneously|Multiple links active sequentially|
|Throughput potential|High (multi-link concurrency)|Moderate (depends on hopping efficiency)|
|Complexity|High (multi-radio or full-duplex)|Lower hardware cost|

---

## 4. **Use in Wi-Fi 7**

- EMLSR allows **low-cost or energy-constrained devices** to participate in **MLO networks** without needing multiple radios.
    
- Scheduling is **time-division-based**, hopping between primary channels of links.
    
- Works well with **puncturing** and **secondary channel skipping**, but cannot exploit full STR concurrency.
    

---

✅ **Summary**

- **EMLSR = Enhanced Multi-Link Single Radio**
    
- **Single radio**, multiple links, **non-simultaneous Tx/Rx**
    
- Supports MLO features like channel bonding and puncturing, but **Non-STR by nature**
    
- Ideal for low-power devices or devices without multiple RF chains