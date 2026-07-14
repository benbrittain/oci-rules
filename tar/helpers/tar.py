import argparse
import gzip
import json
import os
import sys
import tarfile


def reset(ti: tarfile.TarInfo) -> tarfile.TarInfo:
    """Normalise metadata so identical trees produce byte-identical tars."""
    ti.mtime = 0
    ti.uid = ti.gid = 0
    ti.uname = ti.gname = ""
    return ti


def parents(arcname):
    """Ancestor directory arcnames of `arcname`, outermost first."""
    parts = arcname.strip("/").split("/")[:-1]
    out, cur = [], ""
    for part in parts:
        cur = part if not cur else cur + "/" + part
        out.append(cur)
    return out


def collect(src, arcname, mode, members):
    """Record `src` under `arcname`, recursing into directories.

    Symlinks are dereferenced via realpath so the layer carries real bytes
    rather than links into the build sandbox.
    """
    src = os.path.realpath(src)
    prev = members.get(arcname)
    if os.path.isdir(src):
        if prev is not None and prev[0] is not None:
            raise ValueError(f"Archive path collision at {arcname}: file vs directory")
        members.setdefault(arcname, (None, None))
        for name in sorted(os.listdir(src)):
            collect(os.path.join(src, name), arcname + "/" + name, None, members)
    else:
        if prev is not None and prev != (src, mode):
            raise ValueError(f"Archive path collision at {arcname}")
        members[arcname] = (src, mode)


def create_tar(manifest, compress, filename):
    members = {}
    for entry in manifest:
        collect(entry["src"], entry["arcname"].strip("/"), entry.get("mode"), members)

    # Synthesise parent directories so the layer carries explicit entries.
    for arcname in list(members):
        for parent in parents(arcname):
            if members.get(parent, (None, None))[0] is not None:
                raise ValueError(f"Archive path collision at {parent}: file vs directory")
            members.setdefault(parent, (None, None))

    raw_fobj = gz = None
    if compress == "true":
        # filename="" keeps the output name out of the gzip header (otherwise it
        # is read from fileobj.name), and mtime=0 zeroes the header timestamp, so
        # the compressed stream is reproducible.
        raw_fobj = open(filename, "wb")
        gz = gzip.GzipFile(filename="", fileobj=raw_fobj, mode="wb", mtime=0)
        tar = tarfile.open(fileobj=gz, mode="w|")
    else:
        tar = tarfile.open(filename, "w")
    try:
        # Sorting by arcname is deterministic and keeps parents before children.
        for arcname in sorted(members):
            src, mode = members[arcname]
            if src is None:
                ti = reset(tarfile.TarInfo(arcname + "/"))
                ti.type = tarfile.DIRTYPE
                ti.mode = 0o755
                tar.addfile(ti)
                continue
            if not os.path.exists(src):
                raise FileNotFoundError(f"Path not found: {src}")
            ti = reset(tar.gettarinfo(src, arcname))
            if mode:
                ti.mode = int(mode, 8)
            elif ti.isreg():
                ti.mode = 0o755 if ti.mode & 0o111 else 0o644
            if ti.isreg():
                with open(src, "rb") as f:
                    tar.addfile(ti, f)
            else:
                tar.addfile(ti)
    finally:
        tar.close()
        if gz is not None:
            gz.close()
            raw_fobj.close()


def read_manifest(path):
    try:
        with open(path, "r") as file:
            return json.load(file)
    except IOError as e:
        print(f"Failed to read manifest {path}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a deterministic tar from a manifest"
    )
    parser.add_argument(
        "--compress", required=True, help="Whether to gzip the tar file"
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to a JSON manifest of {arcname, src, mode} entries",
    )
    parser.add_argument("--filename", required=True, help="Name of the tar file")
    args = parser.parse_args()

    try:
        create_tar(read_manifest(args.manifest), args.compress, args.filename)
    except (FileNotFoundError, ValueError) as e:
        print(e, file=sys.stderr)
        sys.exit(1)
