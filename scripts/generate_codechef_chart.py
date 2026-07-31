"""
generate_codechef_chart.py

Renders the CodeChef contest journey as "Color-Coded Delta Bars": one
slim bar per contest, height/direction encoding the rating change for
that contest, colored by gain vs loss. Deliberately a different chart
family from the LeetCode line-with-markers chart (per spec, Part 3
should not duplicate Part 2's visualization) while staying in the same
baby-pink palette and small footprint befitting its lower emphasis.

Output: assets/codechef_chart.svg
"""

import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "codechef.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "codechef_chart.svg")

WIDTH, HEIGHT = 900, 160
PAD_L, PAD_R, PAD_T, PAD_B = 40, 20, 16, 26

GAIN_COLOR = "#F8BBD0"
LOSS_COLOR = "#8f5468"
ZERO_LINE = "#3a3f4a"
TEXT_COLOR = "#8b8f98"


def main() -> None:
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    contests = data.get("contests") or []

    if not contests:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} 80" width="100%" height="80">'
            f'<text x="20" y="40" fill="{TEXT_COLOR}" font-family="Segoe UI, sans-serif" font-size="13">'
            f"No CodeChef contest history yet.</text></svg>"
        )
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            f.write(svg)
        print("[generate_codechef_chart] no contests, wrote placeholder")
        return

    deltas = []
    prev = None
    for c in contests:
        rating = c["rating"]
        delta = 0.0 if prev is None else round(rating - prev, 0)
        deltas.append(delta)
        prev = rating

    n = len(contests)
    plot_w = WIDTH - PAD_L - PAD_R
    plot_h = HEIGHT - PAD_T - PAD_B
    mid_y = PAD_T + plot_h / 2

    max_abs = max(1.0, max(abs(d) for d in deltas))
    bar_w = max(2.5, min(10, plot_w / n * 0.6))
    step = plot_w / n

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="100%" '
        f'height="{HEIGHT}" font-family="Segoe UI, Helvetica, Arial, sans-serif">',
        f'<line x1="{PAD_L}" y1="{mid_y:.1f}" x2="{WIDTH - PAD_R}" y2="{mid_y:.1f}" '
        f'stroke="{ZERO_LINE}" stroke-width="1"/>',
    ]

    for i, (c, d) in enumerate(zip(contests, deltas)):
        x = PAD_L + step * i + (step - bar_w) / 2
        bar_h = abs(d) / max_abs * (plot_h / 2 - 4)
        color = GAIN_COLOR if d >= 0 else LOSS_COLOR
        y = mid_y - bar_h if d >= 0 else mid_y
        svg_parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{max(bar_h, 1):.1f}" '
            f'rx="1.5" fill="{color}"><title>{c["name"]} — rating {c["rating"]:.0f} ({d:+.0f})</title>'
            f"</rect>"
        )

    svg_parts.append(
        f'<text x="{PAD_L}" y="{HEIGHT - 6}" font-size="10" fill="{TEXT_COLOR}">contest 1</text>'
    )
    svg_parts.append(
        f'<text x="{WIDTH - PAD_R}" y="{HEIGHT - 6}" text-anchor="end" font-size="10" '
        f'fill="{TEXT_COLOR}">contest {n}</text>'
    )
    svg_parts.append(
        f'<text x="{PAD_L}" y="{PAD_T + 8}" font-size="10" fill="{TEXT_COLOR}">'
        f'current {contests[-1]["rating"]:.0f}</text>'
    )

    svg_parts.append("</svg>")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_parts))
    print(f"[generate_codechef_chart] wrote {OUT_PATH} ({n} contests)")


if __name__ == "__main__":
    main()