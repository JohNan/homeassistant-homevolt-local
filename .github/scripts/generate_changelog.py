
import argparse
import os
from datetime import datetime

import semver
from github import Github

# Configuration for changelog categories based on PR labels
CATEGORIES = {
    "🚨 Breaking changes": ["breaking-change"],
    "✨ New features": ["new-feature", "feature"],
    "🐛 Bug fixes": ["bugfix", "bug", "fix"],
    "🚀 Enhancements": ["enhancement", "refactor", "performance"],
    "🧰 Maintenance": ["maintenance", "chore", "ci"],
    "📚 Documentation": ["documentation", "docs"],
    "⬆️ Dependency updates": ["dependencies"],
}

EXCLUDE_LABELS = ["skip-changelog"]


def get_latest_tags():
    """Fetch the latest stable and overall Git tags."""
    g = Github(os.getenv("GITHUB_TOKEN"))
    repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))

    tags = repo.get_tags()

    valid_tags = []
    for tag in tags:
        if tag.name.startswith('v'):
            try:
                version = semver.VersionInfo.parse(tag.name[1:])
                valid_tags.append((version, tag))
            except ValueError:
                continue

    # Sort tags by version descending
    valid_tags.sort(key=lambda x: x[0], reverse=True)

    latest_tag_obj = valid_tags[0][1] if valid_tags else None

    latest_stable_tag_obj = None
    for version, tag in valid_tags:
        if not version.prerelease:
            latest_stable_tag_obj = tag
            break

    return latest_tag_obj, latest_stable_tag_obj


def generate_changelog(version_str):
    """Generate a changelog from pull requests."""
    g = Github(os.getenv("GITHUB_TOKEN"))
    repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))

    try:
        new_version = semver.VersionInfo.parse(version_str)
    except ValueError:
        print(f"Error: Invalid version string provided: {version_str}")
        return "Error generating changelog: Invalid version."

    latest_tag, latest_stable_tag = get_latest_tags()

    base_tag = None
    if new_version.prerelease:
        # For pre-releases, compare against the very last tag
        base_tag = latest_tag
    else:
        # For stable releases, compare against the last stable tag
        base_tag = latest_stable_tag

    if base_tag is None:
        print("No base tag found, generating changelog from the beginning of time.")
        since_date = datetime.min
    else:
        print(f"Generating changelog since base tag: {base_tag.name}")
        base_commit = repo.get_commit(base_tag.commit.sha)
        since_date = base_commit.commit.committer.date

    # Fetch pull requests merged since the base tag's commit date
    pulls = repo.get_pulls(state='closed', sort='updated', direction='desc')

    categorized_prs = {key: [] for key in CATEGORIES}

    for pr in pulls:
        if not pr.merged or pr.merged_at < since_date:
            continue

        pr_labels = [label.name for label in pr.labels]

        if any(label in EXCLUDE_LABELS for label in pr_labels):
            continue

        for category_title, category_labels in CATEGORIES.items():
            if any(label in pr_labels for label in category_labels):
                categorized_prs[category_title].append(pr)
                break

    # Build the changelog markdown
    changelog_lines = ["## What's Changed"]
    for category_title, pr_list in categorized_prs.items():
        if pr_list:
            changelog_lines.append(f"\n### {category_title}")
            for pr in sorted(pr_list, key=lambda p: p.number):
                line = (
                    f"- {pr.title} by @{pr.user.login} in #{pr.number}"
                )
                changelog_lines.append(line)

    return '\n'.join(changelog_lines)


def main():
    """Parse arguments and generate the changelog."""
    parser = argparse.ArgumentParser(
        description='Generate a changelog from GitHub pull requests.'
    )
    parser.add_argument(
        '--version',
        type=str,
        required=True,
        help='The new version being released.',
    )
    args = parser.parse_args()

    changelog = generate_changelog(args.version)
    print(changelog)


if __name__ == "__main__":
    main()
