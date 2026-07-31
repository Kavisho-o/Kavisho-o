"""
generate_leetcode_contest_chart.py

Renders the LeetCode contest rating journey as a "Line Chart with Data
Markers": a single smooth pink line tracing rating over every attended
contest, a soft gradient fill beneath it, and small markers colour-coded
green/pink-red for gain/loss on hover. This was chosen over the other
options (waterfall, radial spiral, HUD, ridgeline, etc.) because:

  - it reads instantly to a recruiter in ~2 seconds (a rising/falling line
    is the most universally legible way to show "growth over time")
  - it stays visually quiet at README scale, unlike bar/waterfall/HUD
    styles which get noisy once there are 30+ contests
  - a single continuous line + light area fill matches the existing
    activity-graph / streak-stats widgets already in the README, so it
    feels native to the profile instead of bolted on

Output: assets/leetcode_contest_chart.svg
"""

import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leetcode.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "leetcode_contest_chart.svg")

WIDTH, HEIGHT = 900, 260
PAD_L, PAD_R, PAD_T, PAD_B = 46, 20, 24, 30

GAIN_COLOR = "#F48FB1"
LOSS_COLOR = "#8f6b78"
LINE_COLOR = "#F48FB1"
GRID_COLOR = "#232833"
TEXT_COLOR = "#8b8f98"
BG = "transparent"


def main() -> None:
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    contests = data.get("contests") or []

    if not contests:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} 100" width="100%" height="100">'
            f'<text x="20" y="50" fill="{TEXT_COLOR}" font-family="Segoe UI, sans-serif" font-size="13">'
            f"No contest history yet.</text></svg>"
        )
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            f.write(svg)
        print("[generate_leetcode_contest_chart] no contests, wrote placeholder")
        return

    ratings = [c["rating_after"] for c in contests]
    r_min, r_max = min(ratings), max(ratings)
    pad_range = max(30, (r_max - r_min) * 0.15)
    y_min, y_max = r_min - pad_range, r_max + pad_range

    n = len(contests)
    plot_w = WIDTH - PAD_L - PAD_R
    plot_h = HEIGHT - PAD_T - PAD_B

    def x_at(i):
        return PAD_L + (plot_w if n == 1 else plot_w * i / (n - 1))

    def y_at(rating):
        return PAD_T + plot_h - (rating - y_min) / (y_max - y_min) * plot_h

    points = [(x_at(i), y_at(c["rating_after"])) for i, c in enumerate(contests)]

    line_path = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area_path = (
        line_path
        + f" L {points[-1][0]:.1f},{PAD_T + plot_h:.1f}"
        + f" L {points[0][0]:.1f},{PAD_T + plot_h:.1f} Z"
    )

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="100%" '
        f'height="{HEIGHT}" font-family="Segoe UI, Helvetica, Arial, sans-serif">',
        "<defs>",
        '<linearGradient id="lcFill" x1="0" y1="0" x2="0" y2="1">',
        f'<stop offset="0%" stop-color="{GAIN_COLOR}" stop-opacity="0.35"/>',
        f'<stop offset="100%" stop-color="{GAIN_COLOR}" stop-opacity="0"/>',
        "</linearGradient>",
        "</defs>",
    ]

    # Horizontal gridlines + y-axis labels (4 bands)
    for frac in [0, 0.25, 0.5, 0.75, 1]:
        y = PAD_T + plot_h * frac
        rating_val = round(y_max - (y_max - y_min) * frac)
        svg_parts.append(
            f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{WIDTH - PAD_R}" y2="{y:.1f}" '
            f'stroke="{GRID_COLOR}" stroke-width="1"/>'
        )
        svg_parts.append(
            f'<text x="{PAD_L - 8}" y="{y + 3:.1f}" text-anchor="end" font-size="10" '
            f'fill="{TEXT_COLOR}">{rating_val}</text>'
        )

    svg_parts.append(f'<path d="{area_path}" fill="url(#lcFill)" stroke="none"/>')
    svg_parts.append(f'<path d="{line_path}" fill="none" stroke="{LINE_COLOR}" stroke-width="2.2" '
                      f'stroke-linejoin="round" stroke-linecap="round"/>')

    for i, (x, y) in enumerate(points):
        c = contests[i]
        color = GAIN_COLOR if c["delta"] >= 0 else LOSS_COLOR
        r = 5.5 if i == len(points) - 1 else 3.2
        svg_parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" stroke="#0d1117" stroke-width="1.2">'
            f'<title>{c["name"]} — rating {c["rating_after"]} ({c["delta"]:+.0f})</title></circle>'
        )

    # Peak marker
    peak_idx = max(range(n), key=lambda i: contests[i]["rating_after"])
    px, py = points[peak_idx]
    svg_parts.append(
        f'<text x="{px:.1f}" y="{py - 10:.1f}" text-anchor="middle" font-size="10" '
        f'fill="{TEXT_COLOR}">peak {contests[peak_idx]["rating_after"]:.0f}</text>'
    )

    # X-axis start/end labels
    svg_parts.append(
        f'<text x="{points[0][0]:.1f}" y="{HEIGHT - 8}" font-size="10" fill="{TEXT_COLOR}">'
        f'{contests[0]["start_time"] and ""}{"contest 1"}</text>'
    )
    svg_parts.append(
        f'<text x="{points[-1][0]:.1f}" y="{HEIGHT - 8}" text-anchor="end" font-size="10" '
        f'fill="{TEXT_COLOR}">contest {n}</text>'
    )

    svg_parts.append("</svg>")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_parts))
    print(f"[generate_leetcode_contest_chart] wrote {OUT_PATH} ({n} contests)")


if __name__ == "__main__":
    main()