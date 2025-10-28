import json
import os
import sys

def update_version():
    """Update the version in the manifest file."""
    if len(sys.argv) < 2:
        print("No version specified")
        sys.exit(1)

    version = sys.argv[1]

    # Get the path to the manifest.json file
    manifest_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "homevolt_local",
        "manifest.json",
    )

    # Read the manifest file
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    # Update the version
    manifest["version"] = version

    # Write the manifest file
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    update_version()
