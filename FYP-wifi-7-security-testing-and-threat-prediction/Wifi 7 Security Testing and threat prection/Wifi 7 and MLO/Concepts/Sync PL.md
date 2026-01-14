Got it 👍 — you want a **full explanation of Synchronous Parallel Links (Sync PL) operation in Wi-Fi 7 MLO**. Let’s break this down carefully from the ground up.

---

# 🔹 What is Sync PL in Wi-Fi 7 (802.11be MLO)?

MLO (Multi-Link Operation) allows a device (MLD = Multi-Link Device) to use multiple bands/links (like 5 GHz + 6 GHz) **together**.

In **Synchronous Parallel Link (Sync PL)** mode:

- All the selected links (bands) of the MLD are treated as a **single logical transmission entity**.
    
- A transmission can **only start when all links are simultaneously ready** (backoff = 0).
    
- Frames may be **split and sent in parallel across the links** for higher throughput.
    

---

# 🔹 How Sync PL Works

### 1. **Backoff Synchronization**

- Each link runs its own CSMA/CA backoff procedure.
    
- But for Sync PL, the MLD ensures they are **aligned at zero** before transmission.
    
- If one link finishes early (BO=0), it must wait until the others also finish.
    

### 2. **Transmission Start**

- Once all links’ backoffs are zero, the MLD **transmits simultaneously** on those links.
    
- This allows splitting a large frame (or multiple frames) across links → effectively a “wide pipe.”
    

### 3. **Handling Imbalances**

- If one link becomes busy (occupied by another device), the whole synchronous group is delayed.
    
- After the busy link becomes free, the MLD uses **backoff compensation** so that waiting links don’t get unfairly penalized.
    

---

# 🔹 Advantages of Sync PL

✅ **Higher Throughput**

- By splitting traffic across multiple links at the same time.
    

✅ **Deterministic Latency**

- Since transmissions are aligned, they avoid inter-link jitter and keep timing consistent.
    

✅ **Efficient for Large Packets**

- Big data frames (e.g., AR/VR, 8K video) benefit from parallel split transmission.
    

---

# 🔹 Disadvantages of Sync PL

❌ **Blocked by the slowest/busiest link**

- If one band is congested, the entire synchronous transmission is delayed.
    

❌ **Increased Collision Risk**

- All links must hit zero BO at once, which may require waiting longer.
    

❌ **Wasted Opportunities**

- A free link cannot be used independently while waiting → efficiency loss compared to async mode.
    

---

# 🔹 Comparison with Conventional Wideband (Pre-Wi-Fi 7)

- **Old Way (Wideband in 802.11ac/ax)**:
    
    - You bond channels within the **same band** (e.g., 80 MHz → 160 MHz).
        
    - Still one PHY, one contention window.
        
- **New Way (Sync PL in Wi-Fi 7)**:
    
    - You can bond **across multiple bands (5 GHz + 6 GHz)** using multiple radios.
        
    - Still logically synchronized, but physically independent links.
        
    - More flexible, but more complex.
        

---

# 🔹 Example Analogy

Imagine you’re sending goods using **two conveyor belts (links)**:

- In **Sync PL**:
    
    - Both belts must start **together**.
        
    - If one belt is blocked, the other waits.
        
    - Packages can be split (half on one belt, half on the other).
        
- In **Async PL**:
    
    - Each belt runs independently.
        
    - You can send on one while the other is blocked.
        
    - But deliveries may not arrive in perfect sync.
        

---

# 🔹 Timeline Example (Simplified)

```
Link A: [BO 5][TX]........................
Link B: [BO 7]....[TX]....................

Sync PL: Must wait until both BO=0 → TX starts together
Async PL: Link A could TX earlier, B later, independently
```

---

# 🔹 Special Case: Free Ride Issue

- In Sync PL, sometimes one link’s BO is already at 0 when another finishes.
    
- It can **“free ride”** → skip its own waiting, since transmission must align.
    
- But repeated free rides can distort fairness → leads to **backoff overflow problems** (other devices perceive unfair contention).
    

---

✅ So, in short:

**Sync PL = coordinated, lockstep multi-link transmission with high throughput but vulnerable to congestion/delays.**

---

Do you want me to now also give you a **visual diagram (timeline + link states)** so you can clearly see how Sync PL vs Async PL plays out?