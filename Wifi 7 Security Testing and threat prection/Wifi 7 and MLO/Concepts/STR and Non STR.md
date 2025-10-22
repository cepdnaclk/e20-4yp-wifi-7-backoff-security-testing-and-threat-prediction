**STR vs. Non-STR MLDs:**

- **STR (Simultaneous Transmit and Receive):** An MLD that can transmit on one link while simultaneously receiving on another.
    
- **Non-STR:** An MLD that _cannot_ transmit and receive at the same time across its different links due to radio frequency (RF) power leakage between them. The paper focuses heavily on solutions for non-STR MLDs



**Non-STR**, not “NSTR.” Thanks for clarifying. In **Wi-Fi 7 / MLO**, **STR** stands for **Simultaneous Transmit and Receive**, so **Non-STR** is the opposite concept. Let me explain clearly:

---

## 1. **STR vs Non-STR**

|Term|Meaning|
|---|---|
|**STR**|Simultaneous Transmit and Receive — a device can **transmit and receive at the same time** on the same or different links (full-duplex style).|
|**Non-STR**|The device **cannot transmit and receive at the same time** on a given link; it must alternate between Tx and Rx (half-duplex behavior).|

---

## 2. **Context in MLO**

- In **Multi-Link Operation**, a device may have multiple links (radios) across different frequency bands or channels.
    
- **STR-capable device**: Can transmit on Link A while receiving on Link B simultaneously.
    
- **Non-STR device**: Must schedule transmissions and receptions so that Tx and Rx **don’t overlap on the same radio**.
    
- Some older hardware or low-cost Wi-Fi 7 devices are **Non-STR** on certain bands due to RF chain limitations.
    

---

## 3. **Implications**

1. **Throughput**:
    
    - STR allows **higher aggregated throughput**, because multiple links can be active simultaneously.
        
    - Non-STR may reduce effective throughput since Tx and Rx on the same link must be **serialized**.
        
2. **Latency**:
    
    - STR reduces latency for bi-directional traffic.
        
    - Non-STR introduces waiting time if Tx blocks Rx or vice versa.
        
3. **MLO Scheduler**:
    
    - STR devices can schedule **parallel transmissions across links**.
        
    - Non-STR devices must schedule **non-overlapping Tx/Rx slots**, possibly skipping some secondary channels temporarily.
        
4. **Cross-Link Interference (CLI)**:
    
    - Non-STR behavior can help **avoid self-interference** because the device never transmits and receives simultaneously on the same radio.
        
    - STR requires careful PHY/MAC design or self-interference cancellation.
        

---

✅ **Summary:**

- **Non-STR = cannot transmit and receive at the same time** on a link.
    
- It’s essentially **half-duplex operation** in MLO context.
    
- Wi-Fi 7 defines **STR and Non-STR modes** to account for hardware limitations and manage scheduling, throughput, and interference.
    

---

If you want, I can make a **simple diagram showing STR vs Non-STR behavior across multiple links** in Wi-Fi 7 — it’s very useful for research notes.

Do you want me to make that?

##### You said:

for STR you need asynchronous mode and for the NON STR you need synchrnous mode right

###### ChatGPT said:

Yes — that’s broadly correct, but let me explain carefully, because the **STR vs Non-STR distinction and its relation to synchronous/asynchronous operation** in Wi-Fi 7 is subtle.

---

## 1. **STR (Simultaneous Transmit and Receive) → Asynchronous Mode**

- STR allows a device to **transmit and receive at the same time**, either on the **same band** (full-duplex) or on **different bands/links**.
    
- Because multiple links are active simultaneously, each link’s transmissions and receptions must be **scheduled independently**.
    
- This is called **asynchronous operation**:
    
    - The device does not wait for one link’s Tx/Rx to finish before using another link.
        
    - MLO scheduler can activate links in a fully overlapping way to maximize throughput.
        
- **Requirement:** Hardware capable of handling **simultaneous signals** and PHY-level **self-interference cancellation** (if on same radio).
    

---

## 2. **Non-STR → Synchronous Mode**

- Non-STR devices **cannot transmit and receive simultaneously** on a link.
    
- All links operate in a **serialized fashion**: Tx and Rx slots are **aligned in time** to avoid overlap.
    
- This is called **synchronous operation**:
    
    - Each link follows a fixed schedule, and transmissions/receptions are coordinated.
        
    - Avoids self-interference, since the same RF chain is used in one direction at a time.
        
- **Implication:** Scheduler must be aware of Non-STR behavior and assign non-overlapping Tx/Rx windows across all links.
    

---

## 3. **Summary Table**

|Mode|Tx/Rx|Timing|Scheduler Type|Hardware Requirement|
|---|---|---|---|---|
|STR|Simultaneous|Asynchronous|Independent per link|Multi-radio / self-interference cancellation|
|Non-STR|Half-duplex|Synchronous|Coordinated / serialized|Single-radio or simpler hardware|

---

## 4. **Key Takeaways**

- **STR → asynchronous → higher throughput, more complex hardware**
    
- **Non-STR → synchronous → simpler hardware, lower throughput, serialized scheduling**
    
- The **asynchronous vs synchronous terms** in Wi-Fi 7 MLO refer to **how multiple links’ Tx/Rx activities are coordinated**, not the PHY symbol-level timing.