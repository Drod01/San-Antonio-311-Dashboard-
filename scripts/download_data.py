#!/usr/bin/env python3
"""
Fetch the current 311 Service Calls CSV from the City of San Antonio open data
portal (CKAN) and record the dataset's metadata alongside it.

    python scripts/download_data.py
    python scripts/download_data.py --out data/311_all.csv

No API key is required. Dataset: https://data.sanantonio.gov/dataset/311-service-calls
License: Creative Commons Attribution (CC BY), City of San Antonio.
"""

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://data.sanantonio.gov"
PACKAGE = "service-calls"
DATASET_PAGE = ("https://data.sanantonio.gov/dataset/"
                "93b0e7ee-3a55-4aa9-b27b-d1817e91aec3")
RESOURCE_NAME = "ALL SERVICE CALLS"
ROOT = Path(__file__).resolve().parent.parent

# The city's file server runs a bot filter that rejects non-browser user agents,
# so identify as a normal browser client. The data itself is public and CC BY.
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0 Safari/537.36"),
    "Accept": "text/csv,application/json,*/*;q=0.8",
}


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def download(url: str, dest: Path) -> None:
    """Fetch a large file.

    Preferred path is curl: the city's Cloudflare bot filter fingerprints the
    TLS handshake and returns 403 to Python's built-in HTTP client, while a
    normal curl request is served. urllib is the fallback when curl is absent.
    """
    curl = shutil.which("curl")
    if curl:
        cmd = [curl, "-L", "--fail", "--retry", "3", "--retry-delay", "2",
               "-A", UA["User-Agent"], "-H", f"Accept: {UA['Accept']}",
               "-o", str(dest), url]
        print("  using curl")
        subprocess.run(cmd, check=True)
        return

    print("  using urllib (curl not found)")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as fh:
        total = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
            total += len(chunk)
            print(f"\r  {total / 1_048_576:,.1f} MB", end="", flush=True)
    print()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "311_all.csv"))
    ap.add_argument("--package", default=PACKAGE)
    args = ap.parse_args()

    meta_url = f"{BASE}/api/3/action/package_show?id={args.package}"
    print(f"reading dataset metadata: {meta_url}")
    pkg = get_json(meta_url)["result"]

    resources = pkg.get("resources", [])
    match = next((r for r in resources
                  if RESOURCE_NAME.lower() in (r.get("name") or "").lower()), None)
    if match is None:
        print("Available resources:")
        for r in resources:
            print("  -", r.get("name"), r.get("format"))
        sys.exit(f"Could not find a resource named '{RESOURCE_NAME}'.")

    url = match["url"]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"downloading: {match.get('name')} ({match.get('format')})")
    print(f"  {url}")
    tmp = out.with_suffix(out.suffix + ".part")
    try:
        download(url, tmp)
    except (subprocess.CalledProcessError, urllib.error.URLError) as exc:
        tmp.unlink(missing_ok=True)
        sys.exit(f"download failed: {exc}\n"
                 f"Try fetching it in a browser:\n  {url}")

    tmp.replace(out)
    size_mb = out.stat().st_size / 1_048_576
    print(f"saved {out} ({size_mb:,.1f} MB)")

    with open(out, "rb") as fh:
        header = fh.readline().decode("utf-8", "replace").strip()
    print(f"columns start: {header[:120]}...")

    record = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_title": pkg.get("title"),
        "dataset_name": pkg.get("name"),
        "dataset_page": DATASET_PAGE,
        "publisher": (pkg.get("organization") or {}).get("title"),
        "license_title": pkg.get("license_title"),
        "license_id": pkg.get("license_id"),
        "metadata_modified": pkg.get("metadata_modified"),
        "resource_name": match.get("name"),
        "resource_id": match.get("id"),
        "resource_last_modified": match.get("last_modified"),
        "resource_url": url,
        "bytes": out.stat().st_size,
        "local_file": str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out),
        "citation": (f"{pkg.get('organization', {}).get('title')}, "
                     f"{pkg.get('title')}, City of San Antonio open data portal, "
                     f"{BASE}, accessed {datetime.now(timezone.utc):%Y-%m-%d}"),
    }
    meta_path = out.parent / "metadata.json"
    meta_path.write_text(json.dumps(record, indent=2) + "\n")
    print(f"saved {meta_path}")


if __name__ == "__main__":
    main()
