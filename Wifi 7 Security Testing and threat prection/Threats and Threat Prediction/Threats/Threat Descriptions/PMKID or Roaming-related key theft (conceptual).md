**What it is:** attacks that abuse roaming/key caching mechanisms to obtain authentication material usable for offline attacks.  
**Impact:** same as handshake capture — credential compromise if key material can be cracked offline.  
**Indicators:** unusual PMKID requests or suspicious handshake fragments.  
**Mitigation:** use up-to-date standards (WPA3/802.1X), patch AP firmware, use strong credentials.