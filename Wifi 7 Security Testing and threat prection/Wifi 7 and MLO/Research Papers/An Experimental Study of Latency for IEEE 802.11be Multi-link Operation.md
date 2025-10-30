
This paper presents an experimental investigation into the real-world latency benefits of MLO, using a large dataset of spectrum occupancy measurements from the 5 GHz band. It compares the performance of traditional **Single-Link Operation (SLO)** with two MLO modes: **MLO-STR** (where radios operate independently) and **MLO-NSTR** (where a primary link controls a secondary one).

The study reveals two key findings:

1. When the different channels used for MLO have similar levels of traffic (**symmetrical occupancy**), MLO can reduce both average and 95th percentile latency by up to 78% compared to SLO.
    
2. However, in cases of **asymmetrical occupancy** (where one channel is much busier than the other), MLO-STR can paradoxically lead to _worse_ latency than using just a single link, with an observed increase of up to 112% in the 95th percentile delay.
    

To address this problem, the authors propose a new channel access method called **MLO-STR+**. In this mode, the device runs the channel access competition (backoff procedure) on all links in parallel and sends the packet on whichever link becomes available first. This approach guarantees that the latency will always be at least as good as, or better than, single-link operation.