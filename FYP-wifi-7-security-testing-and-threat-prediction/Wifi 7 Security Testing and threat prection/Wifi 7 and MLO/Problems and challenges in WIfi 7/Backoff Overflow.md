
Ah — now we’re getting into a subtle but important problem in **synchronous MLO** with **backoff compensation**. Let’s break it down carefully.

---

## 🔹 Recap: Free Ride

- In synchronous MLO, when one link finishes backoff first, other links’ counters are **compensated to zero** to allow **simultaneous transmission**.
    
- This is called a **free ride** — the link effectively “skips” part of its backoff.
    

---

## 🔹 How Free Rides Can Cause Backoff Overflow

1. **Backoff Counters Are Finite**
    
    - Each link maintains a backoff counter in a **finite number of bits** (e.g., 8–16 bits depending on implementation).
        
    - When multiple free rides happen in quick succession, the **backoff logic may try to subtract or compensate multiple times**.
        
2. **Accumulation of Compensation**
    
    - Every free ride adjusts the counter.
        
    - If these adjustments are **not properly bounded**, the counter may go **negative** or wrap around **past its maximum**.
        
    - This is referred to as **backoff overflow**.
        
3. **Resulting Problems**
    
    - **Incorrect BO values** → link may wait too long or transmit prematurely.
        
    - **Loss of fairness** → some links “get ahead” repeatedly.
        
    - **Sync failures** → links may no longer align for joint transmission.
        
    - **Increased collisions** → if a link transmits before channel is really idle.
        

---

### ⚡ Example (Simplified)

|Link|Initial BO|Compensation (Free Ride)|New BO|
|---|---|---|---|
|A|3|0 → transmits|0|
|B|5|-3 (free ride)|2|
|B|2|-3 (next free ride)|??? (underflow!)|

- The second free ride **pushes BO below zero** → counter overflow or undefined behavior.
    
- Hardware/firmware must **detect and clamp** this to prevent misbehavior.
    

---

### 🔹 How Wi-Fi 7 Handles This

- **BO clamping** → counters cannot go below 0.
    
- **Maximum compensation limit** → only allow adjustment up to the current BO.
    
- **Per-link monitoring** → detect repeated free rides and adjust fairness algorithms.
    

---

✅ **In short:**

**Free rides can cause backoff overflow if repeated compensation reduces the backoff counter below zero or beyond its finite representation.** This can break synchronous MLO alignment, fairness, and collision avoidance.
