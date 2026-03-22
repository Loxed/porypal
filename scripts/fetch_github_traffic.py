"""
Fetches GitHub traffic data (clones, views, release downloads) and accumulates
it in stats.json. Safe to run repeatedly -- never double-counts.

Usage:
    GITHUB_TOKEN=ghp_xxx python scripts/fetch_github_traffic.py
"""

import json
import os
from datetime import datetime
from pathlib import Path

import requests

REPO       = "loxed/porypal"
TOKEN      = os.environ["GITHUB_TOKEN"]
STATS_FILE = Path("scripts/stats.json")

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def fetch(endpoint: str) -> dict | list:
    r = requests.get(
        f"https://api.github.com/repos/{REPO}/{endpoint}",
        headers=HEADERS,
    )
    r.raise_for_status()
    return r.json()


def load_stats() -> dict:
    if STATS_FILE.exists():
        return json.loads(STATS_FILE.read_text())
    return {
        "clones":       {},
        "views":        {},
        "releases":     {},
        "last_updated": None,
    }


def save_stats(stats: dict) -> None:
    STATS_FILE.write_text(json.dumps(stats, indent=2))


def merge_traffic(existing: dict, incoming: list) -> dict:
    """Add new daily records without overwriting existing ones."""
    for day in incoming:
        date = day["timestamp"][:10]  # "2025-03-01T00:00:00Z" -> "2025-03-01"
        if date not in existing:
            existing[date] = {
                "count":   day["count"],
                "uniques": day["uniques"],
            }
    return existing


def run() -> None:
    stats = load_stats()

    print("Fetching clones...")
    clones = fetch("traffic/clones")
    stats["clones"] = merge_traffic(stats["clones"], clones.get("clones", []))

    print("Fetching views...")
    views = fetch("traffic/views")
    stats["views"] = merge_traffic(stats["views"], views.get("views", []))

    print("Fetching release downloads...")
    releases = fetch("releases")
    for release in releases:
        for asset in release.get("assets", []):
            stats["releases"][asset["name"]] = asset["download_count"]

    stats["last_updated"] = datetime.utcnow().isoformat()
    save_stats(stats)

    total_cloners  = sum(v["uniques"] for v in stats["clones"].values())
    total_clones   = sum(v["count"]   for v in stats["clones"].values())
    total_views    = sum(v["uniques"] for v in stats["views"].values())
    total_downloads = sum(stats["releases"].values())

    print(f"Done.")
    print(f"  Unique cloners:   {total_cloners}")
    print(f"  Total clones:     {total_clones}")
    print(f"  Unique views:     {total_views}")
    print(f"  Release downloads:{total_downloads}")
    print(f"  Last updated:     {stats['last_updated']}")


if __name__ == "__main__":
    run()
