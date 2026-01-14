## MLO Architecture

- **What it is:** The fundamental design of a Wi-Fi 7 device. A **Multi-Link Device (MLD)** is no longer a single-radio device.
    
- **How it works:** An MLD has one "upper" MAC (Media Access Control) layer that manages multiple "lower" MAC/PHY (Physical) layers. Each MAC/PHY pair is a "link" (e.g., a 5 GHz radio, a 6 GHz radio). To the rest of the network (like your computer's operating system), the MLD appears as a _single device_ with a _single MAC address_. This architecture is what allows MLO to split traffic, aggregate bandwidth, and provide seamless link switching.
    
- **Security Relevance:** This is the _core new attack surface_ in Wi-Fi 7. All security for MLO depends on the logic that manages these links. A flaw in this central MLD logic could be catastrophic, leading to DoS (if the logic crashes), information leakage between links, or failure of the entire MLO mechanism.