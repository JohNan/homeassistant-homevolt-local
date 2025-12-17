
import argparse
import subprocess

import semver


def get_latest_tag():
    """Fetch the latest Git tag that is a valid semantic version."""
    try:
        # Fetch tags to ensure the local repository is up to date
        subprocess.run(
            ['git', 'fetch', '--tags'],  # noqa: S607
            check=True,
            capture_output=True,
        )

        # Get all tags, sorted by version in descending order
        tags_str = subprocess.check_output(
            ['git', 'tag', '--sort=-v:refname'],  # noqa: S607
        ).decode('utf-8')

        tags = tags_str.strip().split('\n')

        # Find the most recent tag that is a valid semantic version
        for tag in tags:
            if tag.startswith('v'):
                try:
                    # Strip the 'v' prefix and parse the version
                    version = semver.VersionInfo.parse(tag[1:])
                    return version
                except ValueError:
                    # Ignore tags that are not valid semantic versions
                    continue
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def main():
    """Calculate and print the next version."""
    parser = argparse.ArgumentParser(
        description='Calculate the next version for a release.'
    )
    parser.add_argument(
        '--version-bump',
        type=str,
        required=True,
        choices=['patch', 'minor', 'major'],
    )
    parser.add_argument('--prerelease', type=str, required=True)
    args = parser.parse_args()

    is_prerelease = args.prerelease.lower() == 'true'
    latest_version = get_latest_tag()

    if latest_version is None:
        # If no tags are found, start from version 0.0.0
        latest_version = semver.VersionInfo.parse("0.0.0")

    if is_prerelease:
        if latest_version.prerelease:
            # If the latest version is a pre-release, increment the beta number
            pr_parts = latest_version.prerelease.split('.')
            is_beta = (
                len(pr_parts) == 2
                and pr_parts[0] == 'beta'
                and pr_parts[1].isdigit()
            )
            if is_beta:
                beta_num = int(pr_parts[1]) + 1
                new_prerelease = f"beta.{beta_num}"
                new_version = latest_version.replace(prerelease=new_prerelease)
            else:
                # If the pre-release format is unexpected, bump the patch
                # and start a new beta series.
                new_version = latest_version.replace(
                    prerelease=None
                ).bump_patch().replace(prerelease="beta.1")
        else:
            # If the latest version is stable, bump it and start a new beta series
            if args.version_bump == 'patch':
                new_version = latest_version.bump_patch()
            elif args.version_bump == 'minor':
                new_version = latest_version.bump_minor()
            elif args.version_bump == 'major':
                new_version = latest_version.bump_major()
            new_version = new_version.replace(prerelease="beta.1")
    else:  # This is a final/stable release
        if latest_version.prerelease:
            # If the latest version is a pre-release, the new version is its
            # stable counterpart.
            new_version = latest_version.replace(prerelease=None)
        else:
            # If the latest version is stable, bump it as specified
            if args.version_bump == 'patch':
                new_version = latest_version.bump_patch()
            elif args.version_bump == 'minor':
                new_version = latest_version.bump_minor()
            elif args.version_bump == 'major':
                new_version = latest_version.bump_major()

    print(str(new_version))

if __name__ == '__main__':
    main()
