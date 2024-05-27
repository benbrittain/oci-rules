import argparse
import tarfile
import os
import sys

def create_tar(paths, compress, filename):
    with tarfile.open(filename, "w:gz" if compress == "true" else "w") as tar:
        for path in paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Path not found: {path}")
            tar.add(path, arcname=os.path.basename(path))

def read_paths(file_path):
    try:
        with open(file_path, "r") as file:
            return file.read().splitlines()
    except IOError as e:
        print(f"Failed to read file {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a tar file from specified paths"
    )
    parser.add_argument(
        "--compress", required=True, help="Whether to gzip the tar file"
    )
    parser.add_argument(
        "--file_path",
        required=True,
        help="Path to the file containing paths to include in the tar file",
    )
    parser.add_argument("--filename", required=True, help="Name of the tar file")
    args = parser.parse_args()

    paths = read_paths(args.file_path)

    try:
        create_tar(paths, args.compress, args.filename)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
