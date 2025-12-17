
import sys
from unittest.mock import patch

import pytest
from semver import VersionInfo

# Add the scripts directory to the Python path
sys.path.append('.github/scripts')

from calculate_version import get_latest_tag, main

@pytest.mark.parametrize(
    "tags, expected_version",
    [
        # No tags exist
        ([], None),
        # Simple case with one tag
        (["v1.0.0"], VersionInfo.parse("1.0.0")),
        # Multiple tags, should return the highest
        (["v1.0.0", "v1.1.0", "v0.9.0"], VersionInfo.parse("1.1.0")),
        # Tags with pre-release identifiers
        (["v1.0.0", "v1.1.0-beta.1"], VersionInfo.parse("1.1.0-beta.1")),
        # Invalid tags should be ignored
        (["v1.0.0", "not-a-version"], VersionInfo.parse("1.0.0")),
        # Tags without 'v' prefix should be ignored by the script's logic
        (["1.0.0"], None),
    ],
)
def test_get_latest_tag(tags, expected_version):
    """Test the get_latest_tag function."""
    with patch('subprocess.check_output') as mock_check_output:
        mock_check_output.return_value = '\n'.join(tags).encode('utf-8')
        assert get_latest_tag() == expected_version

@pytest.mark.parametrize(
    "latest_tag, version_bump, prerelease, expected_version",
    [
        # Initial release
        (None, "patch", False, "0.0.1"),
        # Standard patch bump
        ("1.2.3", "patch", False, "1.2.4"),
        # Standard minor bump
        ("1.2.3", "minor", False, "1.3.0"),
        # Standard major bump
        ("1.2.3", "major", False, "2.0.0"),
        # Create first pre-release from stable
        ("1.2.3", "patch", True, "1.2.4-beta.1"),
        # Increment an existing pre-release
        ("1.2.4-beta.1", "patch", True, "1.2.4-beta.2"),
        # Finalize a pre-release
        ("1.2.4-beta.2", "patch", False, "1.2.4"),
        # New pre-release with a minor bump
        ("1.2.3", "minor", True, "1.3.0-beta.1"),
        # New pre-release with a major bump
        ("1.2.3", "major", True, "2.0.0-beta.1"),
    ],
)
def test_main_version_calculation(
    capsys, latest_tag, version_bump, prerelease, expected_version
):
    """Test the main version calculation logic."""
    args = [
        'calculate_version.py',
        '--version-bump',
        version_bump,
        '--prerelease',
        str(prerelease),
    ]

    mock_tag = VersionInfo.parse(latest_tag) if latest_tag else None

    with patch('calculate_version.get_latest_tag', return_value=mock_tag):
        with patch.object(sys, 'argv', args):
            main()
            captured = capsys.readouterr()
            assert captured.out.strip() == expected_version
