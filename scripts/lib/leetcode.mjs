// scripts/lib/leetcode.mjs
// Minimal client around LeetCode's public GraphQL endpoint.
// No API key required, but LeetCode is picky about headers — we mimic a browser request.

const ENDPOINT = "https://leetcode.com/graphql/";

async function gql(query, variables) {
  const res = await fetch(ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Referer": "https://leetcode.com",
      "User-Agent": "Mozilla/5.0 (compatible; leetcode-pink-viz/1.0; +https://github.com)",
    },
    body: JSON.stringify({ query, variables }),
  });

  if (!res.ok) {
    throw new Error(`LeetCode GraphQL request failed: ${res.status} ${res.statusText}`);
  }

  const json = await res.json();
  if (json.errors) {
    throw new Error(`LeetCode GraphQL errors: ${JSON.stringify(json.errors)}`);
  }
  return json.data;
}

/** Full contest-by-contest rating history (only attended contests, chronological). */
export async function getContestHistory(username) {
  const query = /* GraphQL */ `
    query userContestRankingInfo($username: String!) {
      userContestRankingHistory(username: $username) {
        attended
        rating
        ranking
        trendDirection
        problemsSolved
        totalProblems
        finishTimeInSeconds
        contest {
          title
          startTime
        }
      }
      userContestRanking(username: $username) {
        rating
        globalRanking
        totalParticipants
        topPercentage
        attendedContestsCount
        badge {
          name
        }
      }
    }
  `;
  const data = await gql(query, { username });
  const history = (data.userContestRankingHistory || [])
    .filter((c) => c.attended)
    .sort((a, b) => a.contest.startTime - b.contest.startTime);

  return {
    history,
    summary: data.userContestRanking,
  };
}

/** Daily submission calendar for the current + previous year, merged. */
export async function getSubmissionCalendar(username) {
  const query = /* GraphQL */ `
    query userProfileCalendar($username: String!) {
      matchedUser(username: $username) {
        userCalendar {
          activeYears
          streak
          totalActiveDays
          submissionCalendar
        }
      }
    }
  `;
  const data = await gql(query, { username });
  const cal = data.matchedUser?.userCalendar;
  if (!cal) throw new Error("No userCalendar returned — check the username.");

  const raw = JSON.parse(cal.submissionCalendar || "{}");
  // raw: { "<unix_seconds_day_start_utc>": count, ... }
  const days = Object.entries(raw)
    .map(([ts, count]) => ({ date: new Date(Number(ts) * 1000), count: Number(count) }))
    .sort((a, b) => a.date - b.date);

  return {
    days,
    streak: cal.streak,
    totalActiveDays: cal.totalActiveDays,
    activeYears: cal.activeYears,
  };
}

/** Overall solved-problem stats, used for the compact summary card. */
export async function getProfileStats(username) {
  const query = /* GraphQL */ `
    query userProblemsSolved($username: String!) {
      matchedUser(username: $username) {
        username
        profile {
          ranking
        }
        submitStatsGlobal {
          acSubmissionNum {
            difficulty
            count
          }
        }
      }
      userContestRanking(username: $username) {
        rating
        globalRanking
        attendedContestsCount
        topPercentage
      }
    }
  `;
  const data = await gql(query, { username });
  const m = data.matchedUser;
  if (!m) throw new Error("No matchedUser returned — check the username.");

  const byDifficulty = Object.fromEntries(
    m.submitStatsGlobal.acSubmissionNum.map((d) => [d.difficulty, d.count])
  );

  return {
    username: m.username,
    ranking: m.profile.ranking,
    solved: {
      all: byDifficulty.All || 0,
      easy: byDifficulty.Easy || 0,
      medium: byDifficulty.Medium || 0,
      hard: byDifficulty.Hard || 0,
    },
    contest: data.userContestRanking,
  };
}
