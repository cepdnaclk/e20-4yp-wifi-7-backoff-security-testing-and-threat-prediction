## What is a Free Ride?

In **CSMA/CA**, each link has its **own backoff (BO) counter**. Normally:

1. A device waits for the channel to be idle.
    
2. It decrements its BO counter **slot by slot**.
    
3. When the counter reaches zero, it transmits.
    

**A free ride occurs when a link can transmit without spending the usual backoff time**, usually because of **synchronization with another link**.

---

### 🔄 How Free Ride Happens in Synchronous MLO

1. **Scenario:**
    
    - Two links (Link A and Link B) are part of an MLD using synchronous MLO.
        
    - Link A finishes its backoff first, Link B still has some backoff remaining.
        
2. **Backoff Compensation:**
    
    - To transmit **simultaneously**, the remaining BO of Link B is **compensated / reduced to zero instantly**.
        
    - Link B gets a “free ride” — it didn’t have to wait for its backoff to count down normally.
        
3. **Effect:**
    
    - Both links can transmit together, improving efficiency.
        
    - Link B effectively **skips part of its normal waiting period** — hence the term **“free ride”**.
        

---

### ⚡ Key Points About Free Ride

- Happens **only in synchronous MLO**, not asynchronous mode.
    
- Improves **throughput and latency** by aligning transmissions.
    
- Must be carefully controlled, or it can **violate fairness rules** if overused.
    

---

### 💡 Analogy

- Imagine two friends waiting to enter a ride (BO).
    
- Friend A finishes waiting first, and the operator lets friend B join immediately **without waiting**, just so they can ride together.
    
- Friend B got a “free ride.”
    

---

✅ **In short:**

**Free ride = when a link transmits without finishing its full backoff because backoff compensation aligns it with other links in synchronous MLO.**