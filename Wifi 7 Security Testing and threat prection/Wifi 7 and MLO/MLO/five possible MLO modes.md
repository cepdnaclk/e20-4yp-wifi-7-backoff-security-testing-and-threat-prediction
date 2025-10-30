## Five possible MLO modes

- **What it is:** MLO isn't a single thing; it's a flexible framework. While not always named as "five modes," the operation of an MLO device (MLD) generally falls into these categories:
    
    1. **STR (Simultaneous Transmit/Receive):** The "full power" MLO. The device can literally transmit on one link (e.g., 5 GHz) _while simultaneously_ receiving on another (e.g., 6 GHz). This offers the highest throughput and lowest latency.
        
    2. **NSTR (Non-Simultaneous Transmit/Receive):** The device has multiple links but can only use one at a time (transmit _or_ receive). It can switch between them very quickly ("fast link switching"). This is less complex and power-hungry.
        
    3. **Synchronous Mode:** Links are tightly time-synchronized to transmit or receive data that is split across them. This is used for "bonding" links into one giant pipe.
        
    4. **Asynchronous Mode:** Links operate independently, each with its own backoff process. This is good for sending different, independent traffic flows on different links.
        
    5. **MLSR (Multi-Link Single Radio):** A more power-efficient mode where a device uses a single radio to quickly switch between links, but it can't monitor them simultaneously.
        
- **Security Relevance:** Each mode has different timing characteristics. **Security testing** must analyze all supported modes. For example, STR mode could open up new **timing side-channels** (like in the VoWiFi paper you provided), while Sync mode's reliance on timing makes it vulnerable to attacks that disrupt that synchronization.