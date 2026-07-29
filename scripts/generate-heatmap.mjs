// scripts/generate-heatmap.mjs
// Renders the last 365 days of submissions as a radial "orbit" heatmap instead
// of the standard square grid: each day is a glowing dot placed on a spiral,
// size + opacity encode intensity. Center shows current streak.

import { writeFile, mkdir } from "node:fs/promises";
import { getSubmissionCalendar } from "./lib/leetcode.mjs";

const USERNAME = process.env.LEETCODE_USERNAME || "Kavish0_0";
const OUT_DIR = "assets";
const SIZE = 520;
const CX = SIZE / 2;
const CY = SIZE / 2;
const MAX_RADIUS = 220;
const MIN_RADIUS = 40;
const DAYS = 365;

function intensityColor(count, max) {
  if (count === 0) return { fill: "#2a2a33", opacity: 0.35, r: 2.4 };
  const t = Math.min(1, count / Math.max(1, max));
  // interpolate light-pink -> accent pink -> hot pink
  const stops = [
    [248, 187, 208], // #F8BBD0
    [244, 143, 177], // #F48FB1
    [236, 64, 122], // #EC407A
  ];
  const seg = t * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(seg));
  const localT = seg - i;
  const c = stops[i].map((v, idx) => Math.round(v + (stops[i + 1][idx] - v) * localT));
  return { fill: `rgb(${c[0]},${c[1]},${c[2]})`, opacity: 0.55 + 0.45 * t, r: 2.6 + t * 5.2 };
}

function buildSvg(days, streak, totalActiveDays) {
  const today = new Date();
  today.setUTCHours(0, 0, 0, 0);

  const byDate = new Map(days.map((d) => [d.date.toISOString().slice(0, 10), d.count]));

  const cells = [];
  const maxCount = Math.max(1, ...days.map((d) => d.count));

  for (let i = 0; i < DAYS; i++) {
    const d = new Date(today);
    d.setUTCDate(d.getUTCDate() - (DAYS - 1 - i));
    const key = d.toISOString().slice(0, 10);
    const count = byDate.get(key) || 0;

    // spiral: angle sweeps ~7.2 full turns across the year, radius grows linearly
    const turns = 7.2;
    const angle = (i / DAYS) * turns * 2 * Math.PI - Math.PI / 2;
    const radius = MIN_RADIUS + (i / (DAYS - 1)) * (MAX_RADIUS - MIN_RADIUS);
    const px = CX + radius * Math.cos(angle);
    const py = CY + radius * Math.sin(angle);

    const { fill, opacity, r } = intensityColor(count, maxCount);
    const month = d.toLocaleDateString("en-US", { month: "short" });
    const dayLabel = d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

    cells.push({ px, py, fill, opacity, r, count, dayLabel, isFirstOfMonth: d.getUTCDate() === 1, month });
  }

  const dots = cells
    .map(
      (c) => `<circle cx="${c.px.toFixed(2)}" cy="${c.py.toFixed(2)}" r="${c.r.toFixed(2)}" fill="${c.fill}" fill-opacity="${c.opacity.toFixed(
        2
      )}"${c.count > 0 && c.r > 5 ? ' filter="url(#dotGlow)"' : ""}><title>${c.dayLabel}: ${c.count} submission${
        c.count === 1 ? "" : "s"
      }</title></circle>`
    )
    .join("\n    ");

  const monthLabels = cells
    .filter((c) => c.isFirstOfMonth)
    .map((c) => {
      const angle = Math.atan2(c.py - CY, c.px - CX);
      const lx = CX + (MAX_RADIUS + 26) * Math.cos(angle);
      const ly = CY + (MAX_RADIUS + 26) * Math.sin(angle);
      return `<text x="${lx.toFixed(2)}" y="${ly.toFixed(
        2
      )}" text-anchor="middle" dominant-baseline="middle" font-family="'Fira Code', monospace" font-size="10" fill="#8b8b96">${c.month}</text>`;
    })
    .join("\n    ");

  const activeDaysInWindow = days.filter((d) => d.count > 0).length;

  return `<svg width="${SIZE}" height="${SIZE}" viewBox="0 0 ${SIZE} ${SIZE}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="bgGlow" cx="50%" cy="50%" r="60%">
      <stop offset="0%" stop-color="#F48FB1" stop-opacity="0.10"/>
      <stop offset="100%" stop-color="#0d1117" stop-opacity="0"/>
    </radialGradient>
    <filter id="dotGlow" x="-100%" y="-100%" width="300%" height="300%">
      <feGaussianBlur stdDeviation="2.2" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <rect x="0" y="0" width="${SIZE}" height="${SIZE}" rx="18" fill="#0d1117"/>
  <rect x="0.5" y="0.5" width="${SIZE - 1}" height="${SIZE - 1}" rx="18" fill="none" stroke="#F48FB1" stroke-opacity="0.18"/>
  <circle cx="${CX}" cy="${CY}" r="${MAX_RADIUS + 30}" fill="url(#bgGlow)"/>

  <text x="${SIZE / 2}" y="30" text-anchor="middle" font-family="'Fira Code', monospace" font-size="14" font-weight="600" fill="#F8BBD0">365-DAY SUBMISSION ORBIT</text>

  ${dots}
  ${monthLabels}

  <circle cx="${CX}" cy="${CY}" r="${MIN_RADIUS - 6}" fill="#0d1117" stroke="#EC407A" stroke-opacity="0.4"/>
  <text x="${CX}" y="${CY - 6}" text-anchor="middle" font-family="'Fira Code', monospace" font-size="22" font-weight="700" fill="#F8BBD0">${streak}</text>
  <text x="${CX}" y="${CY + 12}" text-anchor="middle" font-family="'Fira Code', monospace" font-size="9" fill="#8b8b96">DAY STREAK</text>

  <text x="${SIZE / 2}" y="${SIZE - 16}" text-anchor="middle" font-family="'Fira Code', monospace" font-size="11" fill="#8b8b96">${activeDaysInWindow} active days in the last year · ${totalActiveDays} all-time</text>
</svg>`;
}

async function main() {
  const { days, streak, totalActiveDays } = await getSubmissionCalendar(USERNAME);
  const svg = buildSvg(days, streak, totalActiveDays);
  await mkdir(OUT_DIR, { recursive: true });
  await writeFile(`${OUT_DIR}/submission-orbit.svg`, svg, "utf8");
  console.log(`✔ wrote ${OUT_DIR}/submission-orbit.svg`);
}

main().catch((err) => {
  console.error("✘ generate-heatmap failed:", err);
  process.exit(1);
});
