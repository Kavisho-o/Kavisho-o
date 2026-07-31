"""
generate_stats_strip.py

Renders one small, humble stats row (not a dashboard) summarizing the
LeetCode profile: current rating, peak rating, ranking, problems solved,
contests attended. Output: assets/leetcode_stats.svg
"""

import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leetcode.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "leetcode_stats.svg")

TEXT_COLOR = "#e0e0e0"
LABEL_COLOR = "#8b8f98"
ACCENT = "#F48FB1"


def fmt(v, default="—"):
    return default if v is None else v


def main() -> None:
    with open(DATA_PATH, encoding="utf-8") as f:
        d = json.load(f)

    items = [
        ("Rating", fmt(d.get("current_rating"))),
        ("Peak", fmt(d.get("peak_rating"))),
        ("Ranking", f'#{d["global_ranking"]}' if d.get("global_ranking") else "—"),
        ("Solved", fmt(d.get("total_solved"))),
        ("Contests", fmt(d.get("attended_contests_count"))),
    ]

    width, height = 900, 54
    col_w = width / len(items)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" '
        f'height="{height}" font-family="Segoe UI, Helvetica, Arial, sans-serif">'
    ]
    for i, (label, value) in enumerate(items):
        cx = col_w * i + col_w / 2
        parts.append(
            f'<text x="{cx:.1f}" y="24" text-anchor="middle" font-size="18" font-weight="600" '
            f'fill="{ACCENT}">{value}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="42" text-anchor="middle" font-size="10.5" letter-spacing="0.5" '
            f'fill="{LABEL_COLOR}">{label.upper()}</text>'
        )
        if i > 0:
            parts.append(
                f'<line x1="{col_w * i:.1f}" y1="10" x2="{col_w * i:.1f}" y2="{height - 10}" '
                f'stroke="#232833" stroke-width="1"/>'
            )
    parts.append("</svg>")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print(f"[generate_stats_strip] wrote {OUT_PATH}")


if __name__ == "__main__":
    main()