That’s a **very important and subtle topic** in Wi-Fi 7 (IEEE 802.11be), especially with **Multi-Link Operation (MLO)** — where multiple links can transmit simultaneously. Let’s go step-by-step so you really understand what _collision probability of MLOs_ means and how it’s modeled or analyzed in research.

---

## 🌐 1. Background — Why Collisions Occur in Wi-Fi

In traditional Wi-Fi (like 802.11ac/ax):

- Each station (STA) contends for a single channel using **CSMA/CA** (Carrier Sense Multiple Access with Collision Avoidance).
    
- A **collision** happens when two or more STAs choose the same backoff slot and transmit at the same time.
    

The **collision probability (Pc)** depends on:  
[  
P_c = 1 - (1 - \tau)^{n-1}  
]  
where

- ( n ) = number of contending stations
    
- ( \tau ) = transmission probability of a station in a given slot
    

---

## ⚡ 2. Multi-Link Operation (MLO)

In Wi-Fi 7, each device can have **multiple radios (links)** operating across **different bands** (2.4 GHz, 5 GHz, 6 GHz).  
Two major types:

- **STR (Simultaneous Transmit and Receive):** Links work concurrently.
    
- **Non-STR (Non-Simultaneous):** Only one link transmits at a time.
    

Each link has its **own contention window (CW)**, **backoff counter**, and **channel conditions**, but the station (MLO STA) can coordinate how these links behave.

---

## 💥 3. What “Collision Probability of MLO” Means

When an MLO STA uses **multiple links**, the collision probability becomes **multi-dimensional** — depending on the interaction between links.  
There are **two main categories of collisions**:

### (a) **Intra-MLO collisions**

Between the _links of the same STA_ (e.g., both try to transmit at once in Non-STR mode).  
These can usually be avoided by coordination at the MAC layer — so this probability is often modeled as **zero** or **negligible** in analytical models.

### (b) **Inter-MLO collisions**

Between **links of different MLO STAs** contending in overlapping channels.  
This is where **collision probability analysis** focuses.

---

## 🧮 4. Collision Probability Model for MLOs

Let’s assume:

- ( N ) = number of MLO STAs
    
- Each STA has ( L ) links (e.g., 2 links: primary and secondary)
    
- ( \tau_l ) = transmission probability on link ( l )
    
- ( n_l ) = number of contending STAs on link ( l )
    

Then, the **collision probability for link ( l )** is:

[  
P_{c,l} = 1 - (1 - \tau_l)^{n_l - 1}  
]

However, for **multi-link scheduling**, the **effective collision probability** across all links of an MLO STA (assuming coordinated access) can be approximated as:

[  
P_c^{MLO} = 1 - \prod_{l=1}^{L} (1 - P_{c,l})  
]

This gives the **probability that at least one of the links experiences a collision**.

---

## 🧠 5. Intuition

- Using **more links** can **reduce effective delay**, but can also **increase contention**, since more links = more attempts.
    
- However, when **MLO coordination** is smart (e.g., “Fast switching” or “Backoff sharing”), it **lowers overall collision probability** because:
    
    - The STA can choose a **link with a lower busy probability**.
        
    - Idle links can **free ride** when another link wins the channel.
        

---

## 📊 6. Example Scenario

|Parameter|Value|
|---|---|
|# of MLO STAs|4|
|Links per STA|2 (5 GHz & 6 GHz)|
|Transmission probability per link (τ)|0.05|
|Contenders per link (nₗ)|4|

Then:  
[  
P_{c,5GHz} = 1 - (1 - 0.05)^{3} = 0.143  
]  
[  
P_{c,6GHz} = 1 - (1 - 0.05)^{3} = 0.143  
]  
[  
P_c^{MLO} = 1 - (1 - 0.143)^2 = 0.267  
]

So about **26.7% chance** that _any_ of the STA’s links collides in a given slot.

But if MLO intelligently schedules transmissions, this value can drop significantly (e.g., down to 10–12%).

---

## 🚀 7. Factors Affecting Collision Probability

|Factor|Effect|
|---|---|
|**Number of links (L)**|More links → potentially higher chance of at least one colliding, but lower delay if coordinated well|
|**Backoff synchronization**|Unsynchronized backoff can reduce intra-MLO collisions|
|**Link correlation (same or different channels)**|Independent channels → lower collision correlation|
|**MLO mode (STR vs Non-STR)**|STR can parallelize but also increase contention footprint|
|**Traffic load**|High load increases per-link τ, raising Pc|
|**Backoff compensation & aggregation policies**|Smart policies like Sync-FT reduce effective Pc|

---

## 🧾 8. Research Examples

Recent works model this analytically or via simulation:

- **"Performance Modeling of Multi-Link Operation in IEEE 802.11be" (IEEE Access, 2023)** — proposes equations for collision probability and throughput with variable contention window adaptation.
    
- **"MAC Layer Performance of Wi-Fi 7 MLO under Non-STR Mode" (IEEE ICC 2024)** — studies how cross-link coordination affects Pc and delay.
    
- **"Free-Riding and Backoff Sharing in MLO: Fairness vs Efficiency" (IEEE Trans. Wireless Comm, 2024)** — discusses how reduced backoff per link affects collision probability fairness.
    

---

## ✅ 9. Summary

|Term|Description|
|---|---|
|**Collision probability per link**|( P_{c,l} = 1 - (1 - \tau_l)^{n_l - 1} )|
|**Overall MLO collision probability**|( P_c^{MLO} = 1 - \prod_{l=1}^{L}(1 - P_{c,l}) )|
|**Goal**|Minimize Pc by coordinating link backoffs and choosing least-busy links|
|**Key insight**|MLO can reduce _effective collisions_ by offering multiple access opportunities, even though per-link contention remains|

---
