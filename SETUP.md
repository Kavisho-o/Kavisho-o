# Setup

This repo generates two custom, on-brand LeetCode visuals as SVGs and refreshes them automatically:

- `assets/leetcode-summary.svg` — compact solved-problem stat card
- `assets/contest-rating.svg` — glowing neon smooth-curve contest rating chart, with auto-detected personal-best milestones
- `assets/submission-orbit.svg` — a radial "orbit" heatmap of the last 365 days of submissions (spiral layout, glow-intensity dots) instead of the standard GitHub-style square grid

None of it uses a third-party widget service — every asset is generated locally from LeetCode's own public GraphQL API (`https://leetcode.com/graphql/`), so nothing is hardcoded and nothing depends on an external rendering server staying online.

## 1. Fork / clone this repo

Push it to its own GitHub repository, e.g. `leetcode-pink-viz`, or drop the `scripts/`, `.github/workflows/`, and `assets/` folders straight into your existing profile repo (`<your-username>/<your-username>`).

## 2. Set your LeetCode username

Two options:

- **Quick:** edit the `LEETCODE_USERNAME` default in `scripts/lib/leetcode.mjs`-consuming scripts (currently defaults to `Kavish0_0`).
- **Recommended:** in your repo, go to **Settings → Secrets and variables → Actions → Variables** and add a repository variable named `LEETCODE_USERNAME` with your handle. The workflow already reads `vars.LEETCODE_USERNAME` and falls back to the default if it's unset.

## 3. Enable the workflow

`.github/workflows/update-leetcode-visuals.yml` is already wired up to:

- run every 6 hours (`cron: "17 */6 * * *"`)
- run on every push that touches `scripts/**`
- run on demand via **Actions → Update LeetCode Visuals → Run workflow**

It regenerates the three SVGs and commits them back to `assets/` only if they changed, using `stefanzweifel/git-auto-commit-action`. No manual steps, no cron jobs to host yourself.

Make sure **Settings → Actions → General → Workflow permissions** is set to **Read and write permissions**, otherwise the commit-back step will fail.

## 4. Run it locally (optional)

```bash
npm install        # no dependencies today, but future-proofs it
LEETCODE_USERNAME=your_handle node scripts/generate-all.mjs
```

Requires Node 20+ (native `fetch`). This will fail with `403` if run from an environment LeetCode blocks (some CI sandboxes, some corporate networks) — GitHub Actions runners work fine.

## 5. Point the README at the assets

The README below already references:

```
assets/leetcode-summary.svg
assets/contest-rating.svg
assets/submission-orbit.svg
```

using the raw GitHub path pattern:

```
https://raw.githubusercontent.com/<user>/<repo>/main/assets/<file>.svg
```

If you embed this section inside your profile README (`<username>/<username>`), use the same repo for both, or point the `src` at whichever repo hosts `assets/`.

## Why hand-rolled SVG instead of an existing widget?

- Full control over the exact palette (`#F48FB1` / `#EC407A` / `#F8BBD0` / `#0d1117`) so it matches the rest of the README pixel-for-pixel.
- No dependency on a third-party rendering service's uptime or rate limits.
- The contest chart and heatmap layouts (milestone-annotated glow curve, spiral orbit heatmap) aren't offered by any existing badge/widget service — they had to be built from raw `userContestRankingHistory` / `submissionCalendar` data.

## Extending it

- `scripts/lib/leetcode.mjs` — all LeetCode GraphQL queries live here; add new ones the same way.
- `scripts/lib/svg-utils.mjs` — shared helpers (Catmull-Rom path smoothing, escaping, date formatting).
- Each `generate-*.mjs` script is self-contained: fetch → build SVG string → write to `assets/`.
