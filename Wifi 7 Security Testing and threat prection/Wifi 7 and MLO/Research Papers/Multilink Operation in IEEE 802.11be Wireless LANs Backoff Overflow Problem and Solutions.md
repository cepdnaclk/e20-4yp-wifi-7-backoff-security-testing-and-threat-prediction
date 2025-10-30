This paper focuses on a specific technical challenge with the **Multi-Link Operation (MLO)** feature in **IEEE 802.11be (Wi-Fi 7)**. The authors identify a "backoff count overflow problem" that arises in the **enhanced synchronous channel access scheme (Sync-FT)** when backoff compensation is used to ensure fairness with older, single-link devices. This overflow can degrade the performance of new multi-link devices (MLDs). The paper proposes and evaluates four solutions to fix this problem.

#### **New Terminologies**

- **MLO (Multi-Link Operation):** A core feature of Wi-Fi 7 that lets a device use multiple channels at the same time for sending and receiving data.
    
- **MLD (Multi-Link Device):** A device that can perform MLO.
    
- **STR and non-STR MLDs:** MLDs can be **Simultaneous Transmit and Receive (STR)**, meaning they can send and receive on different links at the same time, or **non-STR**, meaning they cannot, due to potential radio interference.
    
- **Sync vs. Async Operation:** Two ways for MLDs to access channels. In **Synchronous (Sync)** operation, all links must be ready before transmission starts. In **Asynchronous (Async)** operation, each link works independently.
    
- **Sync-FT (Synchronous Operation for Faster Transmission):** A hybrid of the Sync and Async methods designed for faster transmissions.
    
- **Free-riding:** When a link in Sync-FT transmits data before its backoff process is finished.
    
- **Backoff Count Overflow:** A problem where a device's backoff counter becomes too large from repeated compensations, preventing it from getting a chance to transmit.
    
- **SLD (Single-Link Device):** An older device that can only use one channel at a time.
    

#### **Technology Explanations**

- **Backoff Procedure:** In Wi-Fi, to avoid data collisions, devices use a "listen-before-talk" system. If a device senses the channel is busy, it waits for a random "backoff" time before trying to transmit again.
    
- **Backoff Compensation:** To be fair to older devices, when a new MLD "free-rides" and transmits ahead of its turn, it has to add a penalty to its next backoff time. This paper shows that too much of this compensation can lead to the "backoff count overflow" problem, effectively locking the device out of transmitting.
    