**What it is:** exploiting the WPS PIN mechanism (if enabled) to brute force the PIN and recover the PSK.  
**Impact:** attacker can obtain the network passphrase and join the network.  
**Indicators:** repeated WPS attempts in AP logs.  
**Mitigation:** disable WPS, use WPA2/WPA3 with strong passphrases, monitor for WPS activity.