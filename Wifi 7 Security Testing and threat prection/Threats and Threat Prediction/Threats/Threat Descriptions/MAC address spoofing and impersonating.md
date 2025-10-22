**What it is:** attacker changes their MAC to impersonate another device for bypassing MAC filtering or confusing network controls.  
**Impact:** bypass weak access controls, complicate auditing.  
**Indicators:** same MAC appears from different radios/locations, conflicting ARP entries.  
**Mitigation:** avoid MAC-based auth, use strong authentication, monitor for MAC duplicates.