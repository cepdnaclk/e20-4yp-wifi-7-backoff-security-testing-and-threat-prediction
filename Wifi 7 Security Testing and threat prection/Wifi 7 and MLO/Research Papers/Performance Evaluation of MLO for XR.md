
### Paper: "Performance Evaluation of MLO for XR.pdf"

- **Authors**: Marc Carrascosa-Zamacois, Lorenzo Galati-Giordano, Francesc Wilhelmi, Gianluca Fontanesi, Anders Jonsson, Giovanni Geraci, Boris Bellalta
- **Source**: arXiv:2407.05802v1 [cs.NI] 8 Jul 2024

#### Summary

This paper evaluates Multi-Link Operation (MLO) in Wi-Fi 7 for XR (Extended Reality) streaming, focusing on VR traffic. Simulations show MLO meets XR's stringent throughput (>100 Mbps) and delay (<10 ms) requirements, especially in uplink. MLO reduces delay via independent channel access, supports more users than Single-Link Operation (SLO), and performs better with more narrow-channel links than fewer wide ones. It highlights Wi-Fi 7's enabler role for XR, addressing challenges like distributed access and uplink control.

#### Important Points

- XR apps (VR/AR/MR) need high throughput, low delay; Wi-Fi struggles due to LBT and contention.
- MLO allows simultaneous transmission/reception on multiple links, reducing contention/delay.
- Uplink delay stricter than downlink; MLO helps via independent access.
- More MLO links (narrow channels) yield lower delays than fewer wide channels (same bandwidth).
- MLO supports more users than SLO with equivalent links.
- Simulations use realistic VR traffic; QoS via EDCA/OFDMA may worsen performance.
- Direct line-of-sight needed for good QoE; poor RSSI causes inconsistency.
- Funded by various grants (e.g., MAX-R, Wi-XR).

#### New Terms and Technologies

- **Multi-Link Operation (MLO)**: [[MLO]] Wi-Fi 7 feature for multi-band/channel connections via single association.
- **Extended Reality (XR)**: Includes VR/AR/MR with strict requirements (throughput >100 Mbps, delay <10 ms).
- **Listen Before Talk (LBT)**: [[Listen Before Talk (LBT)]] Wi-Fi's unlicensed spectrum access method causing contention.
- **Quality of Experience (QoE)**: [[Quality of Experience (QoE)]] User-perceived quality in XR (e.g., no lag/dizziness).
- **Single-Link Operation (SLO)**: [[Single-Link Operation]] Legacy Wi-Fi using one link.
- **OFDMA [[Multi-User OFDMA & MU-MIMO Enhancements]](Orthogonal Frequency Division Multiple Access)**: Wi-Fi 6+ feature for multi-user access, but may degrade XR.
- **Received Signal Strength Indicator (RSSI)**: Signal quality metric impacting XR performance.
[[QUC (QoS Unit Control)]]

