In networking and Wi-Fi research, **“95th percentile delay”** is a common **performance metric** used to characterize latency. Let’s break it down clearly:

---

## 1. **Definition**

- The **95th percentile delay** is the value of **end-to-end delay** below which **95% of all measured packets fall**.
    
- In other words: only 5% of packets experience **higher delay** than this value.
    

Formally, if you collect **N packet delays**:

D1,D2,D3,...,DND_1, D_2, D_3, ..., D_ND1​,D2​,D3​,...,DN​

- Sort the delays in **ascending order**.
    
- Find the delay at position 0.95×N0.95 \times N0.95×N (or interpolate if needed).
    
- That value = **95th percentile delay**.
    

---

## 2. **Why it’s used**

- **Mean delay** can be misleading if a few packets have extremely high latency.
    
- The 95th percentile gives a **robust measure of worst-case latency for most packets**.
    
- Widely used in **QoS evaluation, wireless networks, MLO, and Wi-Fi 7 research**.
    

---

## 3. **Example**

Suppose you measure 20 packets and their delays (ms) are:

`1, 2, 3, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 10, 12, 15, 18, 20, 25, 30`

- Sort: already sorted.
    
- 95th percentile position = 0.95×20=190.95 × 20 = 190.95×20=19 → 19th value = **25 ms**.
    
- Interpretation: **95% of packets had delay ≤ 25 ms**, only 5% exceeded it.
    

---

## 4. **Use in Wi-Fi 7 / MLO**

- Wi-Fi 7 uses **multi-link operation** to reduce latency.
    
- Researchers often report **95th percentile delay per link** or **aggregated across links** to evaluate:
    
    - MLO scheduling efficiency
        
    - STR vs Non-STR impact
        
    - Effect of puncturing and cross-link interference (CLI) on latency
        

---

✅ **Summary:**

- 95th percentile delay = “delay that 95% of packets experience or less”
    
- It’s a **robust latency metric** that captures near-worst-case performance without being skewed by rare outliers.