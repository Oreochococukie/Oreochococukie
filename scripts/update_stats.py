"""Fetch account statistics from GitHub and regenerate both profile SVGs."""

import json
import os
import subprocess
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STATS_PATH = ROOT / "stats.json"
LOGIN = os.environ.get("PROFILE_USERNAME", "Oreochococukie")
API = "https://api.github.com/graphql"


def resolve_token() -> str:
    token = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    if os.environ.get("GITHUB_ACTIONS") == "true":
        raise RuntimeError("ACCESS_TOKEN or GITHUB_TOKEN is required")
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], check=True, capture_output=True, text=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise RuntimeError("Authenticate gh or provide GITHUB_TOKEN") from error
    return result.stdout.strip()


def graphql(token: str, query: str, variables: dict) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(API, data=payload, method="POST")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("User-Agent", f"{LOGIN}-profile-readme")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise RuntimeError(f"GitHub API returned {error.code}: {detail}") from error
    if body.get("errors"):
        raise RuntimeError(f"GitHub GraphQL failed: {body['errors']}")
    return body["data"]


def fetch_profile(token: str, start: str, end: str) -> dict:
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        following { totalCount }
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar { totalContributions }
          totalCommitContributions
          totalPullRequestContributions
        }
      }
    }
    """
    return graphql(token, query, {"login": LOGIN, "from": start, "to": end})["user"]


def fetch_repositories(token: str) -> list[dict]:
    query = """
    query($login: String!, $cursor: String) {
      user(login: $login) {
        repositories(
          first: 100,
          after: $cursor,
          ownerAffiliations: OWNER,
          orderBy: {field: PUSHED_AT, direction: DESC}
        ) {
          pageInfo { hasNextPage endCursor }
          nodes {
            name
            isFork
            isPrivate
            pushedAt
            stargazerCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name } }
            }
          }
        }
      }
    }
    """
    repositories: list[dict] = []
    cursor = None
    while True:
        data = graphql(token, query, {"login": LOGIN, "cursor": cursor})["user"]["repositories"]
        repositories.extend(data["nodes"])
        if not data["pageInfo"]["hasNextPage"]:
            return repositories
        cursor = data["pageInfo"]["endCursor"]


def main() -> None:
    token = resolve_token()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    start = now - timedelta(days=365)
    profile = fetch_profile(token, start.isoformat(), now.isoformat())
    repositories = fetch_repositories(token)

    languages: Counter[str] = Counter()
    for repository in repositories:
        for edge in repository["languages"]["edges"]:
            languages[edge["node"]["name"]] += edge["size"]

    active_repository = next(
        (
            repository["name"]
            for repository in repositories
            if repository["name"].lower() != LOGIN.lower()
        ),
        LOGIN,
    )
    contributions = profile["contributionsCollection"]
    stats = {
        "login": LOGIN,
        "generated_at": now.isoformat(),
        "created_at": profile["createdAt"],
        "repos_total": len(repositories),
        "repos_public": sum(not repository["isPrivate"] for repository in repositories),
        "stars_received": sum(repository["stargazerCount"] for repository in repositories),
        "followers": profile["followers"]["totalCount"],
        "following": profile["following"]["totalCount"],
        "contributions_365d": contributions["contributionCalendar"]["totalContributions"],
        "commits_365d": contributions["totalCommitContributions"],
        "pull_requests_365d": contributions["totalPullRequestContributions"],
        "active_repository": active_repository,
        "top_languages": [name for name, _ in languages.most_common(4)],
    }
    STATS_PATH.write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats, indent=2))

    import generate_profile

    generate_profile.main()


if __name__ == "__main__":
    main()
