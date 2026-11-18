#!/usr/bin/env python3
"""
Render the San Antonio 311 operations dashboard.

Source data (CC BY, City of San Antonio):
https://data.sanantonio.gov/dataset/311-service-calls

Usage:
    python build_dashboard.py
    python build_dashboard.py --csv /path/to/allservicecalls.csv --out /tmp/charts

Outputs:
    output/san_antonio_311_dashboard.png   1280 x 769 dashboard
    output/metrics.json                    every figure on the page
"""

import argparse
import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parent

BG = "#0E1B2C"
PANEL = "#16273D"
PANEL_EDGE = "#22354E"
TXT = "#E8EEF6"
MUTE = "#8FA3BC"
TEAL = "#38BDF8"
AMBER = "#F5A524"
GREEN = "#34D399"
RED = "#F87171"

COLS = ["OPENEDDATETIME", "CLOSEDDATETIME", "Late (Yes/No)", "Dept",
        "TYPENAME", "CASESTATUS", "COUNCIL_DIST"]


def load(csv_path: Path) -> pd.DataFrame:
    d = pd.read_csv(csv_path, usecols=COLS)
    d["opened"] = pd.to_datetime(d["OPENEDDATETIME"], errors="coerce")
    d["closed"] = pd.to_datetime(d["CLOSEDDATETIME"], errors="coerce")
    return d.dropna(subset=["opened"])


def compute(d: pd.DataFrame) -> dict:
    """Rolling 12 months ending on the newest date present in the file."""
    end = d["opened"].max().normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    start = end - pd.DateOffset(years=1)
    cur = d[(d["opened"] > start) & (d["opened"] <= end)]

    closed = cur[cur["CASESTATUS"] == "CLOSED"]
    late = int((closed["Late (Yes/No)"] == "YES").sum())
    ontime = int((closed["Late (Yes/No)"] == "NO").sum())
    on_time_pct = ontime / max(ontime + late, 1) * 100

    days = (closed["closed"] - closed["opened"]).dt.total_seconds() / 86400
    median_days = float(days[(days >= 0) & (days < 400)].median())

    open_now = int((cur["CASESTATUS"] == "OPEN").sum())
    vol = len(cur)
    per_day = vol / 365

    # monthly trend: drop partial first/last buckets so the line does not lie
    monthly = (cur.groupby(cur["opened"].dt.to_period("M"))
                  .size().sort_index().iloc[1:-1])
    monthly.index = monthly.index.to_timestamp()

    # on-time by department (closed cases with an SLA verdict only)
    dep = closed[closed["Late (Yes/No)"].isin(["YES", "NO"])]
    dep_g = dep.groupby("Dept")["Late (Yes/No)"].agg(
        total="size", ontime=lambda s: (s == "NO").sum())
    dep_g["pct"] = dep_g["ontime"] / dep_g["total"] * 100
    dep_g = dep_g.sort_values("pct", ascending=True).tail(8)

    types = (cur[cur["TYPENAME"].notna()]
             .groupby("TYPENAME").size().sort_values(ascending=False).head(7))

    cd = cur[cur["COUNCIL_DIST"].between(1, 10)].groupby("COUNCIL_DIST").size()

    return dict(cur=cur, closed=closed, ontime=ontime, late=late,
                on_time_pct=on_time_pct, median_days=median_days,
                open_now=open_now, vol=vol, per_day=per_day, end=end,
                start=start, monthly=monthly, dep=dep_g, types=types, cd=cd,
                records=len(d))


def nice_type(t: str) -> str:
    t = str(t).split("/")
    t = max(t, key=len).strip()               # "Overgrown Yard/Trash" -> "Overgrown Yard"
    return t if len(t) <= 22 else t[:21].rstrip() + "\u2026"


DISPLAY = {
    "Carts(Damaged Cart)": "Damaged Cart",
    "Carts(Lost-Stolen)": "Lost/Stolen Cart",
    "Animals(Stray Animal)": "Stray Animal",
    "Animals(Aggressive Non-Critical)": "Aggressive Animal",
}


def render(s: dict, out: Path) -> Path:
    fig = plt.figure(figsize=(12.8, 7.69), dpi=200)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    def panel(x, y, w, h, r=0.012):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                     boxstyle=f"round,pad=0,rounding_size={r}",
                     facecolor=PANEL, edgecolor=PANEL_EDGE, linewidth=1.1, zorder=1))

    def sub(rect):
        return fig.add_axes(rect)

    # ---------- header ----------
    ax.text(0.028, 0.952, "CITY OF SAN ANTONIO  \u00b7  311 SERVICE OPERATIONS",
            color=TXT, fontsize=15.5, fontweight="bold", va="center")
    ax.text(0.028, 0.902,
            f"Rolling 12 months ending {s['end']:%b %d, %Y}   \u00b7   "
            f"{s['records']:,} records in dataset   \u00b7   Source: data.sanantonio.gov",
            color=MUTE, fontsize=9.2, va="center")
    ax.add_patch(Rectangle((0.028, 0.876), 0.944, 0.0016, color=PANEL_EDGE, zorder=2))
    ax.text(0.972, 0.952, "OPERATIONS OVERVIEW", color=TEAL, fontsize=8.4,
            fontweight="bold", va="center", ha="right")

    # ---------- KPI cards ----------
    kpis = [
        ("SERVICE REQUESTS", f"{s['vol']:,}",
         f"about {s['per_day']:,.0f} new requests per day", TEAL),
        ("CLOSED ON TIME", f"{s['on_time_pct']:.1f}%",
         f"{s['ontime']:,} of {s['ontime'] + s['late']:,} closed", GREEN),
        ("MEDIAN DAYS TO CLOSE", f"{s['median_days']:.1f}",
         "from opened to closed", AMBER),
        ("OPEN BACKLOG", f"{s['open_now']:,}",
         f"{s['open_now'] / s['vol'] * 100:.1f}% of requests still open", RED),
    ]
    cx0, cw, gap = 0.028, 0.2255, 0.0145
    for i, (label, value, note, color) in enumerate(kpis):
        x = cx0 + i * (cw + gap)
        panel(x, 0.665, cw, 0.19)
        ax.add_patch(Rectangle((x + 0.012, 0.833), 0.026, 0.0032, color=color, zorder=3))
        ax.text(x + 0.014, 0.806, label, color=MUTE, fontsize=7.6,
                fontweight="bold", va="center")
        ax.text(x + 0.014, 0.742, value, color=TXT, fontsize=25,
                fontweight="bold", va="center")
        ax.text(x + 0.014, 0.694, note, color=color, fontsize=7.4, va="center")

    # ---------- monthly trend ----------
    monthly = s["monthly"]
    panel(0.028, 0.345, 0.545, 0.295)
    ax.text(0.045, 0.607, "Monthly request volume", color=TXT,
            fontsize=10.5, fontweight="bold", va="center")
    ax.text(0.045, 0.574,
            f"{monthly.index[0]:%b %Y} \u2013 {monthly.index[-1]:%b %Y}  \u00b7  all departments",
            color=MUTE, fontsize=7.6, va="center")
    a = sub([0.055, 0.372, 0.495, 0.185])
    xs = np.arange(len(monthly))
    a.plot(xs, monthly.values, color=TEAL, linewidth=1.9, zorder=4)
    a.fill_between(xs, monthly.values, monthly.values.min() * 0.94,
                   color=TEAL, alpha=0.18, zorder=3)
    a.set_facecolor(PANEL)
    a.set_xlim(-0.5, len(monthly) - 0.5)
    a.set_ylim(monthly.values.min() * 0.94, monthly.values.max() * 1.06)
    a.grid(axis="y", color=PANEL_EDGE, linewidth=0.9, zorder=0)
    a.set_axisbelow(True)
    for sp in a.spines.values():
        sp.set_visible(False)
    ticks = list(range(len(monthly.index)))
    a.set_xticks(ticks)
    a.set_xticklabels([monthly.index[i].strftime("%b") for i in ticks],
                      fontsize=6.4, color=MUTE)
    a.tick_params(axis="y", colors=MUTE, labelsize=6.8, length=0)
    a.tick_params(axis="x", length=0, pad=3)
    a.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, p: f"{v/1000:.0f}k"))

    # ---------- on-time by department ----------
    dep = s["dep"]
    panel(0.588, 0.345, 0.384, 0.295)
    ax.text(0.605, 0.607, "On-time closure by department", color=TXT,
            fontsize=10.5, fontweight="bold", va="center")
    ax.text(0.605, 0.574, "share of closed requests met within SLA",
            color=MUTE, fontsize=7.6, va="center")
    b = sub([0.742, 0.365, 0.212, 0.196])
    labels = [l.replace("Solid Waste Services", "Solid Waste")
               .replace("Traffic Signals and Signs", "Traffic Signals")
               .replace("Streets & Infrastructure", "Streets & Infra")
               .replace("Parks and Recreation", "Parks & Rec")
               .replace("Animal Care Services", "Animal Care")
               .replace("Health_Sanitation", "Health & Sanitation")
              for l in dep.index]
    colors = [GREEN if v >= 85 else AMBER if v >= 70 else RED for v in dep["pct"]]
    b.barh(range(len(dep)), dep["pct"], color=colors, height=0.62, zorder=3)
    b.set_facecolor(PANEL)
    b.set_yticks(range(len(dep)))
    b.set_yticklabels(labels, fontsize=6.9, color=TXT)
    b.set_xlim(0, 118)
    b.grid(axis="x", color=PANEL_EDGE, linewidth=0.8, zorder=0)
    b.set_axisbelow(True)
    for sp in b.spines.values():
        sp.set_visible(False)
    b.tick_params(axis="x", labelsize=6.4, colors=MUTE, length=0, pad=2)
    b.tick_params(axis="y", length=0)
    b.set_xticks([0, 25, 50, 75, 100])
    b.xaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:.0f}%"))
    for i, v in enumerate(dep["pct"]):
        b.text(v + 2.5, i, f"{v:.0f}%", va="center", fontsize=6.6, color=TXT, zorder=5)

    # ---------- top request types ----------
    types = s["types"].copy()
    types.index = [DISPLAY.get(x, nice_type(x)) for x in types.index]
    panel(0.028, 0.038, 0.30, 0.283)
    ax.text(0.043, 0.288, "Top request types", color=TXT,
            fontsize=10.5, fontweight="bold", va="center")
    ax.text(0.043, 0.256, "last 12 months", color=MUTE, fontsize=7.6, va="center")
    c = sub([0.122, 0.062, 0.130, 0.183])
    c.barh(range(len(types))[::-1], types.values, color=TEAL, height=0.6, zorder=3)
    c.set_facecolor(PANEL)
    c.set_yticks(range(len(types))[::-1])
    c.set_yticklabels(types.index, fontsize=6.2, color=TXT)
    c.set_xlim(0, types.values.max() * 1.18)
    c.grid(axis="x", color=PANEL_EDGE, linewidth=0.8, zorder=0)
    c.set_axisbelow(True)
    for sp in c.spines.values():
        sp.set_visible(False)
    c.tick_params(axis="x", labelsize=6.3, colors=MUTE, length=0, pad=2)
    c.tick_params(axis="y", length=0)
    c.xaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, p: f"{v/1000:.1f}k" if v else "0"))
    for i, v in zip(range(len(types))[::-1], types.values):
        c.text(v + types.values.max() * 0.03, i, f"{v:,}",
               va="center", fontsize=6.4, color=MUTE)

    # ---------- council districts ----------
    cd = s["cd"]
    panel(0.342, 0.038, 0.315, 0.283)
    ax.text(0.357, 0.288, "Requests by council district", color=TXT,
            fontsize=10.5, fontweight="bold", va="center")
    ax.text(0.357, 0.256, "volume tracks population and housing age",
            color=MUTE, fontsize=7.6, va="center")
    e = sub([0.360, 0.062, 0.272, 0.183])
    idx, vals = list(cd.index), list(cd.values)
    e.bar(range(len(idx)), vals,
          color=[AMBER if v == max(vals) else "#2F4B6B" for v in vals],
          width=0.62, zorder=3)
    e.set_facecolor(PANEL)
    e.set_xticks(range(len(idx)))
    e.set_xticklabels([str(i) for i in idx], fontsize=6.6, color=MUTE)
    e.set_xlabel("district", fontsize=6.2, color=MUTE, labelpad=1)
    e.set_ylim(0, max(vals) * 1.20)
    e.grid(axis="y", color=PANEL_EDGE, linewidth=0.8, zorder=0)
    e.set_axisbelow(True)
    for sp in e.spines.values():
        sp.set_visible(False)
    e.tick_params(axis="y", labelsize=6.3, colors=MUTE, length=0, pad=2)
    e.tick_params(axis="x", length=0, pad=2)
    e.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, p: f"{v/1000:.0f}k" if v else "0"))
    for i, v in enumerate(vals):
        e.text(i, v + max(vals) * 0.025, f"{v/1000:.1f}k",
               ha="center", fontsize=6.3, color=MUTE)

    # ---------- status mix ----------
    panel(0.670, 0.038, 0.302, 0.283)
    ax.text(0.685, 0.288, "Where the year went", color=TXT,
            fontsize=10.5, fontweight="bold", va="center")
    ax.text(0.685, 0.256, "final status of 12-month requests",
            color=MUTE, fontsize=7.6, va="center")
    f = sub([0.678, 0.052, 0.125, 0.192])
    f.set_facecolor(PANEL)
    parts = [s["ontime"], s["late"], s["open_now"]]
    pcolors = [GREEN, RED, AMBER]
    f.pie(parts, colors=pcolors, startangle=90, counterclock=False,
          wedgeprops=dict(width=0.36, edgecolor=PANEL, linewidth=2.2))
    f.set_aspect("equal")
    f.text(0, 0, f"{s['on_time_pct']:.0f}%", ha="center", va="center",
           fontsize=15, color=TXT, fontweight="bold")
    f.text(0, -0.30, "on time", ha="center", va="center", fontsize=6.4, color=MUTE)
    for i, (lab, val, col) in enumerate(zip(["On time", "Late", "Still open"],
                                            parts, pcolors)):
        yy = 0.232 - i * 0.052
        ax.add_patch(Rectangle((0.812, yy - 0.007), 0.011, 0.014, color=col, zorder=4))
        ax.text(0.831, yy, lab, color=TXT, fontsize=7.6, va="center")
        ax.text(0.962, yy, f"{val/1000:.1f}k" if val > 1000 else f"{val:,}",
                color=MUTE, fontsize=7.6, va="center", ha="right")

    # ---------- footer ----------
    ax.text(0.028, 0.013,
            "Sample dashboard built from the City of San Antonio open data portal  \u00b7  data.sanantonio.gov",
            color="#5F7794", fontsize=6.9, va="center")
    ax.text(0.972, 0.013, "DAVID RODRIGUEZ  \u00b7  POWER BI & DATA CLEANUP",
            color="#5F7794", fontsize=6.9, va="center", ha="right", fontweight="bold")

    # Render at 2x, then downsample to the exact 1280 x 769 output size.
    out.parent.mkdir(parents=True, exist_ok=True)
    hi = out.with_name(out.stem + "@2x.png")
    fig.savefig(hi, facecolor=BG, dpi=200)
    plt.close(fig)

    with Image.open(hi) as im:
        im = im.convert("RGB").resize((1280, 769), Image.LANCZOS)
        im.save(out, optimize=True)
    hi.unlink(missing_ok=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Render the San Antonio 311 dashboard.")
    ap.add_argument("--csv", default=str(ROOT / "data" / "311_all.csv"),
                    help="path to allservicecalls.csv (default: data/311_all.csv)")
    ap.add_argument("--out", default=str(ROOT / "output"),
                    help="output directory (default: output/)")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(
            f"CSV not found: {csv_path}\n"
            "Run: python scripts/download_data.py"
        )

    out_dir = Path(args.out)
    stats = compute(load(csv_path))
    png = render(stats, out_dir / "san_antonio_311_dashboard.png")

    metrics = {
        "source": {
            "dataset": "311 Service Calls",
            "publisher": "City of San Antonio \u2014 311 City Services",
            "portal": "https://data.sanantonio.gov",
            "dataset_page": "https://data.sanantonio.gov/dataset/311-service-calls",
            "resource_id": "20eb6d22-7eac-425a-85c1-fdb365fd3cd7",
            "license": "CC BY",
            "csv": str(csv_path),
        },
        "window": {
            "start": stats["start"].isoformat(),
            "end": stats["end"].isoformat(),
            "records_in_file": int(stats["records"]),
            "requests_in_window": int(stats["vol"]),
        },
        "kpis": {
            "requests_per_day": round(float(stats["per_day"]), 1),
            "on_time_pct": round(float(stats["on_time_pct"]), 1),
            "closed_on_time": int(stats["ontime"]),
            "closed_late": int(stats["late"]),
            "median_days_to_close": round(float(stats["median_days"]), 1),
            "open_backlog": int(stats["open_now"]),
        },
        "on_time_by_department": {k: round(float(v), 1)
                                  for k, v in stats["dep"]["pct"].items()},
        "requests_by_council_district": {int(k): int(v) for k, v in stats["cd"].items()},
        "monthly_volume": {d.strftime("%Y-%m"): int(v)
                           for d, v in stats["monthly"].items()},
        "top_request_types": {str(k): int(v) for k, v in stats["types"].items()},
    }
    mpath = out_dir / "metrics.json"
    mpath.write_text(json.dumps(metrics, indent=2) + "\n")

    print(f"saved {png}")
    print(f"saved {mpath}")
    print(json.dumps(metrics["kpis"], indent=1))


if __name__ == "__main__":
    main()
