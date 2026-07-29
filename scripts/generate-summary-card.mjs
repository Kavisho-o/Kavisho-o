// scripts/generate-summary-card.mjs
// Compact stat card: overall solved counts + contest rating, on-brand pink theme.

import { writeFile, mkdir } from "node:fs/promises";
import { getProfileStats } from "./lib/leetcode.mjs";

const USERNAME = process.env.LEETCODE_USERNAME || "Kavish0_0";
const OUT_DIR = "assets";
const WIDTH = 420;
const HEIGHT = 200;

function bar(label, count, total, y, color) {
  const trackW = 220;
  const pct = total > 0 ? Math.min(1, count / total) : 0;
  return `
    <text x="24" y="${y}" font-family="'Fira Code', monospace" font-size="12" fill="#e0e0e0">${label}</text>
    <text x="${24 + trackW + 12}" y="${y}" font-family="'Fira Code', monospace" font-size="12" fill="#8b8b96" text-anchor="start">${count}</text>
    <rect x="90" y="${y - 11}" width="${trackW}" height="8" rx="4" fill="#20202a"/>
    <rect x="90" y="${y - 11}" width="${(trackW * pct).toFixed(2)}" height="8" rx="4" fill="${color}"/>
  `;
}

function buildSvg(stats) {
  const { solved, contest, ranking, username } = stats;

  return `<svg width="${WIDTH}" height="${HEIGHT}" viewBox="0 0 ${WIDTH} ${HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="cardBorder" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#F8BBD0"/>
      <stop offset="100%" stop-color="#EC407A"/>
    </linearGradient>
  </defs>
  <rect x="0.75" y="0.75" width="${WIDTH - 1.5}" height="${HEIGHT - 1.5}" rx="16" fill="#0d1117" stroke="url(#cardBorder)" stroke-width="1.5"/>

  <text x="24" y="30" font-family="'Fira Code', monospace" font-size="14" font-weight="600" fill="#F8BBD0">LEETCODE &#183; ${username}</text>
  <text x="${WIDTH - 24}" y="30" text-anchor="end" font-family="'Fira Code', monospace" font-size="12" fill="#8b8b96">Rank #${ranking?.toLocaleString?.() ?? ranking}</text>

  ${bar("Easy", solved.easy, solved.all, 66, "#F8BBD0")}
  ${bar("Medium", solved.medium, solved.all, 96, "#F48FB1")}
  ${bar("Hard", solved.hard, solved.all, 126, "#EC407A")}

  <line x1="24" y1="146" x2="${WIDTH - 24}" y2="146" stroke="#F48FB1" stroke-opacity="0.15"/>

  <text x="24" y="172" font-family="'Fira Code', monospace" font-size="12" fill="#e0e0e0">Total Solved: <tspan fill="#F8BBD0" font-weight="600">${solved.all}</tspan></text>
  <text x="${WIDTH - 24}" y="172" text-anchor="end" font-family="'Fira Code', monospace" font-size="12" fill="#e0e0e0">Contest Rating: <tspan fill="#F8BBD0" font-weight="600">${
    contest ? Math.round(contest.rating) : "—"
  }</tspan></text>
</svg>`;
}

async function main() {
  const stats = await getProfileStats(USERNAME);
  const svg = buildSvg(stats);
  await mkdir(OUT_DIR, { recursive: true });
  await writeFile(`${OUT_DIR}/leetcode-summary.svg`, svg, "utf8");
  console.log(`✔ wrote ${OUT_DIR}/leetcode-summary.svg`);
}

main().catch((err) => {
  console.error("✘ generate-summary-card failed:", err);
  process.exit(1);
});
