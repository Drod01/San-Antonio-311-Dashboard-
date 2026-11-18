# data/

The source CSV is **not** stored in this repository. It is about 172 MB, and the City of San Antonio replaces it daily, so a committed copy would be stale within a day and would bloat every clone.

Fetch the current file:

```bash
python scripts/download_data.py
```

That creates:

- `311_all.csv` — the full `ALL SERVICE CALLS` extract (514,891 records at the time of writing)
- `metadata.json` — the license, resource id, last-modified timestamp, byte count and citation for exactly the file you downloaded

Both are gitignored. `build_dashboard.py` reads `311_all.csv` from this folder by default; pass `--csv` to use a copy kept elsewhere.

Source: https://data.sanantonio.gov/dataset/311-service-calls (CC BY, City of San Antonio).
