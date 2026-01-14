**What it is:** protocol or implementation vulnerabilities in the four-way handshake or key management that allow nonce reuse or replay, permitting decryption or injection in some versions/implementations.  
**Impact:** possible decryption of traffic, session hijacking depending on vulnerability specifics.  
**Indicators:** signs of anomalous negotiation or known CVE signatures.  
**Mitigation:** keep AP/client firmware up to date, apply vendor patches, prefer modern cryptographic suites.