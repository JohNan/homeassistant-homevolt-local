import json
import sys
from pathlib import Path


def update_version():
    """Update the version in the manifest file."""
    if len(sys.argv) < 2:
        print("No version specified")
        sys.exit(1)

    version = sys.argv[1]

    # Get the path to the manifest.json file
    manifest_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "homevolt_local"
        / "manifest.json"
    )

    # Read the manifest file
    with manifest_path.open() as f:
        manifest = json.load(f)

    # Update the version
    manifest["version"] = version

    # Write the manifest file
    with manifest_path.open("w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")  # Ensure trailing newline



if __name__ == "__main__":
    update_version()
