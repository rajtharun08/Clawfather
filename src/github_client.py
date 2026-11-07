import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple

try:
    import requests
except ImportError:
    requests = None

GRAPHQL_QUERY = """
query($userName: String!) {
  user(login: $userName) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
"""

def map_streak_to_cat_rank(streak_days: int) -> int:
    """
    Maps consecutive commit streak days to Cat Rank (0 to 4):
      Rank 0 — The Scavenger (0–2 Days): Shivering stray cat huddled in the cold
      Rank 1 — The Street Runner (3–6 Days): Newsie cat with newspaper
      Rank 2 — The Alley Enforcer (7–10 Days): Pinstripe vest & unlit cigar
      Rank 3 — The Made Cat (11–14 Days): Flat cap, cigar, folded arms
      Rank 4 — The Clawfather (15+ Days): Plump Mafia Don in velvet armchair
    """
    if streak_days <= 2:
        return 0
    elif streak_days <= 6:
        return 1
    elif streak_days <= 10:
        return 2
    elif streak_days <= 14:
        return 3
    else:
        return 4

def map_volume_to_loot_tier(commits_today: int) -> int:
    """
    Maps daily/recent commit volume to Loot Tier (0 to 2):
      Tier 0 — The Scraps (0–2 Commits): Empty sardine tin with fish bones
      Tier 1 — The Cut (3–6 Commits): Banded cash rolls & gold pocket watch
      Tier 2 — The Vault (7+ Commits): Heavy wooden syndicate crate of cash & gold
    """
    if commits_today <= 2:
        return 0
    elif commits_today <= 6:
        return 1
    else:
        return 2

def fetch_github_metrics(
    username: str = None,
    token: str = None
) -> Tuple[int, int, int, int]:
    """
    Queries GitHub GraphQL API for the user's contribution calendar.
    Returns: (streak_days, commits_today, cat_rank, loot_tier)
    Falls back gracefully to mock/default values if no network/token is available.
    """
    username = username or os.environ.get("GITHUB_ACTOR") or os.environ.get("GH_USERNAME")
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    # If mock values provided in environment, respect them for testing
    if "MOCK_STREAK" in os.environ or "MOCK_COMMITS" in os.environ:
        streak_days = int(os.environ.get("MOCK_STREAK", 7))
        commits_today = int(os.environ.get("MOCK_COMMITS", 4))
        cat_rank = map_streak_to_cat_rank(streak_days)
        loot_tier = map_volume_to_loot_tier(commits_today)
        return streak_days, commits_today, cat_rank, loot_tier

    if not username or not token or requests is None:
        print("[The Clawfather Client] Notice: GitHub token or username not set. Using standard active streak defaults.")
        streak_days = 7
        commits_today = 5
        return streak_days, commits_today, map_streak_to_cat_rank(streak_days), map_volume_to_loot_tier(commits_today)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": GRAPHQL_QUERY, "variables": {"userName": username}},
            headers=headers,
            timeout=10
        )
        data = response.json()
        
        if "errors" in data or "data" not in data or not data["data"]["user"]:
            print(f"[The Clawfather Client] API Response error: {data.get('errors')}. Falling back to default.")
            return 7, 5, 2, 1

        calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        days = []
        for week in calendar["weeks"]:
            for day in week["contributionDays"]:
                days.append((day["date"], day["contributionCount"]))

        if not days:
            return 0, 0, 0, 0

        # Sort days by date ascending
        days.sort(key=lambda x: x[0])
        
        # Calculate commits in the last recorded day
        commits_today = days[-1][1]

        # Calculate consecutive streak
        streak_days = 0
        for date_str, count in reversed(days):
            if count > 0:
                streak_days += 1
            else:
                # If today has 0 commits, check if yesterday was part of streak
                if streak_days == 0 and date_str == days[-1][0]:
                    continue
                break

        cat_rank = map_streak_to_cat_rank(streak_days)
        loot_tier = map_volume_to_loot_tier(commits_today)
        return streak_days, commits_today, cat_rank, loot_tier

    except Exception as e:
        print(f"[The Clawfather Client] Network or parsing exception: {e}. Falling back to defaults.")
        return 7, 5, 2, 1

if __name__ == "__main__":
    streak, commits, rank, loot = fetch_github_metrics()
    print(f"The Clawfather Metrics: Streak={streak}d -> Rank {rank} | Commits={commits} -> Loot Tier {loot}")
