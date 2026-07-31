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
import re
import sys
import time
import requests

CODECHEF_USERNAME = os.environ.get("CODECHEF_USERNAME", "kavi_abstract")
PRIMARY_URL = f"https://codechef-api.vercel.app/handle/{CODECHEF_USERNAME}"
# Fallback only covers current rating / stars / contest count, no rating
# history, but it keeps the stats strip alive if the primary source is
# temporarily blocking requests from GitHub's IP ranges.
FALLBACK_URL = f"https://codechef-stats-api-two.vercel.app/{CODECHEF_USERNAME}/profile"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "codechef.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}


def _get_json(url: str, retries: int = 3, backoff: float = 2.5) -> dict:
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=25)
            print(f"[fetch_codechef] GET {url} -> HTTP {resp.status_code}", file=sys.stderr)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"[fetch_codechef] attempt {attempt} on {url} failed: {exc}", file=sys.stderr)
            time.sleep(backoff * attempt)
    raise RuntimeError(f"Failed after {retries} attempts against {url}: {last_err}")


def _parse_stars(raw_stars) -> int | None:
    """Handles '4★', '4 Star', 4, '4', etc."""
    if raw_stars is None:
        return None
    digits = re.sub(r"[^0-9]", "", str(raw_stars))
    return int(digits) if digits else None


def normalize_primary(raw: dict) -> dict:
    if raw.get("success") is False:
        raise RuntimeError(f"API responded with success=false: {raw}")

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
        "stars": _parse_stars(raw.get("stars")),
        "global_rank": raw.get("globalRank"),
        "country_rank": raw.get("countryRank"),
        "contests_count": len(contests),
        "contests": contests,
    }


def normalize_fallback(raw: dict) -> dict:
    data = raw.get("data") or {}
    return {
        "username": CODECHEF_USERNAME,
        "current_rating": data.get("currentRating"),
        "highest_rating": data.get("maxRating"),
        "stars": _parse_stars(data.get("rank")),
        "global_rank": None,
        "country_rank": None,
        "contests_count": data.get("totalContests") or 0,
        "contests": [],  # fallback source has no per-contest rating history
    }


def main() -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    normalized = None

    try:
        raw = _get_json(PRIMARY_URL)
        normalized = normalize_primary(raw)
        print("[fetch_codechef] primary source succeeded", file=sys.stderr)
    except Exception as primary_exc:  # noqa: BLE001
        print(f"[fetch_codechef] primary source failed: {primary_exc}", file=sys.stderr)
        try:
            raw = _get_json(FALLBACK_URL)
            normalized = normalize_fallback(raw)
            print("[fetch_codechef] fallback source succeeded "
                  "(note: no contest rating history from this source)", file=sys.stderr)
        except Exception as fallback_exc:  # noqa: BLE001
            print(f"[fetch_codechef] fallback source also failed: {fallback_exc}", file=sys.stderr)

    if normalized is None:
        if os.path.exists(OUT_PATH):
            print("[fetch_codechef] both sources failed, keeping previously cached data",
                  file=sys.stderr)
            return
        print("[fetch_codechef] both sources failed and no cache exists, "
              "writing empty placeholder", file=sys.stderr)
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