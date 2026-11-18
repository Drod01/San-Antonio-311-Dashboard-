# What the numbers say

Rolling 12 months of San Antonio 311 requests: **Nov 14, 2025 → Nov 13, 2026**, 501,723 requests.

## 1. Volume is steady and large

About **1,375 new requests per day**, or roughly one every 63 seconds. Monthly volume stays inside a fairly narrow band, so this is a constant operational load rather than a seasonal spike operation. Spikes that do appear are usually a single high-volume category (solid waste, overgrown lots) rather than a citywide surge.

## 2. SLA compliance is high overall, but the average hides a tail

**92.4% of closed requests were closed on time**, measured against the city's own `Late (Yes/No)` verdict — 439,883 on time out of 476,299 with a verdict.

The distribution across departments is where the story is:

- Metro Health (97.5%) and Development Services (96.4%) run tight processes with clear deadlines.
- Solid Waste (95.2%) and Public Works (94.5%) handle the biggest volume and still clear most work on time.
- **Historic Preservation (66.0%)** is the clear outlier — roughly one in three of its closed cases missed its deadline.
- Animal Care (80.0%) and the 311 call center itself (82.0%) sit well below the citywide figure.

A single citywide "92%" would let a resident conclude their case will be handled on time regardless of what it is. Department-level reporting is the difference between a vanity metric and an operational one.

## 3. Most work closes fast; a small share drags

Median time to close is **1.8 days**. That matters more than the mean here: close times have a long right tail, and a handful of records open for hundreds of days would pull an average far above what a typical request experiences. The median says the typical case is handled in under two days.

## 4. The backlog is small but real

**25,424 requests (5.1%) remain open** at the end of the window. That is a manageable figure against 502k received, but it is the number that determines whether residents call back. Tracking it monthly — rather than as a year-end total — is what turns it into a management metric.

## 5. District volume follows population, not failure

District 5 leads at **60.1k** requests, ahead of Districts 2 and 3. High counts in a district mostly reflect how many people live there and how old the housing stock is (older homes generate more property-maintenance and solid-waste calls). Volume alone is not evidence of a service problem; pairing it with on-time rates per district would be the next cut.

## What I would add with a client's own data

This public dataset is a single rolling year with no cost, staffing or satisfaction fields. On a client's export the same layout would extend to:

- Cost or hours per request, to find the expensive categories rather than just the frequent ones.
- Staffing or shift data, to test whether late cases cluster on particular days or crews.
- Reopen rate, which separates "closed" from "fixed".
- Resident satisfaction or callback data, to see whether speed actually correlates with the experience.
- Multi-year history, which is what unlocks year-over-year deltas and seasonality properly. The public 311 file cannot support YoY, which is why this dashboard does not show one.

## Method summary

| Question | Field | Rule |
|---|---|---|
| How much work came in? | `OPENEDDATETIME` | Rows opened in the trailing 365 days |
| Was it on time? | `Late (Yes/No)` | `NO` ÷ (`YES` + `NO`), closed cases only |
| How long did it take? | `CLOSEDDATETIME − OPENEDDATETIME` | Median, filtered to 0–400 days |
| What is still open? | `CASESTATUS` | `OPEN` at end of window |

Every figure above is recomputed on each render and written to `output/metrics.json`, so the write-up can be checked against the data rather than trusted.
