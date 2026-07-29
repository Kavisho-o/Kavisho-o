// scripts/generate-all.mjs
// Runs all three generators in sequence and fails loudly if any one fails,
// so a broken LeetCode API response never gets silently ignored in CI.

const scripts = [
  "./generate-summary-card.mjs",
  "./generate-contest-chart.mjs",
  "./generate-heatmap.mjs",
];

for (const s of scripts) {
  console.log(`\n▶ running ${s}`);
  await import(s);
}
