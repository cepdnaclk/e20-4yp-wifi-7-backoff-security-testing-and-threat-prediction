# local MitM after gaining layer-2

**What it is:** once on the same L2 network (e.g., via rogue AP or compromised client), attacker poisons name resolution protocols to intercept traffic.  
**Impact:** interception of credentials, session hijack, credential capture.  
**Indicators:** anomalous ARP entries, duplicate IPs, client DNS failures.  
**Mitigation:** use encrypted application protocols (HTTPS), DNSSEC where applicable, switch port security, monitor ARP tables.