"""
generate_leetcode_contest_chart.py

Renders the LeetCode contest rating journey as a "Mountain Range":
the rating curve becomes a smooth mountain ridge (Catmull-Rom spline,
not straight line segments) filled with a soft baby-pink gradient, with
a faint secondary ridge behind it for depth. Only a handful of
milestone flags are labeled — this is meant to read as artwork first,
chart second, so there are deliberately no axes, gridlines, or numeric
labels beyond the milestones and a small "Today" marker.

Output: assets/leetcode_contest_chart.svg
"""

import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leetcode.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "leetcode_contest_chart.svg")

WIDTH, HEIGHT = 900, 220
PAD_X = 24
PAD_TOP = 46       # extra headroom for milestone flags above the ridge
PAD_BOTTOM = 30

RIDGE_STROKE = "#F48FB1"
RIDGE_FILL_TOP = "#F48FB1"
BACK_RIDGE_COLOR = "#F8BBD0"
FLAG_COLOR = "#F8BBD0"
FLAG_LINE_COLOR = "#5a4450"
LABEL_COLOR = "#c9a8b4"
TODAY_COLOR = "#ffffff"
TEXT_FAMILY = "Segoe UI, Helvetica, Arial, sans-serif"


def catmull_rom_to_bezier_path(points):
    """Convert a polyline into a smooth cubic-bezier SVG path (mountain ridge)."""
    if len(points) < 3:
        return "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in points)

    p = [points[0]] + list(points) + [points[-1]]
    d = [f"M {p[1][0]:.2f},{p[1][1]:.2f}"]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        c1x = p1[0] + (p2[0] - p0[0]) / 6
        c1y = p1[1] + (p2[1] - p0[1]) / 6
        c2x = p2[0] - (p3[0] - p1[0]) / 6
        c2y = p2[1] - (p3[1] - p1[1]) / 6
        d.append(f"C {c1x:.2f},{c1y:.2f} {c2x:.2f},{c2y:.2f} {p2[0]:.2f},{p2[1]:.2f}")
    return " ".join(d)


def pick_milestones(contests):
    """Pick 3-5 significant contest indices to flag (Today is handled separately)."""
    n = len(contests)
    ratings = [c["rating_after"] for c in contests]
    r_min, r_max = min(ratings), max(ratings)

    candidates = {}  # index -> label

    span = r_max - r_min
    if span > 0:
        for frac in (0.35, 0.7):
            target = round((r_min + span * frac) / 50) * 50
            for i, r in enumerate(ratings):
                if r >= target:
                    candidates.setdefault(i, f"first {int(target)}+")
                    break

    jump_idx = max(range(n), key=lambda i: contests[i]["delta"])
    if contests[jump_idx]["delta"] > 0:
        candidates[jump_idx] = f'+{contests[jump_idx]["delta"]:.0f} jump'

    peak_idx = max(range(n), key=lambda i: ratings[i])
    candidates[peak_idx] = f"peak {ratings[peak_idx]:.0f}"

    ordered = sorted(candidates.items(), key=lambda kv: kv[0])
    if len(ordered) > 5:
        must_keep = {peak_idx, jump_idx}
        rest = [i for i, _ in ordered if i not in must_keep]
        keep_n = max(0, 5 - len(must_keep))
        step = max(1, len(rest) // max(1, keep_n))
        chosen = set(list(must_keep) + rest[::step][:keep_n])
        ordered = [(i, lbl) for i, lbl in ordered if i in chosen]

    return ordered


def main() -> None:
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    contests = data.get("contests") or []

    if not contests:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} 100" width="100%" height="100">'
            f'<text x="20" y="50" fill="{LABEL_COLOR}" font-family="{TEXT_FAMILY}" font-size="13">'
            f"No contest history yet.</text></svg>"
        )
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            f.write(svg)
        print("[generate_leetcode_contest_chart] no contests, wrote placeholder")
        return

    ratings = [c["rating_after"] for c in contests]
    r_min, r_max = min(ratings), max(ratings)
    pad_range = max(20, (r_max - r_min) * 0.12)
    y_min, y_max = r_min - pad_range, r_max + pad_range

    n = len(contests)
    plot_w = WIDTH - 2 * PAD_X
    plot_h = HEIGHT - PAD_TOP - PAD_BOTTOM

    def x_at(i):
        return PAD_X + (plot_w if n == 1 else plot_w * i / (n - 1))

    def y_at(rating):
        return PAD_TOP + plot_h - (rating - y_min) / (y_max - y_min) * plot_h

    points = [(x_at(i), y_at(c["rating_after"])) for i, c in enumerate(contests)]
    baseline_y = PAD_TOP + plot_h

    ridge_path = catmull_rom_to_bezier_path(points)
    ridge_area = (
        ridge_path
        + f" L {points[-1][0]:.2f},{baseline_y:.2f}"
        + f" L {points[0][0]:.2f},{baseline_y:.2f} Z"
    )

    back_points = []
    for x, y in points:
        compressed_y = baseline_y - (baseline_y - y) * 0.55
        back_points.append((x + 10, compressed_y - 10))
    back_ridge_path = catmull_rom_to_bezier_path(back_points)
    back_ridge_area = (
        back_ridge_path
        + f" L {back_points[-1][0]:.2f},{baseline_y:.2f}"
        + f" L {back_points[0][0]:.2f},{baseline_y:.2f} Z"
    )

    milestones = pick_milestones(contests)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="100%" '
        f'height="{HEIGHT}" font-family="{TEXT_FAMILY}">',
        "<defs>",
        '<linearGradient id="mtnFront" x1="0" y1="0" x2="0" y2="1">',
        f'<stop offset="0%" stop-color="{RIDGE_FILL_TOP}" stop-opacity="0.55"/>',
        f'<stop offset="100%" stop-color="{RIDGE_FILL_TOP}" stop-opacity="0.04"/>',
        "</linearGradient>",
        '<linearGradient id="mtnBack" x1="0" y1="0" x2="0" y2="1">',
        f'<stop offset="0%" stop-color="{BACK_RIDGE_COLOR}" stop-opacity="0.22"/>',
        f'<stop offset="100%" stop-color="{BACK_RIDGE_COLOR}" stop-opacity="0"/>',
        "</linearGradient>",
        "</defs>",
    ]

    svg_parts.append(f'<path d="{back_ridge_area}" fill="url(#mtnBack)" stroke="none"/>')

    svg_parts.append(f'<path d="{ridge_area}" fill="url(#mtnFront)" stroke="none"/>')
    svg_parts.append(
        f'<path d="{ridge_path}" fill="none" stroke="{RIDGE_STROKE}" stroke-width="2.4" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )

    for i, label in milestones:
        x, y = points[i]
        stem_top = y - 26
        svg_parts.append(
            f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{x:.2f}" y2="{stem_top:.2f}" '
            f'stroke="{FLAG_LINE_COLOR}" stroke-width="1"/>'
        )
        svg_parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.4" fill="{FLAG_COLOR}"/>')
        svg_parts.append(
            f'<text x="{x:.2f}" y="{stem_top - 6:.2f}" text-anchor="middle" font-size="10.5" '
            f'fill="{LABEL_COLOR}">{label}</text>'
        )

    last_x, last_y = points[-1]
    svg_parts.append(f'<circle cx="{last_x:.2f}" cy="{last_y:.2f}" r="5" fill="{TODAY_COLOR}"/>')
    svg_parts.append(f'<circle cx="{last_x:.2f}" cy="{last_y:.2f}" r="8.5" fill="{TODAY_COLOR}" opacity="0.18"/>')
    today_label_y = last_y - 14 if (milestones and milestones[-1][0] != n - 1) else last_y - 30
    svg_parts.append(
        f'<text x="{min(last_x, WIDTH - PAD_X):.2f}" y="{max(today_label_y, 14):.2f}" '
        f'text-anchor="end" font-size="10.5" fill="{TODAY_COLOR}" opacity="0.85">Today · '
        f'{contests[-1]["rating_after"]:.0f}</text>'
    )

    svg_parts.append("</svg>")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_parts))
    print(f"[generate_leetcode_contest_chart] wrote {OUT_PATH} "
          f"({n} contests, {len(milestones)} milestones)")


if __name__ == "__main__":
    main()