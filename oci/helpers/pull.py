import argparse
import subprocess
import sys

def pull_image(crane_path, image, digest, platform, output):
    full_image = f"{image}@{digest}"

    # Construct and execute the crane pull command
    command = [crane_path, 'pull', '--format=oci', '--platform', platform, full_image, output]
    subprocess.run(command, check=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pull OCI image using Crane")
    parser.add_argument("--crane", required=True, help="Path to the crane binary")
    parser.add_argument("--image", required=True, help="OCI image to pull")
    parser.add_argument("--digest", required=True, help="Digest of the OCI image")
    parser.add_argument("--platform", required=True, help="Platform for which to pull the image")
    parser.add_argument("--output", required=True, help="Path to the output tar file")

    args = parser.parse_args()

    try:
        pull_image(args.crane, args.image, args.digest, args.platform, args.output)
    except subprocess.CalledProcessError as e:
        print(f"Error pulling image: {e}", file=sys.stderr)
        sys.exit(1)
