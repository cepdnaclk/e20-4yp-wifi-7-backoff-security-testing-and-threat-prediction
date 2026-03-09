# new_codex_updates

## Scope checked
I scanned additional material from:
- `C:\Users\DTC\OneDrive\Documents\Obsidian Vault\FYP-wifi-7-security-testing-and-threat-prediction\FYP-wifi-7-security-testing-and-threat-prediction\Wifi 7 Security Testing and threat prection\...`
- `C:\Users\DTC\OneDrive\Documents\Obsidian Vault\FYP-wifi-7-security-testing-and-threat-prediction\docs\...`
- `C:\Users\DTC\OneDrive\Documents\Obsidian Vault\FYP-wifi-7-security-testing-and-threat-prediction\code\analysis\GNN\...`

These include notes that were not explicitly captured in the previous `codex-updated` package.

---

## Additional findings not previously captured

## 1. Expanded threat-testing roadmap (explicit 12-item list)
Source: `docs/images/Problems expected to uncover.md`

The Obsidian docs define an explicit list of planned/expected threat vectors:
1. Backoff manipulation for asynchronous behavior / overflow edge-cases.
2. Cross-link interference via legacy-device style primary-link blocking.
3. Collision-probability exploitation through backoff/countdown dynamics.
4. Frame aggregation and striping risk exploitation.
5. Multi-link association hijacking.
6. Naive splitting and out-of-order packet effects.
7. Multi-armed bandit (MAB) exploitation.
8. Packet splitting challenges exploitation.
9. Collision exploitations.
10. Packet allocation exploitation.
11. HARQ-related vulnerability categories.
12. Beam hijacking or spoofed CSI feedback.

This list is useful as a formal "threat matrix target set" for your methodology/future work sections.

---

## 2. Richer NDT architecture blueprint (beyond implemented code)
Sources:
- `NDT/Final Digital Twin Proposal/High-level architecture Of DTN...md`
- `NDT/Final Digital Twin Proposal/High-level flow (Fully explained).md`
- `NDT/Final Digital Twin Proposal/Why design Choices/Why the design Choices.md`

New conceptual architecture detail includes:
- Explicit dual-path flow: AI workflow + simulator federation.
- Simulator federation intent: ns-3 + OMNeT++ + MATLAB by fidelity role.
- NDT-MANO + ZSM lifecycle automation emphasis.
- Containerlab as orchestration backbone with VRnetlab for VM-only NOS.
- Future edge-cloud split and federated-learning oriented operation.

Important: this is broader than what is currently implemented in this repo, so it should be presented as design intent / roadmap rather than fully completed implementation.

---

## 3. More detailed Wi-Fi 7/MLO telemetry wishlist
Source: same NDT architecture/flow notes.

Additional telemetry dimensions are proposed beyond current 13-metric runtime pipeline, including:
- EHT MCS and RU maps.
- Puncturing usage.
- OBSS/BSS-coloring density and OBSS-PD events.
- Per-AC queue statistics.
- EMLSR/MLO state transitions and failovers.
- DFS/mute window events.

This is strong material for a "next-phase instrumentation" subsection.

---

## 4. Dedicated MLO threat-model table (10 threats with indicators)
Source: `Wifi 7 and MLO/MLO/MLO threat-model table.md`

A structured table exists covering 10 threat classes with:
- exploit concept,
- impact,
- qualitative likelihood/severity,
- practical mitigation,
- detection indicators.

It includes concrete indicator patterns (e.g., repeated compensation events, per-link asymmetry in PER/SNR, association teardown anomalies), which can strengthen your detection/monitoring discussion.

---

## 5. Conceptual mechanism notes around backoff compensation risks
Sources:
- `Wifi 7 and MLO/Concepts/Backoff Compensation.md`
- `Wifi 7 and MLO/Concepts/Free Ride.md`
- `Wifi 7 and MLO/Problems and challenges in WIfi 7/Backoff Overflow.md`

New narrative detail:
- "Free ride" in synchronous MLO is clearly explained as compensated countdown skipping.
- Repeated compensation can create underflow/overflow edge cases in finite counters if clamping logic is weak.
- This gives you a strong theoretical bridge between performance behavior and security exploitability.

---

## 6. Packet-steering security framing is richer than prior summary
Sources:
- `Wifi 7 and MLO/Concepts/Packet Steering.md`
- `Wifi 7 and MLO/Problems in MLO/Naive Splitting.md`

Additional points:
- AC-aware steering policy by traffic class (voice/video/best effort/background).
- STR vs Non-STR steering implications for reordering/latency.
- Naive splitting formalized as an anti-pattern with detection metrics (busy ratio asymmetry, PER/retrans spikes, reordering effects).
- Clear security angle: steering manipulation can force high-priority flows onto degraded links.

---

## 7. Additional adversarial-learning perspective notes
Sources:
- `Threats and Threat Prediction/Threats/Exploitations/Exploitation Of MAB.md`
- `Threats and Threat Prediction/Threats/Exploitations/link failures in MLO.md`

These notes extend your threat narrative into:
- reward/observation poisoning risks for MAB-based steering,
- link-failure induction/exploitation patterns,
- defensive emphasis on authenticated telemetry and cross-sensor validation.

These are useful for your future-work and robust-AI/security sections.

---

## 8. Legacy/parallel GNN codebase context (not in main runtime pipeline)
Sources:
- `code/analysis/GNN/attack_model.py`
- `code/analysis/GNN/backoff_dataset.py`
- `code/analysis/GNN/train_attack.py`

New context:
- There is an older/parallel GNN workflow using a 3-class output (`normal`, `positive attack`, `negative attack`).
- Dataset feature set there includes **`bias` as an input feature** in `FEATURE_KEYS`, which can create label leakage risk in ML evaluation if not handled carefully.

This is important if your final paper compares old vs new modeling pipelines.

---

## How this should update the final paper draft

1. Add an explicit "Threat Coverage Matrix" section using the 12-item roadmap + 10-item threat table.
2. Split architecture claims into:
- implemented now,
- proposed architecture roadmap (MANO/ZSM/federated sim/FL).
3. Add "Telemetry Expansion Plan" for RU/puncturing/OBSS/EMLSR/DFS features.
4. Add a short "Modeling Lineage" section:
- legacy 3-class GNN path,
- current binary pipeline detector path,
- risks like label leakage from explicit `bias` feature in early datasets.

---

## Evidence quality note
These findings come from Obsidian research/design notes and planning docs. Treat them as:
- high value for research framing, design rationale, and future work,
- but not always evidence of completed implementation in the current `ndt-wifi7-mlo-security` runtime code.

