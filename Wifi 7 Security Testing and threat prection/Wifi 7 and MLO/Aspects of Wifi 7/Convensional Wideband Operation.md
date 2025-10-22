## Conventional Wideband Operation in IEEE 802.11

1. **Definition**
    
    - Traditional Wi-Fi uses **a single frequency channel (or “band”)** for transmission.
        
    - The **channel width** can vary: e.g., **20 MHz, 40 MHz, 80 MHz, 160 MHz**.
        
    - “Wideband” generally refers to using **channels wider than the basic 20 MHz**, to increase throughput.
        
2. **How It Works**
    
    - Data is transmitted using **OFDM (Orthogonal Frequency-Division Multiplexing)** within the single channel.
        
    - All subcarriers in that channel are used together — the link is **monolithic**, meaning you cannot split a single frame across multiple independent channels.
        
3. **Characteristics**
    
    - **Single channel per link** → no multi-link aggregation.
        
    - **Channel bonding**: combine adjacent channels to form a wider band (e.g., 80 MHz = four 20 MHz channels).
        
    - **Simplicity**: easier to implement in hardware, fewer synchronization issues.
        

---

### 🔹 Example in IEEE 802.11ac/ax

|Standard|Max Channel Width|Modulation|Notes|
|---|---|---|---|
|802.11n|40 MHz|up to 64-QAM|“narrow” wideband|
|802.11ac|80/160 MHz|up to 256-QAM|Channel bonding to increase throughput|
|802.11ax|20/40/80/160 MHz|1024-QAM|OFDMA introduces resource unit division, but still single-link per user|

---

### 🔹 Limitations of Conventional Wideband Operation

1. **Single-band dependency**
    
    - All data uses one channel; if it’s congested, throughput drops.
        
2. **No multi-link aggregation**
    
    - Unlike **MLO in Wi-Fi 7**, a conventional wideband link cannot **stripe frames across multiple channels**.
        
3. **Sensitivity to interference**
    
    - Wider channels are more prone to interference because more spectrum is used simultaneously.
        
4. **Backoff and fairness**
    
    - Standard CSMA/CA applies only to that single channel.
        
    - No per-band backoff coordination like in MLO.
        

---

### 🔹 Analogy

- **Conventional wideband = a single highway with extra lanes**
    
    - A single car can use all lanes for speed (more subcarriers → more data).
        
    - If the highway is congested, everything slows down.
        
- **MLO = multiple separate highways**
    
    - You can use multiple highways at once, possibly splitting traffic across them.
        
    - More robust and higher total throughput.
        

---

✅ **Summary**

- **Conventional wideband operation** = transmitting on a **single wide channel**, using **all subcarriers within that channel**.
    
- All IEEE 802.11 versions before Wi-Fi 7 (802.11be) used this method.
    
- **Limitations**: no multi-link frame splitting, sensitive to congestion/interference, single backoff per link.


## Old Way (Conventional Wideband)

- One **big channel** (20/40/80/160 MHz).
    
- All data for a device goes through **that one channel**.
    
- If it’s congested or blocked, you’re stuck.
    
- Backoff and contention are **only for that channel**.
    
- Example: Wi-Fi 6E using a single 160 MHz channel in 6 GHz.
    

---

## 🔹 New Way in Wi-Fi 7 → **Multi-Link Operation (MLO)**

Instead of using just one big pipe, Wi-Fi 7 lets you use **multiple different frequency bands simultaneously**.

### ✅ Core Ideas

1. **Multiple Links (Bands/Channels)**
    
    - A device (Multi-Link Device, **MLD**) can connect to the AP on **2 or more bands** (e.g., 5 GHz + 6 GHz, or multiple 160 MHz chunks).
        
2. **Two Modes**
    
    - **Asynchronous MLO**: each band transmits independently (like having parallel pipes).
        
    - **Synchronous MLO**: all bands transmit in sync (like bundling multiple lanes into one super highway).
        
3. **Backoff Compensation**
    
    - Each band has its own contention (backoff), but to align in synchronous mode, unfinished bands are **“fast-forwarded”** (free ride).
        
4. **Load Balancing / Aggregation**
    
    - Data can be:
        
        - **Aggregated (striped)** across multiple links → higher throughput.
            
        - **Steered dynamically** to the less-congested link → lower latency.
            

---

## 🔹 Why This New Way is Better

|Aspect|Conventional Wideband|Wi-Fi 7 MLO|
|---|---|---|
|Channel use|One wide channel|Multiple independent links|
|Reliability|If channel interfered → performance drops|Can switch or aggregate across links|
|Latency|Higher (single queue, single BO)|Lower (parallel BOs, fast path selection)|
|Efficiency|Limited by congestion in that band|Can spread load dynamically|
|Flexibility|All data must fit one pipe|Data can be striped across multiple pipes|

---

### 🔹 Analogy

- **Old way (wideband)**: You’re driving a **super-wide highway**. It’s fast — but if there’s a traffic jam, everything stops.
    
- **New way (MLO)**: You have **multiple highways in parallel**. You can:
    
    - Use all of them at once (striping = higher throughput).
        
    - Pick whichever is clear at the moment (asynchronous = reliability).
        
    - Or synchronize them to act like one super-road (synchronous).
        

---

✅ **In short**:

- **Old way = one fat channel** (channel bonding).
    
- **New way = Multi-Link Operation (MLO)** → multiple bands/channels used at once, with sync/asynchronous modes, backoff compensation, and load balancing.