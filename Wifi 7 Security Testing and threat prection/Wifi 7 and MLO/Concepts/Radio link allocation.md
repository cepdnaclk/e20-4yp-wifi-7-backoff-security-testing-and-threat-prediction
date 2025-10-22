Radio link allocation in Wi-Fi 7 is managed by its flagship feature, **Multi-Link Operation (MLO)**.

At its core, MLO allows a single Wi-Fi 7 device (like a phone or laptop) to establish _multiple_ connections to a single Wi-Fi 7 access point (router) _simultaneously_, using different radio bands (e.g., 5 GHz and 6 GHz).

The **Access Point (AP) is the controller** that manages this entire process. It decides how to allocate the links to all connected devices to optimize the network's overall performance.

---

## Goals of Link Allocation in MLO

The AP's allocation strategy is designed to achieve three main goals, often at the same time:

1. **Higher Throughput (Speed):** This is done via **link aggregation**. The AP can split a large data stream (like a 4K video) across two or more links. For example, it might send half the video packets over the 5 GHz link and the other half over the 6 GHz link, effectively combining their bandwidth for much faster speeds.
    
2. **Lower Latency (Responsiveness):** For time-sensitive data like gaming or video calls, the AP can use the first available link. If the 5 GHz link is busy, it doesn't wait; it immediately sends the packet over the 6 GHz link, drastically reducing delay.
    
3. **Higher Reliability (Stability):** This is achieved through **link duplication**. For critical applications, the AP can send the _exact same_ data packet over both the 5 GHz and 6 GHz links. Even if one link suffers from interference (e.g., from a microwave) and drops the packet, the duplicate packet gets through on the other link, preventing a stall or stutter.
    

---

## How the Allocation is Decided and Managed

The AP uses sophisticated, real-time algorithms to decide "which packet goes where." This is a dynamic process involving several mechanisms.

### 1. Hardware Modes (How Devices Can Operate)

When a device connects, it negotiates with the AP which MLO mode it supports. This depends on the device's radio hardware:

- **Multi-Link Multi-Radio (MLMR):** This is the "true" MLO. The device has _multiple radios_ (e.g., one for 5 GHz, one for 6 GHz) and can transmit and receive on both links at the exact same time. This is the highest-performance mode.
    
- **Enhanced Multi-Link Single-Radio (eMLSR):** This is a more cost-effective mode for devices with only _one radio_. The single radio rapidly switches back and forth between links. While it can't transmit on both simultaneously, it can switch so fast that it still provides lower latency and better reliability than old single-link Wi-Fi.
    

### 2. Dynamic Traffic Steering and Load Balancing

The AP's "brain" is constantly at work. This is where the allocation happens:

- **Traffic Steering:** The AP inspects the _type_ of traffic. It will identify a gaming packet (which needs low latency) and may choose to _duplicate_ it. It will see a large file download (which needs high throughput) and will _aggregate_ it across links.
    
- **Load Balancing:** The AP monitors the real-time conditions (congestion, interference, signal strength) of all its links (2.4 GHz, 5 GHz, 6 GHz).
    
    - If it sees the 5 GHz band is becoming crowded with older Wi-Fi 6 devices, it will _steer_ its Wi-Fi 7 MLO clients to use the 6 GHz band more heavily.
        
    - If a client moves to the edge of the 6 GHz range, the AP will seamlessly shift its connection to the 5 GHz or 2.4 GHz link without dropping the connection.
        

This allocation problem—assigning dozens of clients and thousands of data packets to the best available links—is a highly complex optimization task that the AP must solve in milliseconds. As you noted in your previous query, this is the exact type of problem that can be mathematically modeled using bipartite graphs to find the most efficient solution.