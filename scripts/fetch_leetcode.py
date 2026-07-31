"""
fetch_leetcode.py

Pulls profile stats, the submission-calendar (for the heatmap) and the
complete contest rating history for a LeetCode user via LeetCode's public
GraphQL endpoint, and writes everything to data/leetcode.json.

No API key is required. LeetCode does require a browser-like User-Agent
and a matching Referer header or the request is rejected.
"""

import json
import os
import sys
import time
import requests

LEETCODE_USERNAME = os.environ.get("LEETCODE_USERNAME", "kavish0_0")
GRAPHQL_URL = "https://leetcode.com/graphql"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leetcode.json")

HEADERS = {
    "Content-Type": "application/json",
    "Referer": f"https://leetcode.com/{LEETCODE_USERNAME}/",
    "User-Agent": "Mozilla/5.0 (compatible; cp-stats-bot/1.0)",
}

QUERY = """
query userPublicProfile($username: String!) {
  matchedUser(username: $username) {
    username
    profile {
      ranking
      realName
    }
    submitStats {
      acSubmissionNum {
        difficulty
        count
      }
    }
    submissionCalendar
  }
  userContestRanking(username: $username) {
    attendedContestsCount
    rating
    globalRanking
    totalParticipants
    topPercentage
  }
  userContestRankingHistory(username: $username) {
    attended
    rating
    ranking
    trendDirection
    problemsSolved
    totalProblems
    contest {
      title
      startTime
    }
  }
}
"""


def fetch(retries: int = 3, backoff: float = 2.0) -> dict:
    payload = {
        "query": QUERY,
        "variables": {"username": LEETCODE_USERNAME},
        "operationName": "userPublicProfile",
    }
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                raise RuntimeError(data["errors"])
            return data["data"]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"[fetch_leetcode] attempt {attempt} failed: {exc}", file=sys.stderr)
            time.sleep(backoff * attempt)
    raise RuntimeError(f"Failed to fetch LeetCode data after {retries} attempts: {last_err}")


def normalize(raw: dict) -> dict:
    matched_user = raw.get("matchedUser") or {}
    submit_stats = (matched_user.get("submitStats") or {}).get("acSubmissionNum") or []
    solved_by_difficulty = {
        row["difficulty"]: row["count"]
        for row in submit_stats
    }
    contest_ranking = raw.get("userContestRanking") or {}
    history_raw = raw.get("userContestRankingHistory") or []

    # Keep only contests the user actually attended, sorted chronologically.
    attended = [c for c in history_raw if c.get("attended")]
    attended.sort(key=lambda c: c["contest"]["startTime"])

    contests = []
    prev_rating = None
    for c in attended:
        rating = round(c["rating"], 1)
        delta = round(rating - prev_rating, 1) if prev_rating is not None else 0.0
        contests.append(
            {
                "name": c["contest"]["title"],
                "start_time": c["contest"]["startTime"],
                "rating_after": rating,
                "rating_before": prev_rating if prev_rating is not None else rating,
                "delta": delta,
                "ranking": c.get("ranking"),
            }
        )
        prev_rating = rating

    peak_rating = max((c["rating_after"] for c in contests), default=0)

    return {
        "username": LEETCODE_USERNAME,
        "ranking": (matched_user.get("profile") or {}).get("ranking"),
        "total_solved": solved_by_difficulty.get("All", 0),
        "solved_by_difficulty": solved_by_difficulty,
        "current_rating": round(contest_ranking.get("rating", 0), 1) if contest_ranking else None,
        "peak_rating": peak_rating,
        "global_ranking": contest_ranking.get("globalRanking"),
        "top_percentage": contest_ranking.get("topPercentage"),
        "attended_contests_count": contest_ranking.get("attendedContestsCount", len(contests)),
        "submission_calendar": json.loads(matched_user.get("submissionCalendar") or "{}"),
        "contests": contests,
    }


def main() -> None:
    raw = fetch()
    normalized = normalize(raw)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2)
    print(f"[fetch_leetcode] wrote {OUT_PATH} "
          f"({len(normalized['contests'])} contests, rating={normalized['current_rating']})")


if __name__ == "__main__":
    main()