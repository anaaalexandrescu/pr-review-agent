"""
Tests for the tools in server.py.
"""

from unittest.mock import patch, MagicMock
import server


def _mock_response(json_data, status_code=200):
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_data
    mock_resp.status_code = status_code
    mock_resp.raise_for_status = MagicMock()
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = Exception("HTTP error")
    return mock_resp


@patch("server.requests.get")
def test_get_github_issues_returns_formatted_list(mock_get):
    mock_get.return_value = _mock_response([
        {"number": 1, "title": "Bug in parser", "created_at": "2026-01-01T00:00:00Z"},
        {"number": 2, "title": "Add feature X", "created_at": "2026-01-02T00:00:00Z"},
    ])

    result = server.get_github_issues("owner/repo")

    assert "#1: Bug in parser" in result
    assert "#2: Add feature X" in result


@patch("server.requests.get")
def test_get_github_issues_filters_out_pull_requests(mock_get):
    mock_get.return_value = _mock_response([
        {"number": 1, "title": "Real issue", "created_at": "2026-01-01T00:00:00Z"},
        {"number": 2, "title": "A PR", "created_at": "2026-01-02T00:00:00Z", "pull_request": {}},
    ])

    result = server.get_github_issues("owner/repo")

    assert "Real issue" in result
    assert "A PR" not in result


@patch("server.requests.get")
def test_get_github_issues_handles_empty_list(mock_get):
    mock_get.return_value = _mock_response([])

    result = server.get_github_issues("owner/repo")

    assert "No open issues found" in result


@patch("server.requests.get")
def test_get_github_prs_returns_formatted_list(mock_get):
    mock_get.return_value = _mock_response([
        {"number": 5, "title": "Refactor auth", "created_at": "2026-02-01T00:00:00Z"},
    ])

    result = server.get_github_prs("owner/repo")

    assert "#5: Refactor auth" in result


@patch("server.requests.get")
def test_get_commit_activity_returns_formatted_list(mock_get):
    mock_get.return_value = _mock_response([
        {
            "commit": {
                "message": "Fix crash on startup\n\nLonger description here",
                "author": {"name": "Ana", "date": "2026-03-01T12:00:00Z"},
            }
        }
    ])

    result = server.get_commit_activity("owner/repo")

    assert "Fix crash on startup" in result
    assert "Longer description here" not in result
    assert "Ana" in result


@patch("server.requests.get")
def test_get_github_issues_handles_network_error(mock_get):
    mock_get.side_effect = server.requests.exceptions.ConnectionError("no network")

    result = server.get_github_issues("owner/repo")

    assert "Network error" in result

@patch("server.requests.get")
def test_get_pr_diff_returns_raw_diff(mock_get):
    mock_resp = MagicMock()
    mock_resp.text = "diff --git a/main.py b/main.py\n+print('hello')"
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = server.get_pr_diff("owner/repo", 1)
    assert "+print('hello')" in result


@patch("server.requests.post")
def test_post_pr_comment_success(mock_post, monkeypatch):
    monkeypatch.setattr(server, "GITHUB_TOKEN", "fake_token")
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    result = server.post_pr_comment("owner/repo", 1, "LGTM!")
    assert "successfully posted" in result


def test_post_pr_comment_requires_token(monkeypatch):
    monkeypatch.setattr(server, "GITHUB_TOKEN", None)
    result = server.post_pr_comment("owner/repo", 1, "LGTM!")
    assert "GITHUB_TOKEN is not set" in result