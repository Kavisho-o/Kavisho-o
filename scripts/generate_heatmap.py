"""
generate_heatmap.py

Renders a GitHub-style submission heatmap (last 52 weeks) from
data/leetcode.json's submission_calendar, styled in the README's
baby-pink / dark-background palette, to assets/leetcode_heatmap.svg.
"""

import json
import os
from datetime import datetime, timedelta, timezone

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leetcode.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "leetcode_heatmap.svg")

# Baby-pink scale, darkest -> brightest activity, on a transparent/dark cell base.
EMPTY_COLOR = "#1b1f27"
SCALE = ["#3a2530", "#7a3a52", "#c15c81", "#F48FB1", "#F8BBD0"]

CELL = 11
GAP = 3
WEEKS = 53
DAYS = 7
LEFT_PAD = 28
TOP_PAD = 20


def bucket(count: int, thresholds) -> str:
    if count <= 0:
        return EMPTY_COLOR
    for i, t in enumerate(thresholds):
        if count <= t:
            return SCALE[i]
    return SCALE[-1]


def main() -> None:
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    calendar = {int(k): v for k, v in (data.get("submission_calendar") or {}).items()}

    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=today.weekday())  # Monday of current week
    start = start - timedelta(weeks=WEEKS - 1)

    counts = []
    max_count = 1
    for day_offset in range(WEEKS * DAYS):
        day = start + timedelta(days=day_offset)
        ts = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())
        # LeetCode buckets calendar keys to the start of the UTC day already,
        # but tolerate off-by-a-few-seconds keys by scanning a small window.
        count = 0
        for delta in range(-1, 2):
            count = calendar.get(ts + delta * 86400, 0) or count
            if count:
                break
        counts.append((day, count))
        max_count = max(max_count, count)

    thresholds = [
        max(1, round(max_count * 0.25)),
        max(2, round(max_count * 0.5)),
        max(3, round(max_count * 0.75)),
        max_count,
    ]

    width = LEFT_PAD + WEEKS * (CELL + GAP)
    height = TOP_PAD + DAYS * (CELL + GAP) + 22

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" height="{height}" font-family="Segoe UI, Helvetica, Arial, sans-serif">'
    ]

    month_labels_seen = set()
    for week in range(WEEKS):
        for day_idx in range(DAYS):
            i = week * DAYS + day_idx
            day, count = counts[i]
            x = LEFT_PAD + week * (CELL + GAP)
            y = TOP_PAD + day_idx * (CELL + GAP)
            color = bucket(count, thresholds)
            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" ry="2.5" '
                f'fill="{color}"><title>{day.isoformat()}: {count} submissions</title></rect>'
            )
            if day.day <= 7 and day.month not in month_labels_seen:
                month_labels_seen.add(day.month)
                svg_parts.append(
                    f'<text x="{x}" y="{TOP_PAD - 7}" font-size="9" fill="#8b8f98">'
                    f'{day.strftime("%b")}</text>'
                )

    # Weekday labels (Mon / Wed / Fri)
    for idx, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        y = TOP_PAD + idx * (CELL + GAP) + CELL - 2
        svg_parts.append(f'<text x="0" y="{y}" font-size="9" fill="#8b8f98">{label}</text>')

    # Legend
    legend_x = LEFT_PAD + (WEEKS - 6) * (CELL + GAP)
    legend_y = height - 4
    svg_parts.append(f'<text x="{legend_x - 30}" y="{legend_y}" font-size="9" fill="#8b8f98">Less</text>')
    for i, color in enumerate([EMPTY_COLOR] + SCALE):
        lx = legend_x + i * (CELL + GAP)
        svg_parts.append(
            f'<rect x="{lx}" y="{legend_y - CELL + 2}" width="{CELL}" height="{CELL}" '
            f'rx="2.5" ry="2.5" fill="{color}"/>'
        )
    svg_parts.append(
        f'<text x="{legend_x + 6 * (CELL + GAP) + 4}" y="{legend_y}" font-size="9" fill="#8b8f98">More</text>'
    )

    svg_parts.append("</svg>")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_parts))
    print(f"[generate_heatmap] wrote {OUT_PATH}")


if __name__ == "__main__":
    main()