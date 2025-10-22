**EMLMR**, which is **Enhanced Multi-Link Multi-Radio**. Let me explain clearly and compare it with related architectures:

---

## 1. **Definition**

- **EMLMR = Enhanced Multi-Link Multi-Radio**
    
- A **Wi-Fi 7 STA or AP architecture** where **multiple radios** are used to support **multiple links simultaneously**, with enhancements for STR (Simultaneous Tx/Rx) and MLO scheduling.
    
- Each radio can operate on a **different band/channel**, supporting **concurrent transmissions and receptions**.
    

---

## 2. **How EMLMR Works**

- Each radio is **dedicated to a link**.
    
- **STR capable**: Each radio can transmit and/or receive at the same time.
    
- **Enhanced features** include:
    
    - Efficient **multi-link scheduling**
        
    - **Load balancing** across links
        
    - **Puncturing of busy secondary channels**
        
    - **Low latency / high throughput**, exploiting all available links concurrently
        

---

## 3. **Comparison with other MLO architectures**

|Feature|STR / MLMR|Non-STR / MLMR|EMLSR|EMLMR|
|---|---|---|---|---|
|Radios|2+|2+|1|2+|
|Links|Multiple, concurrent|Multiple, concurrent|Multiple, sequential|Multiple, concurrent|
|Tx/Rx|Simultaneous|Half-duplex|Sequential|Simultaneous|
|Scheduling|Asynchronous|Synchronous|Time-division|Asynchronous|
|Throughput potential|High|Moderate|Moderate|Very high|
|Use case|High-performance STA/AP|Multi-link legacy hardware|Low-cost devices|High-performance STA/AP with full MLO|

---

## 4. **Why “Enhanced”?**

- EMLMR introduces enhancements beyond classic MLMR:
    
    - Smarter **link selection**
        
    - Better **STR exploitation**
        
    - **Interference management** across radios
        
    - Integration with **puncturing**, **channel bonding**, and **MLO scheduling algorithms**
        

---

## 5. **In practice**

- **High-end Wi-Fi 7 APs and STAs** often implement **EMLMR** to maximize throughput and minimize latency.
    
- Works especially well in dense environments or when **multi-band aggregation** is needed.
    
- Together with STR, it allows **simultaneous Tx/Rx across multiple bands**, fully exploiting MLO.
    

---

✅ **Summary**

- **EMLMR = Enhanced Multi-Link Multi-Radio**
    
- Multiple radios → multiple links → STR-capable → high throughput and low latency
    
- Enhancements include smarter scheduling, interference handling, and full-bandwidth aggregation