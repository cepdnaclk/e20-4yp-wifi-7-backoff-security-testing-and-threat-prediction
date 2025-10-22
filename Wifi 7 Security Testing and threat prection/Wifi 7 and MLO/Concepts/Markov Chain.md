**Markov Chains in the context of Multi-Link Operation (MLO) in Wi‑Fi 7**, including how they are used for **modeling link states, traffic, and scheduling decisions**.

---

## 1. **What is a Markov Chain?**

A **Markov Chain (MC)** is a **mathematical model** used to describe a system that transitions between a set of states with **probabilities**, where:

[  
P(\text{next state} \mid \text{current state, past states}) = P(\text{next state} \mid \text{current state})  
]

- This is called the **Markov property**: “future depends only on the present, not the past.”
    
- Formally defined by:
    
    - **States** (S = {s_1, s_2, ..., s_n})
        
    - **Transition probability matrix** (P) where (P_{ij} = \Pr(s_{t+1}=j \mid s_t=i))
        

---

## 2. **Why Markov Chains are useful in MLO**

In Wi‑Fi 7 **Multi-Link Operation (MLO)**, there are multiple links with **dynamic conditions**:

- Each link can be in different states: idle, busy, congested, or failed.
    
- The AP/STA scheduler needs to decide **which link to use for a flow or packet**.
    
- **Markov Chains model link state transitions probabilistically**, allowing:
    

1. **Prediction of link availability**
    
2. **Evaluation of throughput, delay, or collision probability**
    
3. **Design of intelligent scheduling policies**
    

---

## 3. **Typical MLO Markov Model**

### A. **Link states**

For a single link (l), a simple Markov chain might define:

|State|Meaning|
|---|---|
|Idle (I)|Link is free for transmission|
|Busy (B)|Link is currently used by another STA|
|Collision (C)|Transmission collided|
|Failed (F)|Link temporarily unavailable due to interference or error|

Transition probabilities (P_{ij}) could be:

[  
P =  
\begin{bmatrix}  
P_{II} & P_{IB} & P_{IC} & P_{IF} \  
P_{BI} & P_{BB} & P_{BC} & P_{BF} \  
P_{CI} & P_{CB} & P_{CC} & P_{CF} \  
P_{FI} & P_{FB} & P_{FC} & P_{FF}  
\end{bmatrix}  
]

- Each row sums to 1: (\sum_j P_{ij} = 1)
    

---

### B. **Multi-link model**

For **M links**, the **combined state space** is:

[  
S = S_1 \times S_2 \times \dots \times S_M  
]

- Exponentially grows with number of links and states.
    
- Often **simplified using independence assumptions** or **aggregate metrics** like available airtime or congestion level.
    

---

### C. **Applications in MLO**

1. **Link selection / scheduling**
    
    - Predict next link state and assign packets to the link with **highest expected throughput or lowest delay**.
        
2. **Collision probability estimation**
    
    - For multiple STAs sharing multiple links, use MC to compute steady-state probability of collisions per link.
        
3. **QoS-aware scheduling**
    
    - Markov model predicts **link busy/idle patterns**, ensuring high-priority flows get low-latency paths.
        
4. **Performance analysis**
    
    - Compute **steady-state probabilities**:  
        [  
        \pi_j = \lim_{t \to \infty} \Pr(s_t = j)  
        ]
        
    - Allows evaluation of:
        
        - Average link utilization
            
        - Expected delay per AC/flow
            
        - Probability of link failure
            
5. **Learning-based MLO**
    
    - MC can model environment dynamics for **reinforcement learning or multi-armed bandit algorithms**, providing a probabilistic reward model.
        

---

## 4. **Simple Example**

**Single link with 2 states**: Idle (I) and Busy (B)

- Transition probabilities:
    

[  
P = \begin{bmatrix}  
0.7 & 0.3 \  
0.4 & 0.6  
\end{bmatrix}  
]

- Interpretation:
    
    - If link is idle, 70% chance it stays idle next slot, 30% chance it becomes busy.
        
    - If link is busy, 60% chance it stays busy, 40% chance it becomes idle.
        
- **Steady-state probabilities** (\pi = [\pi_I, \pi_B]) satisfy:
    

[  
\pi = \pi P, \quad \pi_I + \pi_B = 1  
]

- Solve:
    

[  
\pi_I = 0.571, \quad \pi_B = 0.429  
]

- Meaning: on average, the link is idle 57.1% of the time and busy 42.9%.
    
- Scheduler can use (\pi_I) to decide which link is likely to be free for transmission.
    

---

## 5. **Advanced MLO Models**

1. **Multi-link AC-aware Markov chain**
    
    - Model each AC queue (VO/VI/BE/BK) per link.
        
    - States include **number of packets in queue**, link status, TXOP availability.
        
2. **Hidden Markov Models (HMM)**
    
    - Observed metrics: RSSI, PER, airtime.
        
    - Hidden states: actual congestion level, interference pattern.
        
    - Useful when links have **uncertain or noisy measurements**.
        
3. **Markov reward processes**
    
    - Assign rewards to states (e.g., throughput, latency).
        
    - Scheduler can **maximize expected reward over time**, combining with MAB or RL approaches.
        

---

## 6. **Benefits of Markov Models in MLO**

- **Predictive scheduling**: anticipate link availability.
    
- **Performance evaluation**: compute collision probability, delay, and utilization.
    
- **Adaptive QoS**: model latency-sensitive flows for AC_VO/AC_VI.
    
- **Integration with learning algorithms**: reward models for MAB or RL-based link steering.
    

---

✅ **Summary**

- Markov chains model **probabilistic link states** in MLO.
    
- Useful for **scheduling, collision estimation, QoS-aware flow allocation**, and **performance prediction**.
    
- Can be **extended** to multiple links, multiple ACs, and integrated with **reward-based learning algorithms**.
    
- Key idea: **predict future link conditions based on current state** to optimize multi-link operations.
    

---

If you want, I can **draw a diagram of a Multi-Link Markov Chain for MLO**, showing **multiple links, states (idle, busy, collision), transitions, and scheduler decisions** — it makes this concept much clearer visually.

Do you want me to make that diagram?