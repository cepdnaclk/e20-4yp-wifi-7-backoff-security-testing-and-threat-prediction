# AI Handoff Prompt for Final Paper Draft (Updated)

Copy this prompt to another AI as-is.

---

You are drafting the **final report / research-paper style draft** for my project on:

**"Digital Twin Threat Prediction for Wi-Fi 7 Backoff Manipulation"**

I need a full paper draft based only on the project context files below. Do not invent experiments. When there are inconsistencies, explicitly state them and choose conservative claims.

## Context files to use (priority order)

1. `00_Project_Context_Master.md`
2. `01_Research_Evidence_and_Results.md`
3. `02_Source_Map_and_File_Guide.md`

Also use these source materials (referenced by the source map):
- `Pathum - Work in progress/Literature review.txt`
- `Pathum - Work in progress/Readme-Files/Datasets/*.md`
- `Pathum - Work in progress/Readme-Files/GNNs/*.md`
- `Pathum - Work in progress/Readme-Files/MLOs/*.md`
- repository docs under `docs/` (especially WP8/WP9/model analysis docs)

## What to produce

Write a complete draft with these sections:

1. Title
2. Abstract
3. Introduction
4. Background and Related Work
5. Problem Statement and Research Questions
6. System Architecture (NDT pipeline)
7. Methodology
8. Attack Modeling in Wi-Fi 7 MLO
9. Data Engineering and Telemetry Pipeline
10. GCN-Based Detection Pipeline
11. Experimental Setup
12. Results
13. Discussion
14. Limitations and Threats to Validity
15. Conclusion and Future Work
16. Appendix-style reproducibility notes

## Writing constraints

- Use formal academic tone.
- Do not claim production readiness unless fully supported.
- If metrics conflict across files, report the conflict and provide a careful interpretation.
- Separate **verified evidence** from **inferred interpretation**.
- Include a subsection that narrates the iterative debugging journey (field mismatch fixes, retraining rationale, distribution-shift issue).
- Include architecture/data-flow diagrams in text form (ASCII okay).

## Critical integrity requirements

- The repo contains documentation drift and version inconsistencies. You must include a transparent "evidence quality" or "consistency notes" subsection.
- Do not hide uncertainty around:
  - model version claims (v2.0.0 vs v2.1.0 narratives),
  - dataset counts (manifest vs local staged files),
  - dashboard/API mismatches.

## Emphasis I care about most

1. Why Wi-Fi 7 MLO creates a new security attack surface.
2. How digital-twin architecture enables security observability and testing.
3. How backoff manipulation was modeled and measured.
4. What worked technically in the pipeline.
5. What did not work cleanly (false positives, data-distribution mismatch), and why that is still a valuable research contribution.

## Output format

- Provide a polished, near-submission draft.
- Use clear headings.
- Include concise tables where useful.
- Include explicit dates (absolute dates) when referencing milestones.

---

After drafting, provide:

1. A short list of claims that are strongly supported.
2. A short list of claims that need more evidence before submission.
3. A list of figures/tables I should generate from the repo to strengthen the paper.

