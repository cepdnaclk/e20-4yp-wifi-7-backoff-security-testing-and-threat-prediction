## Coexistence challenge

- **What it is:** Wi-Fi operates in unlicensed spectrum, meaning it has no exclusive right to the airwaves. It must "coexist" with other technologies.
    
- **How it works:** Examples include:
    
    - **In 2.4 GHz:** Bluetooth, Zigbee, microwave ovens.
        
    - **In 5 GHz:** Weather radar (DFS), and other Wi-Fi networks.
        
    - **In 6 GHz:** Incumbent services (like satellite uplinks) and other Wi-Fi networks.
        
- **Security Relevance:** Coexistence mechanisms are a key target. An attacker can **spoof coexistence signals**. For example, continuously transmitting a fake radar pulse can trick an AP into vacating a 5 GHz channel (a "DFS attack"). This same logic could be applied in 6 GHz to exploit new coexistence mechanisms, forcing the network to operate on fewer or less efficient channels.