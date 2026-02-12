# Review Notes: mlo-attack-dashboard-plan-v2.md

Date: 2026-01-05
Source: .claude/docs/plans/mlo-attack-dashboard-plan-v2.md

Findings
- Medium: The filter uses unanchored regex `experiment_id ~ '${experiment_filter:regex}'`, so a single selection can still match other IDs containing the same substring; anchor it (`^${experiment_filter:regex}$`) or switch to `IN (${experiment_filter:csv})` with an `allValue` to avoid cross-matching.
- Medium: Row 3 is labeled "MAC Layer" but now includes `net_active_flows` (network-level), so the layout rationale is inconsistent; rename the row or pick a MAC metric.
- Low: "Zero manual configuration" conflicts with the fixed absolute time range; new experiments still require a manual time change. Soften the claim or add a dynamic time-range note.
- Low: "Focus on 8 key metrics" conflicts with the table summarizing 6 metrics; align the text or expand the table.
- Low: "Corrects 5 critical issues" does not match the 6 items listed; fix the count for consistency.

Questions
- Do you expect experiment IDs that are prefixes of others? If yes, anchoring the regex becomes important.
- Should Row 3 be relabeled to include `net_active_flows`, or do you want to keep a pure MAC row?
