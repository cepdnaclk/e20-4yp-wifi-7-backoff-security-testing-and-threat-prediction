In Wi-Fi (CSMA/CA – Carrier Sense Multiple Access with Collision Avoidance), before a device transmits:

1. It listens to the channel (Clear Channel Assessment).
    
2. If the channel is busy, it chooses a **random backoff time** (measured in time slots).
    
3. The counter decrements only when the channel is idle.
    
4. Once the counter reaches zero, the device can transmit.
    

This avoids collisions by randomizing who gets the medium next.


### ⚡ Wi-Fi 7 and Backoff Compensation

Wi-Fi 7 introduces **multi-link operation (MLO)** and **enhanced channel access**, which complicate backoff.

**Problem:**

- With multiple links (e.g., 2.4 GHz + 5 GHz + 6 GHz used simultaneously), each link might have a **different backoff timer** running.
    
- If one link becomes free earlier, the other links may waste time still counting down.
    
- This reduces efficiency.
    

**Solution – Backoff Compensation:**

- Wi-Fi 7 introduces **synchronized backoff across links**.
    
- If one link finishes its backoff earlier, the others **adjust (compensate) their timers** so they can transmit together.
    
- This ensures multi-link devices can start transmissions simultaneously, improving throughput and lowering latency.

### 🔑 How Backoff Compensation Works in Wi-Fi 7

1. **Maintain a shared backoff counter** across all active links.
    
2. **When a transmission opportunity arises** on one link, the other links "compensate" their counters so they don’t have to restart from scratch.
    
3. This enables **parallel channel usage** (multi-link synchronous transmissions).
    
4. The result: **better channel utilization, lower delay, and higher aggregate throughput.**

**In short:**  
Backoff compensation in Wi-Fi 7 = **a mechanism to synchronize and reuse backoff timers across multiple links** so that multi-link operation is efficient and doesn’t waste airtime.


[[Free Ride]]
[[Backoff Overflow]]
[[2 Device Backoff]]