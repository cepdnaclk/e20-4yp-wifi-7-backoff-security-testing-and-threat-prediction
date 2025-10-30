## Coordinated Spatial Reuse (CSR)

- **What it is:** A technique to improve efficiency in dense Wi-Fi environments. It's an advanced form of "listen-before-talk."
    
- **How it works:** Normally, if AP 1 hears AP 2 transmitting, AP 1 will wait (back off). With CSR, AP 1 and AP 2 can coordinate. AP 1 might identify the transmission as "friendly" and, if the signal is weak enough, decide to transmit _at the same time_, "reusing" the space.
    
- **Security Relevance:** This relies on APs being able to trust each other's signals and reports. An attacker could **spoof these coordination frames**, tricking an AP into transmitting when it shouldn't (causing a real collision) or tricking it into backing off when it doesn't need to (a DoS attack).