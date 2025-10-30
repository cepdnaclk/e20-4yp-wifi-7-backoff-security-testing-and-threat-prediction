### "Performance_of_80211be_Wi_Fi_7_with_Multi_Link.pdf"

- **Authors**: Molham Alsakati, Charlie Pettersson, Sebastian Max, James Gross, Vishnu Narayanan Moothedath
- **Source**: arXiv:2304.01693v1 [cs.NI] 4 Apr 2023

#### Summary

This paper evaluates Wi-Fi 7 (IEEE 802.11be) performance, focusing on Multi-Link Operation (MLO) for Augmented Reality (AR) applications, which demand high throughput, low latency, and high reliability. It compares MLO with Single-Link (SL) using simulations and different traffic-to-link allocation policies. Results show MLO's superiority in lower latency and supporting more AR users, but policies vary in susceptibility to channel blocking. The study highlights MLO's role in enhancing Wi-Fi for XR (Extended Reality) apps like AR/VR/MR.

#### Important Points

- Wi-Fi 7 aims for Extremely High Throughput (EHT) to support low-latency apps like AR.
- MLO allows simultaneous data transfer on multiple links for higher throughput, lower latency, and reliability.
- Traffic-to-link allocation policies are key; evaluated ones include least-congested link, uniform load balancing, and congestion-aware.
- Congestion-aware policies adapt better; least-congested allocation simplifies and reduces traffic exposure.
- Dynamic policies (periodic updates) vs. non-dynamic (only on flow arrival).
- Increasing links (e.g., 3 vs. 1) reduces 90th percentile latency by 93%; diminishing returns beyond 3 links.
- MLO outperforms SL in AR scenarios with same resources.
- Policies can degrade due to channel blocking.

#### New Terms and Technologies

- **Extremely High Throughput (EHT)**: Wi-Fi 7's goal for max throughput >30 Gbps with low latency.
- **Multi-Link Operation (MLO)**: Wi-Fi 7 feature for concurrent data transfer on multiple radio interfaces.
- **Traffic-to-Link Allocation Policy**: Algorithm distributing traffic flows to links (e.g., least-congested, uniform, congestion-aware).
- **Extended Reality (XR)**: Umbrella for VR, AR, MR apps requiring high throughput/low latency.
- **Task Group be (TGbe)**: IEEE group developing 802.11be.
- **Congestion-Aware Policies**: Policies adjusting load based on link congestion levels, dynamically or non-dynamically.