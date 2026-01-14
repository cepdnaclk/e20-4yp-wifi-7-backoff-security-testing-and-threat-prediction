**Definition:**  
QUC stands for **QoS (Quality of Service) Unit Control**, a mechanism introduced in Wi-Fi 7 (IEEE 802.11be) to manage **fine-grained QoS scheduling** across **multi-link operations (MLO)**.

**How It Works:**

- Each QUC represents a **traffic unit** with defined QoS requirements (latency, reliability, throughput).
    
- The access point (AP) uses QUCs to decide **which packets to transmit on which link** in a multi-link setup.
    
- QUC allows dynamic **traffic steering and prioritization** per link, optimizing utilization while maintaining latency guarantees.
    
- Works closely with **TSN** and **EHT (Extremely High Throughput)** MAC scheduling.
    

**Why It Matters:**

- Enables predictable latency and throughput for high-demand applications (XR, gaming, industrial IoT).
    
- Helps balance MLO traffic efficiently across multiple bands (2.4, 5, 6 GHz).