## Resource Allocation Algorithm

- **What it is:** This is the central "brain" of a Wi-Fi 7 AP, especially one using OFDMA and Multi-Link Operation (MLO). It's the high-level set of rules that decides _who_ gets _what_ resources, _when_, and on _which_ link.
    
- **How it works:** This algorithm is the "super-algorithm" that combines many other concepts to make scheduling decisions. It constantly analyzes multiple inputs, including:
    
    - **Access Categories (ACs):** Is this high-priority voice or low-priority "best effort" data?
        
    - **Channel Quality:** How good is each user's signal on each available link?
        
    - **Fairness Policy:** Has this user been waiting long? (This is where **Proportional Fairness** fits in).
        
    - **MLO Policies:** Should this traffic be split, duplicated, or moved to a different link?
        
    - **Multi-RU state:** How can I "pack" multiple users into the available Resource Units (RUs) most efficiently?
        
- **Security Relevance:** This is the ultimate **algorithmic complexity attack** target. Because this algorithm is so complex and interconnected, a small, targeted attack on one of its _inputs_ (like spoofing channel quality, faking congestion, or sending malformed traffic) can have a massive, unpredictable cascading _output_. A **threat prediction** is that an attacker won't attack the "network" in a brute-force way but will attack the "algorithm," causing it to make a series of bad decisions that lead to a network-wide performance collapse or a highly targeted DoS.