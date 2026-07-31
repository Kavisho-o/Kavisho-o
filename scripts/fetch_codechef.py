"""
fetch_codechef.py

Pulls current rating, stars, and full contest rating history for a
CodeChef user and writes it to data/codechef.json.

Source history (why the fallback chain looks like this):
  - codechef-api.vercel.app (old primary) now returns HTTP 402 Payment
    Required for every handle — it's been paywalled and is effectively
    dead. Kept as a last-ditch fallback in case that ever reverses.
  - codechef-stats-api-two.vercel.app (old fallback) is alive (HTTP 200)
    but its /profile endpoint only returns bio-style fields (displayName,
    country, avatar, social links, etc) — it has NO rating/contest data
    at all. That's why the previous version always wrote rating=None and
    0 contests even on a "successful" response: there was nothing to
    parse in the first place, not a field-name mismatch.

  New primary: codechef-stats.tashif.codes — a documented, actively
  maintained community API (canonical REST surface, OpenAPI docs at
  /docs) that exposes a dedicated /{handle}/contests endpoint with real
  per-contest rating history (name, date, rating, ranking per contest),
  plus current/max rating and division rank. This is the only one of
  the three that actually returns what the contest chart needs.

If every source fails, the script preserves whatever is already cached
in data/codechef.json rather than wiping good data.
"""

import json
import os
import re
import sys
import time
import requests

CODECHEF_USERNAME = os.environ.get("CODECHEF_USERNAME", "kavi_abstract")

# New primary: documented, actively maintained, returns real per-contest
# rating history via a canonical /{handle}/contests route.
PRIMARY_URL = f"https://codechef-stats.tashif.codes/{CODECHEF_USERNAME}/contests"

# Old primary, kept as a secondary fallback in case the paywall on
# codechef-api.vercel.app is ever lifted again.
SECONDARY_URL = f"https://codechef-api.vercel.app/handle/{CODECHEF_USERNAME}"

# Old fallback. No rating/contest fields at all (bio data only) — see
# module docstring — so it can only ever contribute nothing useful, but
# it's kept last as a final network attempt before falling back to cache.
TERTIARY_URL = f"https://codechef-stats-api-two.vercel.app/{CODECHEF_USERNAME}/profile"

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "codechef.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}

# CodeChef's public star bands, used only to derive a star count from a
# rating when a source (like the new primary) reports a division name
# ("Knight", etc) instead of a star count. Approximate but stable.
STAR_BANDS = [
    (999, 1), (1399, 2), (1599, 3), (1799, 4), (1999, 5), (2199, 6),
]


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


def _stars_from_rating(rating) -> int | None:
    if rating is None:
        return None
    try:
        rating = float(rating)
    except (TypeError, ValueError):
        return None
    for ceiling, stars in STAR_BANDS:
        if rating <= ceiling:
            return stars
    return 7


def normalize_new_primary(raw: dict) -> dict:
    """codechef-stats.tashif.codes -> GET /{handle}/contests"""
    if raw.get("status") != "success":
        raise RuntimeError(f"API responded without success status: {raw}")

    data = raw.get("data") or {}
    history_raw = data.get("history") or []

    contests = []
    for entry in history_raw:
        try:
            rating = float(entry.get("rating"))
        except (TypeError, ValueError):
            continue
        contests.append(
            {
                "name": entry.get("name") or "Contest",
                "end_date": entry.get("date"),
                "timestamp": entry.get("timestamp"),
                "rating": rating,
                "rank": entry.get("ranking"),
            }
        )

    # oldest first, matching the ordering the chart/strip scripts expect
    contests.sort(key=lambda c: (c.get("timestamp") is None, c.get("timestamp") or 0))
    for c in contests:
        c.pop("timestamp", None)

    current_rating = data.get("rating")
    highest_rating = data.get("maxRating")

    return {
        "username": CODECHEF_USERNAME,
        "current_rating": current_rating,
        "highest_rating": highest_rating,
        "stars": _stars_from_rating(current_rating),
        "global_rank": data.get("globalRanking"),
        "country_rank": None,
        "contests_count": data.get("count") if data.get("count") is not None else len(contests),
        "contests": contests,
    }


def normalize_secondary(raw: dict) -> dict:
    """Old codechef-api.vercel.app /handle/{username} shape, kept as fallback."""
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


def normalize_tertiary(raw: dict) -> dict:
    """
    codechef-stats-api-two.vercel.app /{username}/profile. Verified live
    (HTTP 200) but its payload is bio/profile metadata only — no rating,
    no contests, no star/rank fields exist on this endpoint at all. This
    function intentionally cannot produce rating or contest data; it only
    confirms the handle is valid so we don't silently write garbage.
    """
    data = raw.get("data") or {}
    if not data.get("username"):
        raise RuntimeError(f"unexpected payload shape, no username field: {raw}")

    return {
        "username": CODECHEF_USERNAME,
        "current_rating": None,
        "highest_rating": None,
        "stars": None,
        "global_rank": None,
        "country_rank": None,
        "contests_count": 0,
        "contests": [],
    }


SOURCES = [
    ("primary (codechef-stats.tashif.codes)", PRIMARY_URL, normalize_new_primary),
    ("secondary (codechef-api.vercel.app)", SECONDARY_URL, normalize_secondary),
    ("tertiary (codechef-stats-api-two.vercel.app, no rating data)", TERTIARY_URL, normalize_tertiary),
]


def main() -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    normalized = None

    for label, url, normalize_fn in SOURCES:
        try:
            raw = _get_json(url)
            normalized = normalize_fn(raw)
            print(f"[fetch_codechef] {label} succeeded", file=sys.stderr)
            break
        except Exception as exc:  # noqa: BLE001
            print(f"[fetch_codechef] {label} failed: {exc}", file=sys.stderr)

    if normalized is None:
        if os.path.exists(OUT_PATH):
            print("[fetch_codechef] all sources failed, keeping previously cached data",
                  file=sys.stderr)
            return
        print("[fetch_codechef] all sources failed and no cache exists, "
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