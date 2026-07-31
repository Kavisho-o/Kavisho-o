"""
generate_codechef_stats_strip.py

Renders a small, humble stats row for CodeChef: rating, stars, contests
attended. Output: assets/codechef_stats.svg
"""

import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "codechef.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "codechef_stats.svg")

TEXT_COLOR = "#e0e0e0"
LABEL_COLOR = "#8b8f98"
ACCENT = "#F8BBD0"


def fmt(v, default="—"):
    return default if v is None else v


def main() -> None:
    with open(DATA_PATH, encoding="utf-8") as f:
        d = json.load(f)

    stars = d.get("stars")
    star_str = ("★" * int(stars)) if stars else "—"

    items = [
        ("Rating", fmt(d.get("current_rating"))),
        ("Stars", star_str),
        ("Contests", fmt(d.get("contests_count"))),
    ]

    width, height = 480, 54
    col_w = width / len(items)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" '
        f'height="{height}" font-family="Segoe UI, Helvetica, Arial, sans-serif">'
    ]
    for i, (label, value) in enumerate(items):
        cx = col_w * i + col_w / 2
        parts.append(
            f'<text x="{cx:.1f}" y="24" text-anchor="middle" font-size="16" font-weight="600" '
            f'fill="{ACCENT}">{value}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="42" text-anchor="middle" font-size="10" letter-spacing="0.5" '
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
    print(f"[generate_codechef_stats_strip] wrote {OUT_PATH}")


if __name__ == "__main__":
    main()