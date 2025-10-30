### **Paper 1: `IEEE 802.11be Network Throughput Optimization with Multi-Link Operation and AP Controller`**

#### **Summary**

This paper argues that simply having Multi-Link Operation (MLO) in Wi-Fi 7 is not enough to guarantee the best performance. The _strategy_ for how to use the multiple links is critical. The authors propose a new, data-driven algorithm that uses a centralized **AP Controller (APC)** to intelligently manage the entire Wi-Fi 7 network. This algorithm solves two main problems:

1. **AP-STA Pairing:** It decides which client device (Station) should connect to which Access Point.
    
2. **Radio Link Allocation:** [[Radio link allocation]] For an MLO device, it decides how its data traffic should be split across the available links (e.g., 2.4 GHz, 5 GHz, 6 GHz).
    

The goal is to maximize the _total network throughput_ while also maintaining **proportional fairness**, which ensures that no single device is "starved" of bandwidth and all users get a fair share. The paper's solution is evaluated for high-performance **MLMR (Multi-Link Multi-Radio)** devices.

#### **Important Points & Pointers**

- **Centralized Control:** The paper's key idea is to use a centralized **AP Controller** (APC) to manage the network. This controller has a complete overview of all APs, clients, and channel conditions, allowing it to make much smarter, network-wide decisions than a single AP or client could.
    
- **Two-Part Problem:** The algorithm breaks the optimization challenge into two steps: (1) finding the best AP-STA pairings, and (2) finding the best link allocation for those pairings.
    
- **Data-Driven:** The algorithm is "data-driven," meaning it uses real-time network status (like channel quality and traffic load) to make its decisions.
    
- **Proportional Fairness [[Proportional Fairness]](PF):** This is a critical goal. Instead of just maximizing raw speed (which might let one device get 10 Gbps while another gets 1 Mbps), PF ensures that the _proportional_ share of the network capacity is distributed fairly among all MLO devices.
    
- **Target Device:** The solution is designed and evaluated for **MLMR (Multi-Link Multi-Radio)** devices, which are high-performance clients that have multiple radios and can use them all at the same time.
    

#### **New Terms & Technologies**

- **AP Controller (APC):** A centralized management system (either a physical appliance or software) that coordinates and controls all the Access Points in a network. This is common in enterprise environments.
    
- **Resource Allocation Algorithm:** [[Resource Allocation Algorithm]] The set of rules and logic that decides "who gets what" on the network (e.g., which device gets to use which radio link and for how long).
    
- **Proportional Fairness (PF):** A scheduling algorithm or goal that balances network efficiency (high total throughput) with fairness (stable performance for all users).
    
- **MLMR [[STR MLMR]](Multi-Link Multi-Radio):** A high-performance MLO device that has multiple, independent radios. This is the most powerful MLO mode, allowing for true simultaneous communication.
    
- **STR [[STR and Non STR]](Simultaneous Transmission and Reception):** A capability of MLMR devices, mentioned in the paper, allowing them to transmit on one link (e.g., 6 GHz) _at the exact same time_ they are receiving on another link (e.g., 5 GHz).