**Definition:**  
DCF is the **fundamental MAC protocol** in IEEE 802.11 (Wi-Fi) that governs how devices share the wireless medium.

**How It Works:**

- Based on **Carrier Sense Multiple Access with Collision Avoidance (CSMA/CA)**.
    
- Each station senses the channel:
    
    - If idle → transmits after a **Distributed Inter-Frame Space (DIFS)**.
        
    - If busy → waits and then uses a **random backoff** before retrying.
        
- Wi-Fi 7 still inherits DCF concepts but enhances them for **multi-link coordination**, especially under **Synchronous MLO**.
    

**Why It Matters:**

- Ensures fair and efficient access to the channel.
    
- Core mechanism extended to support **simultaneous multi-link transmissions**.