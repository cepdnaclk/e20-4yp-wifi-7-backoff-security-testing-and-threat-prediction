
- **Implications:** Offloading infrastructure can be **weaponized**—especially if mobile botnets automate discovery, calibration, and synchronized multi-device attacks. Single offloaders have limited absolute rate, but **many** can be coordinated. Phase effects (when offloaders are receiving and sending simultaneously) complicate multi-offloader synchronization but also offer ways for attackers to **adjust phases** post-hoc by influencing offloader load.
    
  
    
- **Potential defenses (discussed by authors):**
    
    - Deploy **LDoS-aware monitoring** on offloaders: classify/hold suspicious bursts in time windows, **merge** them, or rate-limit per destination to flatten peaks.
        
    - **Randomize TCP minRTO** across servers/paths to reduce alignment—though most stacks default to fixed minRTO.
        
    - **Minimum offload size** or admission controls to raise attacker cost (with some usability trade-offs).
        
