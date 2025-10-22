**What it is:** attacker deploys an AP that imitates a legitimate SSID (and possibly BSSID) to trick clients into connecting.  
**Impact:** credential theft, man-in-the-middle (MitM), traffic interception, injection.  
**Indicators:** unexpected APs with same SSID but different BSSID/location, clients showing new gateway or certificate warnings, unusual DNS or TLS errors.  
**Mitigation:** use 802.1X/EAP (certificate-based auth), educate users, use network access control & client configuration to prefer known BSSIDs, monitor for SSID duplicates.