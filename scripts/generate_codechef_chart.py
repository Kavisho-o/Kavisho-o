"""
generate_codechef_chart.py

Renders the CodeChef contest journey as a floating cumulative waterfall
chart. Built entirely with Matplotlib (SVG backend), but pushed hard on
composition so the output reads like a hand-built product illustration
(Figma/Linear/Apple-dashboard style) rather than a default plot: wide
gradient-filled rounded bars with soft shadows and top highlights, a
glowing halo on the peak bar, bright dashed connectors that guide the
eye across the journey, and tight, intentional typography.

Output: assets/codechef_chart.svg
"""

import json
import os

import numpy as np

import matplotlib
matplotlib.use("SVG")

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch, PathPatch
from matplotlib.path import Path
from matplotlib.collections import LineCollection
from matplotlib.transforms import Bbox

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "codechef.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "codechef_chart.svg")

# ---- Palette -------------------------------------------------------------
GAIN_TOP = "#FFE1EC"        # luminous highlight for gain bars
GAIN_MID = "#F8A9C4"
GAIN_BOT = "#F183AC"
LOSS_TOP = "#C9B3DA"        # muted lavender for loss bars
LOSS_MID = "#9C7FB3"
LOSS_BOT = "#7C5F94"

BAR_EDGE_GAIN = "#FFF3F8"
BAR_EDGE_LOSS = "#DCC9EA"
SHADOW_COLOR = "#1a0f16"
CONNECTOR_COLOR = "#D9A9C2"
TEXT_MAIN = "#F3F1F6"
TEXT_MUTED = "#9C99A6"
TEXT_SUB = "#B7ADC0"
PEAK_GLOW = "#FF6FA8"
PEAK_HALO = "#FF9FC4"

FONT_FAMILY = "DejaVu Sans"

ROUND = 0.16  # rounding size (axes fraction-ish, tuned per bar width)


def _fmt(n: float) -> str:
    return f"{n:+.0f}" if n != 0 else "0"


def _gradient_rounded_bar(ax, x0, y0, w, h, top_color, mid_color, bot_color,
                           edge_color, zorder=3, glow=False, glow_color=None):
    """Draw a rounded rectangle filled with a smooth vertical gradient,
    a soft drop shadow, and a subtle top highlight -- built entirely
    from vector primitives so it survives SVG export cleanly."""

    round_size = min(w * 0.28, h * 0.22, w * 0.5)

    # ---- soft shadow (offset, blurred via stacked low-alpha patches) ----
    shadow_offsets = [(0.10, -0.10, 0.05), (0.06, -0.06, 0.07), (0.03, -0.03, 0.09)]
    for dx, dy, a in shadow_offsets:
        shadow = FancyBboxPatch(
            (x0 + dx, y0 + dy), w, h,
            boxstyle=f"round,pad=0,rounding_size={round_size}",
            linewidth=0,
            facecolor=SHADOW_COLOR,
            alpha=a,
            zorder=zorder - 1,
        )
        ax.add_patch(shadow)

    # ---- glow halo behind peak bar ----
    if glow:
        for pad, a in [(0.09, 0.10), (0.055, 0.16), (0.03, 0.22)]:
            halo = FancyBboxPatch(
                (x0 - pad, y0 - pad), w + 2 * pad, h + 2 * pad,
                boxstyle=f"round,pad=0,rounding_size={round_size + pad}",
                linewidth=0,
                facecolor=glow_color or PEAK_GLOW,
                alpha=a,
                zorder=zorder - 1,
            )
            ax.add_patch(halo)

    # ---- gradient fill, clipped to a rounded-rect path ----
    n_grad = 200
    grad = np.linspace(1, 0, n_grad).reshape(-1, 1)
    cmap_colors = [bot_color, mid_color, top_color]
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("bar_grad", cmap_colors, N=256)

    clip_patch = FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle=f"round,pad=0,rounding_size={round_size}",
        transform=ax.transData,
    )
    im = ax.imshow(
        grad, aspect="auto", cmap=cmap,
        extent=(x0, x0 + w, y0, y0 + h),
        zorder=zorder, interpolation="bicubic",
    )
    im.set_clip_path(clip_patch)

    # ---- crisp edge / border on top ----
    border = FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle=f"round,pad=0,rounding_size={round_size}",
        linewidth=1.6,
        edgecolor=edge_color,
        facecolor="none",
        alpha=0.9,
        zorder=zorder + 1,
    )
    if glow:
        border.set_path_effects([pe.withStroke(linewidth=3.2, foreground=glow_color or PEAK_GLOW, alpha=0.45)])
    ax.add_patch(border)

    # ---- subtle top highlight sliver (glossy sheen) ----
    sheen_h = h * 0.22
    sheen = FancyBboxPatch(
        (x0 + w * 0.08, y0 + h - sheen_h * 1.1), w * 0.84, sheen_h,
        boxstyle=f"round,pad=0,rounding_size={round_size * 0.6}",
        linewidth=0,
        facecolor="#FFFFFF",
        alpha=0.16,
        zorder=zorder + 0.5,
    )
    ax.add_patch(sheen)


def main() -> None:
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    contests = data.get("contests") or []
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    if not contests:
        fig = plt.figure(figsize=(9, 1.1), dpi=100)
        fig.patch.set_alpha(0.0)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis("off")
        ax.text(
            0.02, 0.5, "No CodeChef contest history yet.",
            color=TEXT_MUTED, fontsize=11, family=FONT_FAMILY,
            va="center", ha="left", transform=ax.transAxes,
        )
        fig.savefig(OUT_PATH, format="svg", transparent=True)
        plt.close(fig)
        print("[generate_codechef_chart] no contests, wrote placeholder")
        return

    ratings = [c["rating"] for c in contests]
    starts = [None] + ratings[:-1]
    n = len(contests)

    deltas = []
    for i, r in enumerate(ratings):
        prev = starts[i]
        deltas.append(0.0 if prev is None else round(r - prev, 0))

    # ---- Figure: wide, generous, mostly plot area ----
    fig_w, fig_h = 15.5, 5.4
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=110)
    fig.patch.set_alpha(0.0)
    ax = fig.add_axes([0.018, 0.155, 0.968, 0.70])
    ax.set_facecolor("none")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)

    all_vals = [starts[0] if starts[0] is not None else ratings[0]] + ratings
    y_min, y_max = min(all_vals), max(all_vals)
    y_range = y_max - y_min

    # Compress vertical range so the journey fills ~65% of height,
    # leaving room above for peak/label headroom and below for ticks.
    y_pad_top = y_range * 0.42
    y_pad_bot = y_range * 0.20
    ax.set_ylim(y_min - y_pad_bot, y_max + y_pad_top)

    bar_w = 0.62          # wide, dominant bars
    gap = 1.0
    ax.set_xlim(-0.62, (n - 1) * gap + 0.62)

    peak_idx = max(range(n), key=lambda i: ratings[i])
    biggest_gain_idx = max(range(1, n), key=lambda i: deltas[i], default=None) if n > 1 else None
    biggest_loss_idx = min(range(1, n), key=lambda i: deltas[i], default=None) if n > 1 else None

    connector_segments = []
    prev_top_x, prev_top_y = None, None

    label_font = {"family": FONT_FAMILY}

    for i in range(n):
        x_c = i * gap
        top = ratings[i]
        bottom = starts[i] if starts[i] is not None else ratings[i]
        low, high = min(top, bottom), max(top, bottom)
        height = max(high - low, y_range * 0.018)
        is_gain = deltas[i] >= 0
        is_peak = (i == peak_idx)

        x0 = x_c - bar_w / 2

        if is_gain:
            top_c, mid_c, bot_c, edge_c = GAIN_TOP, GAIN_MID, GAIN_BOT, BAR_EDGE_GAIN
        else:
            top_c, mid_c, bot_c, edge_c = LOSS_TOP, LOSS_MID, LOSS_BOT, BAR_EDGE_LOSS

        _gradient_rounded_bar(
            ax, x0, low, bar_w, height,
            top_c, mid_c, bot_c, edge_c,
            zorder=3, glow=is_peak, glow_color=PEAK_GLOW,
        )

        if prev_top_x is not None:
            connector_segments.append([(prev_top_x, prev_top_y), (x_c, bottom)])
        prev_top_x, prev_top_y = x_c, top

        # ---- annotations: sparse, intentional ----
        label = None
        label_color = TEXT_SUB
        weight = "normal"
        if i == 0:
            label, label_color, weight = f"Start · {ratings[0]:.0f}", TEXT_MAIN, "bold"
        elif i == n - 1:
            label, label_color, weight = f"Current · {ratings[-1]:.0f}", "#FFFFFF", "bold"
        elif i == biggest_gain_idx and deltas[i] > 0:
            label, label_color = _fmt(deltas[i]), GAIN_TOP
        elif i == biggest_loss_idx and deltas[i] < 0:
            label, label_color = _fmt(deltas[i]), LOSS_TOP

        if label is not None and i != peak_idx:
            ax.annotate(
                label,
                xy=(x_c, high),
                xytext=(x_c, high + y_range * 0.075),
                ha="center", va="bottom",
                fontsize=12.5 if i in (0, n - 1) else 11,
                family=FONT_FAMILY,
                color=label_color,
                fontweight=weight,
                zorder=6,
            )

        if i == n - 1:
            # endpoint marker to make the eye land here
            ax.scatter([x_c], [high], marker="o", s=70,
                       facecolor="#FFFFFF", edgecolor=GAIN_BOT,
                       linewidths=1.6, zorder=7)

        if is_peak:
            ax.annotate(
                f"Peak · {ratings[i]:.0f}",
                xy=(x_c, high),
                xytext=(x_c, high + y_range * 0.16),
                ha="center", va="bottom",
                fontsize=13, family=FONT_FAMILY,
                color=PEAK_GLOW, fontweight="bold",
                zorder=8,
                path_effects=[pe.withStroke(linewidth=3, foreground="#2a0f1b", alpha=0.6)],
            )
            star = ax.scatter(
                [x_c], [high + y_range * 0.055], marker="*", s=260,
                color="#FFFFFF", zorder=8, linewidths=0,
            )
            star.set_path_effects([pe.withStroke(linewidth=4, foreground=PEAK_GLOW, alpha=0.9)])

    # ---- Connectors: bright, dashed, consistent, guiding the eye ----
    lc = LineCollection(
        connector_segments,
        colors=CONNECTOR_COLOR,
        linewidths=1.6,
        linestyles=(0, (5, 3)),
        alpha=0.55,
        zorder=2,
        capstyle="round",
    )
    lc.set_path_effects([pe.withStroke(linewidth=3.2, foreground=CONNECTOR_COLOR, alpha=0.12)])
    ax.add_collection(lc)

    # ---- Contest name ticks: small, muted, evenly spaced ----
    for i, c in enumerate(contests):
        short = c["name"].split(" (")[0].replace("Starters ", "#")
        ax.annotate(
            short,
            xy=(i * gap, y_min - y_pad_bot * 0.25),
            xytext=(i * gap, y_min - y_pad_bot * 0.55),
            ha="center", va="top",
            fontsize=8.2, family=FONT_FAMILY,
            color=TEXT_MUTED,
            zorder=4,
        )

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fig.savefig(OUT_PATH, format="svg", transparent=True)
    plt.close(fig)
    print(f"[generate_codechef_chart] wrote {OUT_PATH} ({n} contests)")


if __name__ == "__main__":
    main()