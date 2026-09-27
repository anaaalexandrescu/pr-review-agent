"""
Repo Health Check — MCP server.
"""

import os
import requests
from mcp.server import MCPServer

mcp = MCPServer("Repo Health Check")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _github_get(path: str, params: dict | None = None):
    """Common helper for GET requests to the GitHub API. Raises on error."""
    url = f"https://api.github.com{path}"
    response = requests.get(url, headers=_github_headers(), params=params, timeout=10)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def get_github_issues(repo: str, state: str = "open") -> str:
    """
    Returns the issues from a GitHub repo.

    Args:
        repo: repo name in "owner/repo" format, e.g. "anaaalexandrescu/ASCII-art-studio"
        state: "open", "closed" or "all" (default "open")
    """
    try:
        issues = _github_get(f"/repos/{repo}/issues", params={"state": state, "per_page": 20})
    except requests.exceptions.HTTPError as e:
        return f"Error querying the GitHub API: {e}"
    except requests.exceptions.RequestException as e:
        return f"Network error: {e}"

    real_issues = [i for i in issues if "pull_request" not in i]

    if not real_issues:
        return f"No {state} issues found for {repo}."

    lines = [f"{state} issues for {repo}:"]
    for issue in real_issues:
        lines.append(f"- #{issue['number']}: {issue['title']} (created: {issue['created_at'][:10]})")

    return "\n".join(lines)


@mcp.tool()
def get_github_prs(repo: str, state: str = "open") -> str:
    """
    Returns the pull requests from a GitHub repo.

    Args:
        repo: repo name in "owner/repo" format
        state: "open", "closed" or "all" (default "open")
    """
    try:
        prs = _github_get(f"/repos/{repo}/pulls", params={"state": state, "per_page": 20})
    except requests.exceptions.HTTPError as e:
        return f"Error querying the GitHub API: {e}"
    except requests.exceptions.RequestException as e:
        return f"Network error: {e}"

    if not prs:
        return f"No {state} pull requests found for {repo}."

    lines = [f"{state} pull requests for {repo}:"]
    for pr in prs:
        lines.append(f"- #{pr['number']}: {pr['title']} (created: {pr['created_at'][:10]})")

    return "\n".join(lines)


@mcp.tool()
def get_commit_activity(repo: str, limit: int = 10) -> str:
    """
    Returns the most recent commits from a GitHub repo.

    Args:
        repo: repo name in "owner/repo" format
        limit: maximum number of commits to return (default 10)
    """
    try:
        commits = _github_get(f"/repos/{repo}/commits", params={"per_page": limit})
    except requests.exceptions.HTTPError as e:
        return f"Error querying the GitHub API: {e}"
    except requests.exceptions.RequestException as e:
        return f"Network error: {e}"

    if not commits:
        return f"No commits found for {repo}."

    lines = [f"Last {len(commits)} commits for {repo}:"]
    for c in commits:
        message = c["commit"]["message"].split("\n")[0]
        author = c["commit"]["author"]["name"]
        date = c["commit"]["author"]["date"][:10]
        lines.append(f"- {date} ({author}): {message}")

    return "\n".join(lines)


@mcp.tool()
def get_pr_diff(repo: str, pr_number: int) -> str:
    """
    Returns the code diff introduced by a specific Pull Request.

    Args:
        repo: repo name in "owner/repo" format, e.g. "anaaalexandrescu/ASCII-art-studio"
        pr_number: the PR number
    """
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = _github_headers()
    headers["Accept"] = "application/vnd.github.v3.diff"

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        diff_text = response.text
        if not diff_text.strip():
            return f"PR #{pr_number} contains no code changes."
        return diff_text[:8000]
    except requests.exceptions.HTTPError as e:
        return f"Error fetching the diff for PR #{pr_number}: {e}"
    except requests.exceptions.RequestException as e:
        return f"Network error: {e}"


@mcp.tool()
def post_pr_comment(repo: str, pr_number: int, comment: str) -> str:
    """
    Publishes a review comment on an existing GitHub Pull Request.

    Args:
        repo: repo name in "owner/repo" format
        pr_number: the PR number to comment on
        comment: the comment text (Markdown formatted)
    """
    if not GITHUB_TOKEN:
        return "Error: GITHUB_TOKEN is not set in the environment variables. The write action was refused."

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = _github_headers()

    try:
        response = requests.post(url, headers=headers, json={"body": comment}, timeout=15)
        response.raise_for_status()
        return f"Comment successfully posted on PR #{pr_number}."
    except requests.exceptions.HTTPError as e:
        return f"Error posting the comment on PR #{pr_number}: {e}"
    except requests.exceptions.RequestException as e:
        return f"Network error: {e}"


if __name__ == "__main__":
    mcp.run()