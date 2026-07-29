// scripts/generate-contest-chart.mjs
// Builds a custom "glowing neon" area chart of contest rating over time,
// with milestone markers on personal-best peaks. No charting library —
// pure hand-built SVG so it can render in a GitHub README.

import { writeFile, mkdir } from "node:fs/promises";
import { getContestHistory } from "./lib/leetcode.mjs";
import { smoothPath, escapeXml, fmtDate } from "./lib/svg-utils.mjs";

const USERNAME = process.env.LEETCODE_USERNAME || "Kavish0_0";
const OUT_DIR = "assets";
const WIDTH = 900;
const HEIGHT = 320;
const PAD = { top: 40, right: 36, bottom: 46, left: 56 };

function buildSvg(history, summary) {
  const ratings = history.map((c) => c.rating);
  const minR = Math.floor(Math.min(...ratings) / 25) * 25 - 25;
  const maxR = Math.ceil(Math.max(...ratings) / 25) * 25 + 25;

  const plotW = WIDTH - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;

  const x = (i) => PAD.left + (i / (history.length - 1)) * plotW;
  const y = (r) => PAD.top + plotH - ((r - minR) / (maxR - minR)) * plotH;

  const points = history.map((c, i) => ({ x: x(i), y: y(c.rating) }));
  const linePath = smoothPath(points);
  const areaPath =
    `${linePath} L ${points[points.length - 1].x.toFixed(2)} ${(PAD.top + plotH).toFixed(2)} ` +
    `L ${points[0].x.toFixed(2)} ${(PAD.top + plotH).toFixed(2)} Z`;

  // Milestones: running personal-best peaks (local maxima that beat all prior ratings)
  let best = -Infinity;
  const milestones = [];
  history.forEach((c, i) => {
    if (c.rating > best) {
      best = c.rating;
      milestones.push({ i, rating: c.rating, title: c.contest.title, date: new Date(c.contest.startTime * 1000) });
    }
  });
  // keep at most 5 milestones, spaced out, always include the final point
  const keep = [];
  const step = Math.max(1, Math.floor(milestones.length / 4));
  for (let k = 0; k < milestones.length; k += step) keep.push(milestones[k]);
  if (keep[keep.length - 1] !== milestones[milestones.length - 1]) {
    keep.push(milestones[milestones.length - 1]);
  }

  // gridlines (horizontal, 4 bands)
  const gridLines = [];
  const bands = 4;
  for (let b = 0; b <= bands; b++) {
    const r = minR + ((maxR - minR) * b) / bands;
    const gy = y(r);
    gridLines.push(`
      <line x1="${PAD.left}" y1="${gy.toFixed(2)}" x2="${WIDTH - PAD.right}" y2="${gy.toFixed(2)}"
            stroke="#F48FB1" stroke-opacity="0.08" stroke-width="1" stroke-dasharray="4 6"/>
      <text x="${PAD.left - 10}" y="${(gy + 4).toFixed(2)}" text-anchor="end"
            font-family="'Fira Code', monospace" font-size="11" fill="#8b8b96">${Math.round(r)}</text>
    `);
  }

  // x-axis labels: first, middle, last contest dates
  const xLabelIdx = [0, Math.floor((history.length - 1) / 2), history.length - 1];
  const xLabels = xLabelIdx.map((i) => {
    const c = history[i];
    const gx = x(i);
    return `<text x="${gx.toFixed(2)}" y="${HEIGHT - PAD.bottom + 22}" text-anchor="middle"
            font-family="'Fira Code', monospace" font-size="11" fill="#8b8b96">${escapeXml(
              fmtDate(new Date(c.contest.startTime * 1000))
            )}</text>`;
  });

  const milestoneMarkers = keep
    .map((m) => {
      const mx = points[m.i].x;
      const my = points[m.i].y;
      return `
      <g>
        <circle cx="${mx.toFixed(2)}" cy="${my.toFixed(2)}" r="7" fill="#0d1117" stroke="url(#lineGrad)" stroke-width="2"/>
        <circle cx="${mx.toFixed(2)}" cy="${my.toFixed(2)}" r="3" fill="#F8BBD0"/>
        <text x="${mx.toFixed(2)}" y="${(my - 14).toFixed(2)}" text-anchor="middle"
              font-family="'Fira Code', monospace" font-weight="600" font-size="12" fill="#F8BBD0">${Math.round(
                m.rating
              )}</text>
      </g>`;
    })
    .join("\n");

  const lastPoint = points[points.length - 1];

  const summaryLine = summary
    ? `Rating ${Math.round(summary.rating)} · Global Rank #${summary.globalRanking?.toLocaleString?.() ?? summary.globalRanking} · Top ${
        summary.topPercentage ? summary.topPercentage.toFixed(2) : "—"
      }% · ${summary.attendedContestsCount} contests`
    : "";

  return `<svg width="${WIDTH}" height="${HEIGHT}" viewBox="0 0 ${WIDTH} ${HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#0d1117"/>
    </linearGradient>
    <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#F8BBD0"/>
      <stop offset="50%" stop-color="#F48FB1"/>
      <stop offset="100%" stop-color="#EC407A"/>
    </linearGradient>
    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#F48FB1" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#F48FB1" stop-opacity="0"/>
    </linearGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <rect x="0" y="0" width="${WIDTH}" height="${HEIGHT}" rx="18" fill="url(#bgGrad)"/>
  <rect x="0.5" y="0.5" width="${WIDTH - 1}" height="${HEIGHT - 1}" rx="18" fill="none" stroke="#F48FB1" stroke-opacity="0.18"/>

  <text x="28" y="30" font-family="'Fira Code', monospace" font-size="14" font-weight="600" fill="#F8BBD0">CONTEST RATING PROGRESSION</text>
  <text x="${WIDTH - 28}" y="30" text-anchor="end" font-family="'Fira Code', monospace" font-size="11" fill="#8b8b96">${escapeXml(
    summaryLine
  )}</text>

  ${gridLines.join("\n")}

  <path d="${areaPath}" fill="url(#areaGrad)"/>
  <path d="${linePath}" fill="none" stroke="url(#lineGrad)" stroke-width="2.5" filter="url(#glow)" stroke-linecap="round"/>

  ${milestoneMarkers}

  <circle cx="${lastPoint.x.toFixed(2)}" cy="${lastPoint.y.toFixed(2)}" r="5.5" fill="#EC407A" filter="url(#glow)"/>

  ${xLabels.join("\n")}
</svg>`;
}

async function main() {
  const { history, summary } = await getContestHistory(USERNAME);
  if (!history.length) {
    throw new Error(`No attended contests found for ${USERNAME}`);
  }
  const svg = buildSvg(history, summary);
  await mkdir(OUT_DIR, { recursive: true });
  await writeFile(`${OUT_DIR}/contest-rating.svg`, svg, "utf8");
  console.log(`✔ wrote ${OUT_DIR}/contest-rating.svg (${history.length} contests)`);
}

main().catch((err) => {
  console.error("✘ generate-contest-chart failed:", err);
  process.exit(1);
});
