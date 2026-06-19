import argparse
import gzip
import os
import sys
import tarfile


def reset(ti: tarfile.TarInfo) -> tarfile.TarInfo:
    """Normalise metadata so identical trees produce byte-identical tars."""
    ti.mtime = 0
    ti.uid = ti.gid = 0
    ti.uname = ti.gname = ""
    return ti


def add_path(tar: tarfile.TarFile, path: str, arcname: str):
    ti = reset(tar.gettarinfo(path, arcname))
    if ti.isdir():
        tar.addfile(ti)
        for name in sorted(os.listdir(path)):
            add_path(tar, os.path.join(path, name), arcname + "/" + name)
    elif ti.isreg():
        with open(path, "rb") as f:
            tar.addfile(ti, f)
    else:
        tar.addfile(ti)


def create_tar(paths, compress, filename):
    raw_fobj = gz = None
    if compress == "true":
        # Pass an explicit fileobj so the gzip header carries no filename, and
        # mtime=0 so the compressed stream is reproducible.
        raw_fobj = open(filename, "wb")
        gz = gzip.GzipFile(fileobj=raw_fobj, mode="wb", mtime=0)
        tar = tarfile.open(fileobj=gz, mode="w|")
    else:
        tar = tarfile.open(filename, "w")
    try:
        for path in sorted(paths):
            if not os.path.exists(path):
                raise FileNotFoundError(f"Path not found: {path}")
            add_path(tar, path, os.path.basename(path))
    finally:
        tar.close()
        if gz is not None:
            gz.close()
            raw_fobj.close()


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
