## Multi-Link Operation Basics

- A **multi-link device (MLD)** can use **multiple frequency bands/links** at the same time (e.g., 5 GHz + 6 GHz, or two 6 GHz channels).
    
- The goal: higher throughput, lower latency, and more robust performance.
    

---

## ⚡ Modes of MLO

### 1. **Asynchronous MLO**

- Each link operates **independently** with its own contention, backoff, and scheduling.
    
- One link may transmit while another is still waiting.
    
- Advantage: high flexibility (if one band is congested, others can still work).
    
- Downside: higher latency variance and less efficient aggregation.
    

---

### 2. **Synchronous MLO**

- Links are **synchronized** so they transmit/receive **together**.
    
- Requires **backoff compensation** (so all links can align even if their backoff counters differ).
    
- Data frames can be **striped across multiple bands at once** — like parallel lanes on a highway.
    
- Advantage: ultra-low latency, deterministic scheduling, and efficient aggregation.
    
- Downside: requires tighter coordination and may “waste” some capacity if one band is busy.
    

---

## ✅ So, to your question:

In **synchronous MLO**:

- **No, the bands do _not_ work completely independently**.
    
- Instead, the device tries to **align transmissions across all active links**, using backoff compensation and scheduling so they can **start together**.
    

In **asynchronous MLO**:

- **Yes, each band works independently**, with its own backoff and channel access.


## The Key Difference: Compensation & Alignment

- In **asynchronous MLO** → each link’s backoff is **independent**, and they may transmit at different times.
    
- In **synchronous MLO** → all links do their own backoffs **but** when **one link finishes first**, the other links’ counters are **compensated (adjusted)** so they can align and transmit **together**.
    

So:

- **Yes**: all links perform individual BOs.
    
- **But**: unlike asynchronous mode, those BOs don’t stay separate — a “winner” link pulls the others forward through **backoff compensation** so transmission starts in sync.
    

---

## 📊 Analogy

- Imagine 3 runners (links), each with their own stopwatch (backoff).
    
- In **async mode**: whoever’s stopwatch hits zero runs on their own.
    
- In **sync mode**: all keep running their timers, but when the fastest one hits zero, the others skip ahead (compensate) so they all start running together.






in asynchronous mode, the data cannot be split and sent in multiple bands right ?

###### ChatGPT said:

Exactly ✅ — that’s one of the key differences between **asynchronous MLO** and **synchronous MLO (or Sync FT)** in Wi-Fi 7. Let me clarify:

---

## 🔹 Asynchronous MLO

1. **Independent Links**
    
    - Each link operates **independently** with its **own backoff**, **channel access**, and **transmission schedule**.
        
2. **No Coordinated Transmission**
    
    - Since the links are not synchronized, you **cannot reliably split a single frame across multiple bands**.
        
    - Each link can carry **its own frame**, but you cannot stripe or aggregate a single data frame across links.
        
3. **Use Case**
    
    - Good for **flexibility**: if one link is busy, others can still transmit.
        
    - Less complex hardware/timing requirements.
        
    - But you **cannot fully exploit multi-link bandwidth for a single frame**.
        

---

## 🔹 Synchronous MLO (Sync FT)

1. **Synchronized Links**
    
    - Links are aligned using **backoff compensation** and timing coordination.
        
2. **Frame Striping / Aggregation**
    
    - A single data frame can be **split and transmitted across multiple links simultaneously**.
        
    - This is what **maximizes throughput** and reduces latency.
        
3. **Hardware & Timing**
    
    - Requires precise **timing control**, **RF isolation**, and **backoff alignment**.
        

---

### ✅ Summary Table

|Feature|Asynchronous MLO|Synchronous MLO (Sync FT)|
|---|---|---|
|Links work independently|✅|❌ (aligned)|
|Single frame split across links|❌|✅|
|Latency|Higher / variable|Lower / deterministic|
|Throughput efficiency|Moderate|High (aggregated)|
|Complexity|Lower|Higher (timing + RF alignment)|

---

💡 **Analogy:**

- Async MLO: Each lane of a highway runs independently; cars in different lanes may start/stop at different times.
    
- Sync MLO: All lanes move together in perfect sync; a long truck (frame) can occupy multiple lanes at once.



# Problem

now in sync mode, when there are multiple links and if one has finished transmitting then it goes into BO mode. Others are still transmitting. Now if there is a nother process coming it goes on a BO and if that beats the other BO, the band is used for the new process right ? Then For the previous full process to synchronize, it has to wait till the new process finishes right ? Then all the processes can be zerod in the BO and then a new sync operation can be done. Is this correct ? If so then there can be multiple links performing new tasks that could leave the first task to be heavily delayed

###### ChatGPT said:

Yes 👌 — you’ve nailed the tricky part of **synchronous MLO contention behavior**. Let me restate what you’re saying, step by step, and confirm/clarify where needed.

---

## 🔹 Step-by-Step Breakdown

1. **Multi-link synchronous operation**
    
    - An MLD (say MLD-1) is transmitting on multiple bands (links).
        
    - One link finishes its transmission first → it enters **backoff (BO) mode**.
        
    - Other links are **still transmitting**.
        
2. **A new contender arrives (MLD-2)**
    
    - On the link that is already in BO, MLD-2 also chooses a BO counter.
        
    - If MLD-2’s backoff expires before MLD-1’s → **MLD-2 transmits on that band**.
        
3. **Impact on MLD-1’s synchronous operation**
    
    - MLD-1 cannot start a new **synchronous multi-link transmission** until **all of its links are available**.
        
    - Since one of its links is now busy with MLD-2’s traffic, MLD-1 has to **wait until MLD-2 finishes**.
        
4. **Resynchronization**
    
    - Once the busy link becomes free again, MLD-1 can **“zero” the BOs via compensation** across all its links.
        
    - Then it resumes with a new synchronous transmission.
        

---

## 🔹 Consequence: Potential Delay

- Yes ✅, this means that **the original task (MLD-1’s synchronous transmission) can be heavily delayed** if:
    
    - Other MLDs keep sneaking in during BO phases.
        
    - Or one band consistently sees more contention than the others.
        
- Effectively, the synchronous bundle is **only as fast as its slowest / busiest band**.
    

---

## 🔹 Analogy

- Imagine MLD-1 has trucks on **two roads** that must **arrive at the same destination together**.
    
- Road A truck finishes unloading early and waits.
    
- Road B truck is still unloading.
    
- In the meantime, another company (MLD-2) sends its truck onto Road A.
    
- MLD-1’s Road A truck must wait until MLD-2’s truck is done before the two original trucks can synchronize again.
    
- If more trucks from other companies keep coming, MLD-1’s delivery gets delayed more and more.
    

---

## 🔹 Key Takeaway

- **Yes, you are correct:**
    
    - In synchronous MLO, if one link gets occupied by another process while others are still busy, the original MLD must **wait until that link is free again** before it can resynchronize and transmit.
        
    - This can indeed cause **significant delays** if multiple external devices repeatedly contend on those bands.
        

---

👉 This is exactly why **asynchronous MLO mode** is also defined — so an MLD can at least keep using the other links independently, without being held hostage by one congested band.