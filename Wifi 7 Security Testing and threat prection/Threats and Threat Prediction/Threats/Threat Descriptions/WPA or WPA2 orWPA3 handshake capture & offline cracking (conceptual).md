

**What it is:** attacker captures the protocol handshake between a client and AP to attempt offline password guessing against the captured material. (Note: describing capture technique is sensitive—this is only conceptual.)  
**Impact:** if passphrase is weak, attacker may recover it and gain network access.  
**Indicators:** repeats of 4-way handshake events, new unknown clients appearing.  
**Mitigation:** use strong passphrases (>12 chars, random), prefer WPA3 or 802.1X with certificates, monitor for suspicious reconnections.