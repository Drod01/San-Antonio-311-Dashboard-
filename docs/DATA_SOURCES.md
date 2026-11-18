# Data sources

One dataset. Public, free, no key, no scraping.

## Primary source

| Field | Value |
|---|---|
| Title | 311 Service Calls |
| Publisher | City of San Antonio — 311 City Services (`311-city-services`) |
| Portal | https://data.sanantonio.gov |
| Dataset page | https://data.sanantonio.gov/dataset/93b0e7ee-3a55-4aa9-b27b-d1817e91aec3 |
| Portal browse page | https://data.sanantonio.gov |
| CKAN package id | `service-calls` |
| Resource used | `ALL SERVICE CALLS` (CSV) |
| Resource id | `20eb6d22-7eac-425a-85c1-fdb365fd3cd7` |
| Direct URL | https://data.sanantonio.gov/dataset/93b0e7ee-3a55-4aa9-b27b-d1817e91aec3/resource/20eb6d22-7eac-425a-85c1-fdb365fd3cd7/download/allservicecalls.csv |
| License | Creative Commons Attribution (`cc-by`) |
| Dataset created | 2018-05-08 |
| Dataset last modified | 2026-11-15 |
| Pulled for this project | 2026-11-18 |
| Records in file | 514,891 |
| Dataset contact | 311CustomerService@sanantonio.gov |
| Data dictionary | https://data.sanantonio.gov/dataset/93b0e7ee-3a55-4aa9-b27b-d1817e91aec3/resource/0eab0cfc-a114-4064-9f25-d088d8ac46a3/download/datadictionary-311.xlsx |

Publisher's description, verbatim:

> 311 Customer Service connects citizens with specially-trained customer service representatives ready to assist and facilitate City services including animals, potholes, solid waste collection, property maintenance, downed trees, etc. See more Online Service Requests at www.sanantonio.gov/311. NOTE: Data represents the past 365 days of the last upload date.

That note drives the whole analysis: the file is a **rolling 365-day snapshot**, not a historical archive.

## How the file was obtained

The portal runs CKAN, so the metadata is available as JSON before any download:

```bash
# dataset metadata (title, license, resources, last modified)
curl "https://data.sanantonio.gov/api/3/action/package_show?id=service-calls"

# search for a dataset by keyword
curl "https://data.sanantonio.gov/api/3/action/package_search?q=311"
```

`scripts/download_data.py` does exactly this: it reads `package_show`, picks the resource named `ALL SERVICE CALLS`, streams the CSV to `data/311_all.csv`, and writes `data/metadata.json` containing the license, resource id, last-modified timestamp, byte count and a ready-made citation string. That metadata file is the provenance record for any render.

Note that this portal is CKAN, not Socrata — Socrata-style endpoints (`/resource/*.json`, `$limit`) do not exist here.

## Related resources in the same dataset

The portal also publishes per-category extracts. They are subsets of the file used here, useful if you want to reproduce a single department's slice:

| Resource | Resource id |
|---|---|
| SERVICE CALLS RELATED TO ANIMALS | `e77257d9-79af-4ac8-a794-6470e01f9f23` |
| SERVICE CALLS RELATED TO HEALTH AND SANITATION | `9776e2f3-496e-455d-8be0-11e9589d744a` |
| SERVICE CALLS RELATED TO PARKS | `4355b7ef-e13f-487f-b5bc-dc033f87d6bf` |
| SERVICE CALLS RELATED TO SOLID WASTE | `e920e832-da53-43ee-ae7f-8b8681d6181c` |
| SERVICE CALLS RELATED TO STREETS AND INFRASTRUCTURE | `00370431-ce2d-4b32-9b75-b9734bd13fa3` |
| SERVICE CALLS RELATED TO TRAFFIC SIGNALS AND SIGNS | `4880d50a-6c68-4769-a0d3-9b24e04e99c3` |
| SERVICE CALLS RELATED TO PROPERTY MAINTENANCE | `8cb8d6c9-93df-4c7a-b897-85793b21c60e` |
| SERVICE CALLS RELATED TO GRAFFITI | `2b45efc0-196c-4269-ab82-7499f98ca384` |

## Fields used

| Column | What it means | How it is used |
|---|---|---|
| `OPENEDDATETIME` | When the request was created | Defines the 12-month window; drives the monthly trend; start of cycle time |
| `CLOSEDDATETIME` | When the request was closed | End of cycle time; median days to close |
| `SLA_Date` | The deadline the city committed to | Reference only — compliance is taken from `Late (Yes/No)` |
| `Late (Yes/No)` | `YES` / `NO` / blank verdict on SLA compliance | The on-time percentage and the on-time-by-department chart |
| `Dept` | Owning department | Department ranking |
| `TYPENAME` | Request type | Top request types |
| `CASESTATUS` | `OPEN`, `CLOSED`, etc. | Open backlog and status mix |
| `COUNCIL_DIST` | Council district 1–10 | Volume by district |

Columns present but not used: `CASEID`, `REASONNAME`, `SOURCEID`, `OBJECTDESC`, `XY`, `Category`, `SUBSTATUS`, `STREETNAME`, `CITY`, `STATE`, `ZIP`, and address fields. No personally identifying information from the dataset appears in this repository — the charts show aggregates only.

## Citation

City of San Antonio, *311 Service Calls*, City of San Antonio Open Data Portal,
https://data.sanantonio.gov/dataset/93b0e7ee-3a55-4aa9-b27b-d1817e91aec3,
accessed 2026-11-18.
Licensed CC BY.

In a report or slide deck, use:

> Source: City of San Antonio Open Data Portal, "311 Service Calls" (data.sanantonio.gov), accessed November 18, 2026. CC BY.

## Accuracy notes

- The city updates the file daily, so totals in this repository will drift from the live portal over time. `output/metrics.json` records the exact window and record count behind any render.
- Dates are treated as naive local timestamps; no timezone conversion is applied.
- A small number of rows have no `CLOSEDDATETIME` while marked closed, or a negative duration. They are excluded from the median by the 0–400 day filter rather than silently clipped to zero.
- Department names are the city's raw system values, including a few inconsistent ones (`Health_Sanitation`). Display labels are shortened for the chart only; the underlying values are unchanged.
