## **1. Introduction**

**Arbitration Inter-Frame Spacing (AIFS)** is a key component of **Enhanced Distributed Channel Access (EDCA)** in IEEE 802.11e and later standards (including Wi-Fi 7).

- **Purpose**: Controls how long a station waits after the medium becomes idle before attempting transmission.
    
- **Goal**: Prioritize traffic based on **Access Category (AC)** to provide **Quality of Service (QoS)**.
    

---

## **2. Relationship to EDCA**

EDCA defines **four Access Categories (ACs)**:

|AC|Traffic Type|Priority|
|---|---|---|
|AC_VO|Voice|Highest|
|AC_VI|Video|High|
|AC_BE|Best Effort|Medium|
|AC_BK|Background|Lowest|

- Each AC has **separate contention parameters**:
    
    - **CWmin / CWmax**: Contention window
        
    - **TXOP**: Maximum transmission time
        
    - **AIFS**: Arbitration inter-frame spacing
        

**AIFS determines** how quickly a station can start counting down its backoff timer after the medium becomes idle.

---

## **3. AIFS Definition and Calculation**

AIFS[AC]=SIFS+AIFSN[AC]×SlotTime\text{AIFS[AC]} = \text{SIFS} + \text{AIFSN[AC]} \times \text{SlotTime}AIFS[AC]=SIFS+AIFSN[AC]×SlotTime

Where:

- **SIFS (Short Inter-Frame Space)**: Minimum interval between frames for high-priority responses like ACKs.
    
- **AIFSN[AC] (AIFS Number)**: AC-specific integer controlling priority.
    
- **SlotTime**: Duration of a contention slot (depends on PHY layer).
    

**Key points:**

- **Lower AIFS** → Higher priority (can access medium sooner).
    
- **Higher AIFS** → Lower priority (wait longer before attempting transmission).
    

**Example (typical values for 802.11ac/ax/be):**

|AC|AIFSN|AIFS (assuming SIFS = 16 μs, SlotTime = 9 μs)|
|---|---|---|
|AC_VO|2|16 + 2*9 = 34 μs|
|AC_VI|2|34 μs|
|AC_BE|3|16 + 3*9 = 43 μs|
|AC_BK|7|16 + 7*9 = 79 μs|

- Voice/video frames **access the medium faster**, reducing latency.
    

---

## **4. Role in Multi-Link Operation (MLO) and Wi-Fi 7**

In **Wi-Fi 7 MLO**:

1. **Per-link AIFS**: Each link may have **different congestion or interference**, so AIFS can be tuned **per link**.
    
2. **QoS-aware packet steering**: Packet allocation considers AIFS per AC and per link:
    
    - High-priority traffic is steered to links with lower AIFS or lower congestion.
        
3. **Fairness and load balancing**:
    
    - Adjusting AIFS helps prevent **high-priority traffic from starving lower-priority flows** across multiple links.
        
4. **Dynamic adaptation**:
    
    - AIFS can be **dynamically tuned** in response to observed link conditions (e.g., increase AIFS on a congested link to reduce collisions).
        

---

## **5. Interaction with Backoff and TXOP**

- After medium idle for **AIFS[AC]**, the station selects a **random backoff** in the range `[0, CW]`.
    
- **TXOP** defines the maximum time a station can transmit once it wins the channel.
    
- Combined with **AIFS**, these parameters **control access fairness and QoS enforcement**.
    

**Example scenario in MLO:**

|Link|AC|AIFS|CWmin|TXOP|
|---|---|---|---|---|
|Link1 (5 GHz)|AC_VO|34 μs|7|3 ms|
|Link2 (6 GHz)|AC_BE|43 μs|15|1 ms|

- AC_VO frames on Link1 have **lowest latency**, even if Link2 is free, due to lower AIFS.
    

---

## **6. Importance in Security and Threat Modeling**

- Attackers could **exploit AIFS and EDCA parameters** by:
    
    - Sending high-priority frames to occupy medium (priority abuse)
        
    - Manipulating link congestion to degrade QoS of legitimate flows
        
    - Causing naive splitting or unfair flow distribution in MLO
        
- Understanding AIFS behavior is critical for **digital twin simulations and predictive threat modeling** in Wi-Fi 7.
    

---

## **7. Summary**

- **AIFS** is the waiting interval before a station starts backoff, **per AC**, used to enforce QoS.
    
- Lower AIFS → higher priority → faster medium access.
    
- In **Wi-Fi 7 MLO**, AIFS can be tuned **per link**, integrated with **packet steering** and **flow scheduling**, and dynamically adapted for performance and fairness.
    
- AIFS also plays a **key role in security considerations**, as attackers can manipulate channel access priorities to exploit the network.