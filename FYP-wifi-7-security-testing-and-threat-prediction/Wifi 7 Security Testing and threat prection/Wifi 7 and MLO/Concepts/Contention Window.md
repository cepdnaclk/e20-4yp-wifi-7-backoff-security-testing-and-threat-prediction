**CW (Contention Window)** is central to how backoffs work in Wi-Fi (and it ties directly into Sync-FT free riding + compensation).

---

## 🔹 What is CW?

- **CW = Contention Window**.
    
- It defines the **range of random backoff values** a device can choose from when it wants to transmit.
    
- After sensing the medium is idle, the device picks a random integer in **[0, CW]** as its backoff counter.
    

👉 Example:

- If CW = 15, then the device picks a random value from 0–15.
    
- That’s up to 16 slots of waiting before it can transmit.
    

---

## 🔹 Why CW Matters

- The **larger the CW**, the longer the average wait → less chance of collisions.
    
- The **smaller the CW**, the shorter the wait → more aggressive access.
    

Wi-Fi dynamically changes CW (doubling it after collisions, resetting after success) — this is the **Binary Exponential Backoff (BEB)** mechanism.

---

## 🔹 CW in the Context of Sync-FT and Free Riding

- Each link in a Multi-Link Device (MLD) independently chooses a backoff from its CW range.
    
- In **free riding**:
    
    - One link finishes early, forcing the others to “jump to zero.”
        
    - Those other links don’t fully honor the CW they picked → they’re effectively acting as if they had a **smaller CW** than reality.
        
    - Over time, this biases their access probability upward.
        

That’s why **backoff compensation** exists → it restores the _average effect_ of the CW by making the free-riding link **add back its skipped countdown** in the next round.

---

## 🔹 Analogy

Think of CW like a **lottery hat**:

- Each device/link pulls a random wait number from the hat.
    
- Bigger CW = more possible numbers → longer waits.
    
- If a link free rides, it’s like **throwing away its original ticket** and sneaking into the front of the line.
    
- Backoff compensation forces it to **carry over the unused ticket** next time so the game stays fair.
    

---

✅ So in short:  
**CW (Contention Window) = the range that determines how many backoff slots a device must randomly wait before transmitting.**  
In Sync-FT, free riding effectively short-circuits CW, so compensation ensures the link eventually “pays back” its fair share of waiting.