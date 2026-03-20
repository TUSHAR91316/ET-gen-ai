# Impact Model (Back-of-envelope)

## Metrics targeted (rubric)
1. Full workflow automation (not single-step generation)
2. Multi-agent coordination with compliance guardrails
3. Reduced content cycle time (turnaround time)
4. Higher first-pass compliance (less rework)

## Baseline assumptions
Assume an enterprise content team produces **assets per week** (blogs + social + email variants).

For each asset, a typical manual lifecycle is approximated as:
- Drafting + channel formatting: 2.0 hours
- Compliance review + rework loops: 1.5 hours
- Localization: 2.5 hours
- Packaging + scheduling: 0.75 hours

Total manual baseline per asset:
- `6.75 hours/asset`

## Automated savings model (used in code)
Let:
- `draft_time_saved = 0.40`
- `compliance_rework_reduction = 0.30`
- `localization_time_saved = 0.55`
- `packaging_time_saved = 0.20`

The system produces 2 draft variants per channel in the demo.
So the number of drafts/variants scales with:
- `assets_count = len(channels) * 2`

## Rework reduction logic (defensible)
Compliance guardrails are run *before* localization and packaging.

So if the compliance report passes:
- the model increases effective compliance savings
else:
- savings remain lower because the workflow reroutes for edits or stalls in a real deployment.

## Example math (plug-and-play)
If the team ships **20 assets/week**:
- Manual effort ≈ `20 * 6.75 = 135 hours/week`
- With estimated overall reduction ≈ `~60%` (from the weighted model)
- Time saved ≈ `135 * 0.60 = 81 hours/week`

If you assume a blended labor cost (example):
- `₹1200/hour`
- Weekly cost saved ≈ `81 * 1200 = ₹97,200/week`

## Consistency improvement (quality metric)
Report the **compliance first-pass rate**:
- baseline (assume) `70%`
- target (guardrail + audit trail) `90%`

This reduces the number of approval iterations and shortens time-to-publish.

## Assumptions you should state in the pitch
- Compliance checks are representative of real brand/legal rules
- Localization is consistent because required disclaimers and terminology are carried through the structured pipeline
- “Publishing” is demonstrated via payloads + scheduled calendar for hackathon safety

