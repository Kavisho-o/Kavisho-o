"""
fetch_codechef.py

Pulls current rating, stars, and full contest rating history for a
CodeChef user and writes it to data/codechef.json.

CodeChef has no official public API, so this uses the widely-used
community endpoint (codechef-api.vercel.app), which scrapes the same
public profile page GitHub-README tools rely on. If that endpoint is
ever unreachable, the script falls back to keeping whatever was already
cached in data/codechef.json rather than wiping good data.
"""

import json
import os
import sys
import time
import requests

CODECHEF_USERNAME = os.environ.get("CODECHEF_USERNAME", "kavi_abstract")
API_URL = f"https://codechef-api.vercel.app/handle/{CODECHEF_USERNAME}"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "codechef.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; cp-stats-bot/1.0)"}


def fetch(retries: int = 3, backoff: float = 2.0) -> dict:
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(API_URL, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success", True) is False:
                return data
            raise RuntimeError(data)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"[fetch_codechef] attempt {attempt} failed: {exc}", file=sys.stderr)
            time.sleep(backoff * attempt)
    raise RuntimeError(f"Failed to fetch CodeChef data after {retries} attempts: {last_err}")


def normalize(raw: dict) -> dict:
    rating_history_raw = raw.get("ratingData") or []
    contests = []
    for entry in rating_history_raw:
        try:
            rating = float(entry.get("rating"))
        except (TypeError, ValueError):
            continue
        contests.append(
            {
                "name": entry.get("name") or entry.get("code") or "Contest",
                "end_date": entry.get("end_date"),
                "rating": rating,
                "rank": entry.get("rank"),
            }
        )

    return {
        "username": CODECHEF_USERNAME,
        "current_rating": raw.get("currentRating"),
        "highest_rating": raw.get("highestRating"),
        "stars": raw.get("stars"),
        "global_rank": raw.get("globalRank"),
        "country_rank": raw.get("countryRank"),
        "contests_count": len(contests),
        "contests": contests,
    }


def main() -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    try:
        raw = fetch()
        normalized = normalize(raw)
    except Exception as exc:  # noqa: BLE001
        print(f"[fetch_codechef] giving up, keeping cached data: {exc}", file=sys.stderr)
        if os.path.exists(OUT_PATH):
            return
        # No cache to fall back on: write an empty-but-valid structure so
        # downstream SVG generation doesn't crash on first-ever run.
        normalized = {
            "username": CODECHEF_USERNAME,
            "current_rating": None,
            "highest_rating": None,
            "stars": None,
            "global_rank": None,
            "country_rank": None,
            "contests_count": 0,
            "contests": [],
        }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2)
    print(f"[fetch_codechef] wrote {OUT_PATH} "
          f"({normalized['contests_count']} contests, rating={normalized['current_rating']})")


if __name__ == "__main__":
    main()