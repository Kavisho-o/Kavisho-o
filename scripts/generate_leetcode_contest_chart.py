"""
generate_leetcode_contest_chart.py

Renders the LeetCode contest rating journey as a night-sky constellation:
every contest is a star, positioned by rating (higher rating = higher up)
in chronological order, joined by a single glowing pink constellation
curve. The whole piece sits over a dark, layered starfield (background
stars, a couple of soft nebula glows, faint star clusters, cosmic dust)
so it reads as "the journey became a constellation," not a line chart
with stars stuck on top of it.

Only a handful of contests are labeled (peak, a couple of rating
milestones, the biggest single-contest jump) plus the most recent
contest, which is rendered as the largest, brightest star and always
labeled "Today" — the natural visual endpoint of the piece.

Output: assets/leetcode_contest_chart.svg
"""

import json
import math
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leetcode.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "leetcode_contest_chart.svg")

WIDTH, HEIGHT = 900, 320

# constellation occupies ~86% of the canvas width, per the "dominate the
# canvas, not a small chart in empty space" requirement
PAD_X = round(WIDTH * 0.07)
PAD_TOP = 58        # title/subtitle row + headroom for top-row labels
PAD_BOTTOM = 46      # room for bottom-row labels

BG_FILL = "#0d1117"
TITLE_COLOR = "#F8BBD0"
SUBTITLE_COLOR = "#7d6167"
PATH_COLOR = "#F48FB1"
STAR_FILL = "#F48FB1"
STAR_CORE = "#FFFFFF"
GLOW_COLOR = "#F8BBD0"
LABEL_NAME_COLOR = "#b491a0"
LABEL_VALUE_COLOR = "#FCE4EC"
DUST_COLOR = "#F48FB1"
TEXT_FAMILY = "Segoe UI, Helvetica, Arial, sans-serif"

MAX_MILESTONES = 5


def _pseudo_rand(seed):
    """Deterministic pseudo-random in [0,1) so the artwork is stable across runs."""
    x = math.sin(seed * 12.9898) * 43758.5453
    return x - math.floor(x)


def catmull_rom_to_bezier_path(points):
    """Smooth cubic-bezier SVG path through every star (the constellation curve)."""
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


def sparkle_points(cx, cy, r_outer, r_inner):
    """8-vertex polygon forming a 4-pointed sparkle/star shape."""
    pts = []
    for i in range(8):
        angle = math.pi / 2 * (i // 2) + (math.pi / 4 if i % 2 else 0)
        r = r_outer if i % 2 == 0 else r_inner
        pts.append(f"{cx + r * math.cos(angle):.2f},{cy + r * math.sin(angle):.2f}")
    return " ".join(pts)


def pick_milestones(contests, ratings, peak_idx, today_idx):
    """
    Select milestone contests dynamically based on fixed rating thresholds.
    Current is handled separately while drawing.
    """

    candidates = {}  # idx -> (label, priority)

    thresholds = [
        (1600, "First 1600", 2),
        (1800, "First 1800", 3),
        (1850, "Knight Ascension", 4),   # You can rename this
    ]

    # First time each threshold is crossed
    for threshold, label, priority in thresholds:
        for i, rating in enumerate(ratings):
            if rating >= threshold:
                candidates.setdefault(i, (label, priority))
                break

    # Peak rating (unless it's already the current contest)
    if peak_idx != today_idx:
        prev = candidates.get(peak_idx)
        if prev is None or prev[1] < 5:
            candidates[peak_idx] = ("Peak Rating", 5)

    ordered = sorted(
        candidates.items(),
        key=lambda kv: (-kv[1][1], kv[0])
    )[:MAX_MILESTONES]

    return sorted((idx, label) for idx, (label, _) in ordered)

def main() -> None:
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    contests = data.get("contests") or []

    if not contests:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} 100" width="100%" height="100">'
            f'<rect width="{WIDTH}" height="100" fill="{BG_FILL}"/>'
            f'<text x="20" y="50" fill="{SUBTITLE_COLOR}" font-family="{TEXT_FAMILY}" font-size="13">'
            f"No contest history yet.</text></svg>"
        )
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            f.write(svg)
        print("[generate_leetcode_contest_chart] no contests, wrote placeholder")
        return

    ratings = [c["rating_after"] for c in contests]
    r_min, r_max = min(ratings), max(ratings)
    pad_range = max(20, (r_max - r_min) * 0.16)
    y_min, y_max = r_min - pad_range, r_max + pad_range

    n = len(contests)
    plot_w = WIDTH - 2 * PAD_X
    plot_h = HEIGHT - PAD_TOP - PAD_BOTTOM

    def x_at(i):
        return PAD_X + (plot_w / 2 if n == 1 else plot_w * i / (n - 1))

    def y_at(rating):
        return PAD_TOP + plot_h - (rating - y_min) / (y_max - y_min) * plot_h

    points = [(x_at(i), y_at(c["rating_after"])) for i, c in enumerate(contests)]
    peak_idx = max(range(n), key=lambda i: ratings[i])
    today_idx = n - 1
    # gain_idx = max(range(n), key=lambda i: contests[i]["delta"])

    milestones = pick_milestones(contests, ratings, peak_idx, today_idx)
    milestone_idx_set = {i for i, _ in milestones}

    constellation_path = catmull_rom_to_bezier_path(points)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="100%" '
        f'height="{HEIGHT}" font-family="{TEXT_FAMILY}">',
        "<defs>",
        # soft outer glow used by stars and the constellation line
        '<filter id="starGlow" x="-200%" y="-200%" width="500%" height="500%">',
        '<feGaussianBlur stdDeviation="1.6" result="blur"/>',
        '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>',
        "</filter>",
        '<filter id="strongGlow" x="-300%" y="-300%" width="700%" height="700%">',
        '<feGaussianBlur stdDeviation="3.2" result="blur"/>',
        '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>',
        "</filter>",
        '<radialGradient id="nebula1" cx="50%" cy="50%" r="50%">',
        f'<stop offset="0%" stop-color="{DUST_COLOR}" stop-opacity="0.05"/>',
        f'<stop offset="100%" stop-color="{DUST_COLOR}" stop-opacity="0"/>',
        "</radialGradient>",
        '<radialGradient id="nebula2" cx="50%" cy="50%" r="50%">',
        f'<stop offset="0%" stop-color="#FCE4EC" stop-opacity="0.04"/>',
        f'<stop offset="100%" stop-color="#FCE4EC" stop-opacity="0"/>',
        "</radialGradient>",
        '<radialGradient id="haloGrad" cx="50%" cy="50%" r="50%">',
        f'<stop offset="0%" stop-color="{GLOW_COLOR}" stop-opacity="0.55"/>',
        f'<stop offset="100%" stop-color="{GLOW_COLOR}" stop-opacity="0"/>',
        "</radialGradient>",
        "</defs>",
    ]

    # -- dark GitHub-matching backdrop -----------------------------------
    svg_parts.append(f'<rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="{BG_FILL}"/>')

    # -- distant galaxies (blurred soft gradient blobs, very low opacity) --
    galaxy_specs = [
        (WIDTH * 0.10, HEIGHT * 0.20, 130, "nebula1"),
        (WIDTH * 0.88, HEIGHT * 0.78, 150, "nebula2"),
    ]
    for gx, gy, gr, grad in galaxy_specs:
        svg_parts.append(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="{gr}" fill="url(#{grad})"/>')

    # -- faint cosmic dust (soft elongated low-opacity smears) -----------
    for i in range(4):
        dx = _pseudo_rand(i * 4.4 + 30) * WIDTH
        dy = _pseudo_rand(i * 7.1 + 34) * HEIGHT
        rw = 60 + 90 * _pseudo_rand(i * 3.3 + 31)
        rh = rw * (0.25 + 0.2 * _pseudo_rand(i * 5.5 + 32))
        rot = _pseudo_rand(i * 6.6 + 33) * 180
        op = 0.02 + 0.02 * _pseudo_rand(i * 2.2 + 35)
        svg_parts.append(
            f'<ellipse cx="{dx:.1f}" cy="{dy:.1f}" rx="{rw:.1f}" ry="{rh:.1f}" '
            f'fill="{DUST_COLOR}" opacity="{op:.3f}" transform="rotate({rot:.1f} {dx:.1f} {dy:.1f})"/>'
        )

    # -- background starfield: 150-300 tiny stars, very low opacity ------
    n_bg = 220
    twinkle_every = 6  # ~1 in 6 background stars gets a slow twinkle
    for i in range(n_bg):
        sx = _pseudo_rand(i * 3.7 + 1) * WIDTH
        sy = _pseudo_rand(i * 9.1 + 4) * HEIGHT
        if sx < PAD_X + 190 and sy < 46:
            continue  # keep the title corner clear
        r = 0.5 + 1.5 * _pseudo_rand(i * 2.2 + 8)
        base_op = 0.05 + 0.10 * _pseudo_rand(i * 6.6 + 3)
        if i % twinkle_every == 0:
            dur = 2.6 + 2.6 * _pseudo_rand(i * 8.4 + 40)
            delay = dur * _pseudo_rand(i * 5.1 + 41)
            low_op = base_op * 0.25
            svg_parts.append(
                f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{r:.2f}" fill="#F8BBD0" opacity="{base_op:.3f}">'
                f'<animate attributeName="opacity" values="{base_op:.3f};{low_op:.3f};{base_op:.3f}" '
                f'dur="{dur:.2f}s" begin="-{delay:.2f}s" repeatCount="indefinite"/></circle>'
            )
        else:
            svg_parts.append(
                f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{r:.2f}" fill="#F8BBD0" opacity="{base_op:.3f}"/>'
            )

    # -- a few faint star clusters (tight groups of very small dots) -----
    for c in range(3):
        ccx = _pseudo_rand(c * 9.9 + 50) * (WIDTH - 2 * PAD_X) + PAD_X
        ccy = _pseudo_rand(c * 6.3 + 51) * (HEIGHT * 0.5) + HEIGHT * 0.08
        for j in range(5):
            jx = ccx + (_pseudo_rand(c * 11 + j * 2.1 + 52) - 0.5) * 22
            jy = ccy + (_pseudo_rand(c * 13 + j * 3.3 + 53) - 0.5) * 16
            r = 0.5 + 0.7 * _pseudo_rand(c * 5 + j + 54)
            op = 0.08 + 0.08 * _pseudo_rand(c * 7 + j + 55)
            svg_parts.append(f'<circle cx="{jx:.2f}" cy="{jy:.2f}" r="{r:.2f}" fill="#F8BBD0" opacity="{op:.3f}"/>')

    # -- the constellation curve itself: soft blurred glow pass + crisp line
    svg_parts.append(
        f'<path d="{constellation_path}" fill="none" stroke="{PATH_COLOR}" stroke-width="4" '
        f'stroke-opacity="0.22" stroke-linecap="round" stroke-linejoin="round" filter="url(#starGlow)"/>'
    )
    svg_parts.append(
        f'<path d="{constellation_path}" fill="none" stroke="{PATH_COLOR}" stroke-width="1.4" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="0.85"/>'
    )

    # -- every contest = a star -------------------------------------------
    placed_label_x = []  # track label x positions to keep spacing sane

    def label_conflicts(x):
        return any(abs(x - px) < 78 for px in placed_label_x)

    for i, (x, y) in enumerate(points):
        is_today = i == today_idx
        is_milestone = i in milestone_idx_set
        is_major = is_milestone

        if is_today:
            r_out, r_in, core_r, glow_r, filt = 11, 4.0, 3.4, 26, "strongGlow"
        elif is_major:
            r_out, r_in, core_r, glow_r, filt = 6.5, 2.4, 1.7, 15, "starGlow"
        else:
            r_out, r_in, core_r, glow_r, filt = 3.4, 1.3, 0.0, 0, None

        if glow_r:
            svg_parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{glow_r}" fill="url(#haloGrad)"/>')

        pts = sparkle_points(x, y, r_out, r_in)
        filt_attr = f' filter="url(#{filt})"' if filt else ""
        svg_parts.append(f'<polygon points="{pts}" fill="{STAR_FILL}"{filt_attr}/>')
        if core_r:
            svg_parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{core_r:.2f}" fill="{STAR_CORE}"/>')

        if is_today:
            svg_parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{glow_r * 0.7:.1f}" fill="none" '
                f'stroke="{GLOW_COLOR}" stroke-width="1" stroke-opacity="0.35">'
                f'<animate attributeName="r" values="{glow_r * 0.7:.1f};{glow_r * 1.05:.1f};{glow_r * 0.7:.1f}" '
                f'dur="3.6s" repeatCount="indefinite"/>'
                f'<animate attributeName="stroke-opacity" values="0.35;0.05;0.35" dur="3.6s" '
                f'repeatCount="indefinite"/></circle>'
            )

        if is_today or is_milestone:
            label = "Current" if is_today else next(l for idx, l in milestones if idx == i)
            text_x = min(max(x, PAD_X + 34), WIDTH - PAD_X - 34)
            if label_conflicts(text_x):
                text_x += 40 if text_x < WIDTH / 2 else -40
                text_x = min(max(text_x, PAD_X + 34), WIDTH - PAD_X - 34)
            placed_label_x.append(text_x)

            above = y > PAD_TOP + plot_h * 0.35
            if is_today:
                above = y > PAD_TOP + 30
            if above:
                name_y, value_y = y - (glow_r if glow_r else 14) - 16, y - (glow_r if glow_r else 14) - 2
            else:
                name_y, value_y = y + (glow_r if glow_r else 14) + 14, y + (glow_r if glow_r else 14) + 28

            star_prefix = ""
            svg_parts.append(
                f'<text x="{text_x:.2f}" y="{name_y:.2f}" text-anchor="middle" font-size="10" '
                f'fill="{LABEL_NAME_COLOR}">{star_prefix}{label}</text>'
            )
            svg_parts.append(
                f'<text x="{text_x:.2f}" y="{value_y:.2f}" text-anchor="middle" font-size="13" '
                f'font-weight="700" fill="{LABEL_VALUE_COLOR}">{contests[i]["rating_after"]:.0f}</text>'
            )

    # -- minimal title -----------------------------------------------------
    svg_parts.append(
        f'<text x="{PAD_X}" y="24" font-size="10" fill="{SUBTITLE_COLOR}">'
        f"Every contest becomes another star</text>"
    )

    svg_parts.append("</svg>")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_parts))
    print(f"[generate_leetcode_contest_chart] wrote {OUT_PATH} "
          f"({n} contest-stars, {len(milestones)} milestones, peak {ratings[peak_idx]:.0f})")


if __name__ == "__main__":
    main()