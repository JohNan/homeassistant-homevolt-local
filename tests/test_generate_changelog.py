
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from semver import VersionInfo

# Add the scripts directory to the Python path
sys.path.append('.github/scripts')

from generate_changelog import generate_changelog, get_latest_tags

# Mock classes for GitHub API objects
class MockCommit:
    def __init__(self, sha, date):
        self.sha = sha
        self.commit = MagicMock(committer=MagicMock(date=date))

class MockTag:
    def __init__(self, name, sha, date):
        self.name = name
        self.commit = MockCommit(sha, date)

class MockLabel:
    def __init__(self, name):
        self.name = name

class MockPullRequest:
    def __init__(self, number, title, user, labels, merged_at):
        self.number = number
        self.title = title
        self.user = MagicMock(login=user)
        self.labels = [MockLabel(label) for label in labels]
        self.merged = True
        self.merged_at = merged_at

@patch('generate_changelog.Github')
def test_get_latest_tags(mock_github):
    """Test the get_latest_tags function."""
    mock_repo = MagicMock()
    mock_github.return_value.get_repo.return_value = mock_repo

    mock_repo.get_tags.return_value = [
        MockTag("v1.1.0", "sha1", datetime(2023, 1, 15)),
        MockTag("v1.0.0", "sha2", datetime(2023, 1, 10)),
        MockTag("v1.2.0-beta.1", "sha3", datetime(2023, 1, 20)),
    ]

    latest_tag, latest_stable_tag = get_latest_tags()

    assert latest_tag.name == "v1.2.0-beta.1"
    assert latest_stable_tag.name == "v1.1.0"

@patch('generate_changelog.Github')
def test_generate_changelog_stable_release(mock_github):
    """Test changelog generation for a stable release."""
    mock_repo = MagicMock()
    mock_github.return_value.get_repo.return_value = mock_repo

    mock_repo.get_tags.return_value = [
        MockTag("v1.0.0", "stable_sha", datetime(2023, 1, 10)),
    ]
    mock_repo.get_commit.return_value = MockCommit(
        "stable_sha", datetime(2023, 1, 10)
    )

    mock_repo.get_pulls.return_value = [
        MockPullRequest(1, "Feature A", "user1", ["feature"], datetime(2023, 1, 12)),
        MockPullRequest(2, "Fix B", "user2", ["bugfix"], datetime(2023, 1, 14)),
        MockPullRequest(3, "Old PR", "user3", ["enhancement"], datetime(2023, 1, 8)),
    ]

    changelog = generate_changelog("1.1.0")

    assert "## What's Changed" in changelog
    assert "✨ New features" in changelog
    assert "- Feature A by @user1 in #1" in changelog
    assert "🐛 Bug fixes" in changelog
    assert "- Fix B by @user2 in #2" in changelog
    assert "Old PR" not in changelog

@patch('generate_changelog.Github')
def test_generate_changelog_prerelease(mock_github):
    """Test changelog generation for a pre-release."""
    mock_repo = MagicMock()
    mock_github.return_value.get_repo.return_value = mock_repo

    mock_repo.get_tags.return_value = [
        MockTag("v1.0.0", "stable_sha", datetime(2023, 1, 10)),
    ]
    mock_repo.get_commit.return_value = MockCommit(
        "stable_sha", datetime(2023, 1, 10)
    )

    mock_repo.get_pulls.return_value = [
        MockPullRequest(1, "Feature C", "user1", ["feature"], datetime(2023, 1, 12)),
    ]

    changelog = generate_changelog("1.1.0-beta.1")

    assert "- Feature C by @user1 in #1" in changelog
