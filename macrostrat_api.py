#!/usr/bin/env python3
"""
Macrostrat API script
---------------------
Fetches stratigraphic units near a chosen location, summarizes lithology and
geologic age, prints a compact report, saves a CSV of selected fields, and
plots a simple time-vs-thickness "column" chart.

API docs: https://macrostrat.org/api
"""

from __future__ import annotations

import csv
import os
from collections import Counter
from typing import Any

import matplotlib.pyplot as plt
import requests

BASE_URL = "https://macrostrat.org/api/v2"
# Madison, WI — Macrostrat's home turf; rich Paleozoic section
LAT, LNG = 43.07, -89.40
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def fetch_units(lat: float, lng: float) -> list[dict[str, Any]]:
    """Pull Macrostrat units at (or near) a lat/lng."""
    params = {
        "lat": lat,
        "lng": lng,
        "response": "long",
        "format": "json",
    }
    url = f"{BASE_URL}/units"
    print(f"GET {url}")
    print(f"  params: {params}")
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    units = payload.get("success", {}).get("data", [])
    if not isinstance(units, list):
        raise ValueError("Unexpected Macrostrat response shape")
    return units


def primary_lith(unit: dict[str, Any]) -> str:
    liths = unit.get("lith") or []
    if not liths:
        return "unknown"
    # Prefer the lithology with the highest proportion when available
    best = max(liths, key=lambda L: L.get("prop") or 0)
    return best.get("name") or "unknown"


def primary_environ(unit: dict[str, Any]) -> str:
    envs = unit.get("environ") or []
    if not envs:
        return "unknown"
    return envs[0].get("name") or "unknown"


def summarize(units: list[dict[str, Any]]) -> None:
    """Print selected highlights — not the raw API dump."""
    named = [u for u in units if (u.get("unit_name") or "").strip() not in ("", "Unnamed")]
    lith_counts = Counter(primary_lith(u) for u in units)
    env_counts = Counter(primary_environ(u) for u in units)

    oldest = max(units, key=lambda u: u.get("b_age") or 0)
    youngest = min(units, key=lambda u: u.get("t_age") or 1e9)
    fossil_rich = sorted(
        units,
        key=lambda u: (u.get("pbdb_occurrences") or 0),
        reverse=True,
    )[:5]

    print("\n=== Macrostrat units near Madison, WI ===")
    print(f"Units returned: {len(units)} ({len(named)} with formal names)")
    print(
        f"Age span: {oldest.get('b_age')} → {youngest.get('t_age')} Ma "
        f"({oldest.get('b_int_name')} → {youngest.get('t_int_name')})"
    )
    print("\nTop lithologies:")
    for name, count in lith_counts.most_common(8):
        print(f"  {name:20s}  {count}")
    print("\nTop environments:")
    for name, count in env_counts.most_common(8):
        print(f"  {name:25s}  {count}")

    print("\nMost fossil-rich units (PBDB occurrences):")
    for u in fossil_rich:
        if not (u.get("pbdb_occurrences") or 0):
            continue
        label = u.get("strat_name_long") or u.get("unit_name") or f"unit {u.get('unit_id')}"
        print(
            f"  {label[:50]:50s}  "
            f"{u.get('pbdb_occurrences'):4d} occs  "
            f"{u.get('b_age')}–{u.get('t_age')} Ma"
        )


def save_csv(units: list[dict[str, Any]], path: str) -> None:
    """Persist a curated subset of fields."""
    fields = [
        "unit_id",
        "unit_name",
        "strat_name_long",
        "b_age",
        "t_age",
        "b_int_name",
        "t_int_name",
        "max_thick",
        "min_thick",
        "lithology",
        "environment",
        "pbdb_collections",
        "pbdb_occurrences",
        "clat",
        "clng",
    ]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for u in units:
            writer.writerow(
                {
                    "unit_id": u.get("unit_id"),
                    "unit_name": u.get("unit_name"),
                    "strat_name_long": u.get("strat_name_long"),
                    "b_age": u.get("b_age"),
                    "t_age": u.get("t_age"),
                    "b_int_name": u.get("b_int_name"),
                    "t_int_name": u.get("t_int_name"),
                    "max_thick": u.get("max_thick"),
                    "min_thick": u.get("min_thick"),
                    "lithology": primary_lith(u),
                    "environment": primary_environ(u),
                    "pbdb_collections": u.get("pbdb_collections"),
                    "pbdb_occurrences": u.get("pbdb_occurrences"),
                    "clat": u.get("clat"),
                    "clng": u.get("clng"),
                }
            )
    print(f"\nSaved curated table → {path}")


def plot_column(units: list[dict[str, Any]], path: str) -> None:
    """
    Draw a stratified time column: each unit as a horizontal bar from
    bottom age → top age, colored by Macrostrat's own unit color when present.
    """
    usable = [
        u
        for u in units
        if u.get("b_age") is not None and u.get("t_age") is not None and u["b_age"] > u["t_age"]
    ]
    usable.sort(key=lambda u: u["b_age"], reverse=True)

    fig, ax = plt.subplots(figsize=(8, 10))
    for i, u in enumerate(usable):
        bottom, top = u["b_age"], u["t_age"]
        color = u.get("color") or "#888888"
        ax.barh(
            y=i,
            width=bottom - top,
            left=top,
            height=0.85,
            color=color,
            edgecolor="black",
            linewidth=0.4,
        )
        label = (u.get("strat_name_long") or u.get("unit_name") or str(u.get("unit_id")))[:32]
        mid = (bottom + top) / 2
        ax.text(mid, i, label, va="center", ha="center", fontsize=7, color=u.get("text_color") or "black")

    ax.set_yticks([])
    ax.invert_xaxis()  # older ages on the left
    ax.set_xlabel("Age (Ma)  —  older ←")
    ax.set_title(f"Macrostrat units near ({LAT}, {LNG})\ncolored by API unit color")
    ax.set_ylabel("Units (sorted oldest → youngest downward)")
    fig.tight_layout()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Saved column chart → {path}")


def plot_lithology_pie(units: list[dict[str, Any]], path: str) -> None:
    counts = Counter(primary_lith(u) for u in units)
    labels, sizes = zip(*counts.most_common()) if counts else ([], [])
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(sizes, labels=labels, autopct="%1.0f%%", startangle=90, textprops={"fontsize": 8})
    ax.set_title(f"Lithology mix near ({LAT}, {LNG})")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Saved lithology pie → {path}")


def main() -> None:
    units = fetch_units(LAT, LNG)
    if not units:
        print("No units returned for this location.")
        return

    summarize(units)
    csv_path = os.path.join(OUTPUT_DIR, "macrostrat_units_madison.csv")
    col_path = os.path.join(OUTPUT_DIR, "macrostrat_age_column.png")
    pie_path = os.path.join(OUTPUT_DIR, "macrostrat_lithology.png")
    save_csv(units, csv_path)
    plot_column(units, col_path)
    plot_lithology_pie(units, pie_path)


if __name__ == "__main__":
    main()
