import argparse
import gzip
import hashlib
import json
import os
import shutil

EPOCH = "1970-01-01T00:00:00Z"

OCI_LAYER = "application/vnd.oci.image.layer.v1.tar+gzip"
OCI_CONFIG = "application/vnd.oci.image.config.v1+json"
OCI_MANIFEST = "application/vnd.oci.image.manifest.v1+json"
OCI_INDEX = "application/vnd.oci.image.index.v1+json"


def canon(obj) -> bytes:
    # Canonical JSON: sorted keys, no whitespace -> stable digest for stable input.
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_blob(blobs_dir: str, data: bytes, media_type: str) -> dict:
    digest = sha256_hex(data)
    path = os.path.join(blobs_dir, digest)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(data)
    return {"mediaType": media_type, "digest": "sha256:" + digest, "size": len(data)}


def read_json_blob(layout_dir: str, descriptor: dict) -> dict:
    algo, digest = descriptor["digest"].split(":", 1)
    with open(os.path.join(layout_dir, "blobs", algo, digest), "rb") as f:
        return json.load(f)


def resolve_manifest(layout_dir: str) -> dict:
    with open(os.path.join(layout_dir, "index.json"), "rb") as f:
        node = json.load(f)
    # Descend through any nested indexes. oci_pull resolves a single --platform,
    # so picking the first manifest is sufficient here.
    while "manifests" in node and "config" not in node:
        node = read_json_blob(layout_dir, node["manifests"][0])
    return node


def make_layer(blobs_dir: str, tar_path: str):
    """
    diff_id is the digest of the *uncompressed* tar (referenced by the config);
    the descriptor digest is the *compressed* blob (referenced by the manifest).
    """
    with open(tar_path, "rb") as f:
        raw = f.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    diff_id = "sha256:" + sha256_hex(raw)
    gz = gzip.compress(raw, compresslevel=6, mtime=0)
    return write_blob(blobs_dir, gz, OCI_LAYER), diff_id


def build(args):
    blobs_dir = os.path.join(args.output, "blobs", "sha256")
    os.makedirs(blobs_dir, exist_ok=True)

    base_manifest = resolve_manifest(args.base)
    base_config = read_json_blob(args.base, base_manifest["config"])

    # Copy the base layer blobs across (content addressed, so this is a no-op dedup).
    base_blobs = os.path.join(args.base, "blobs", "sha256")
    for layer in base_manifest["layers"]:
        digest = layer["digest"].split(":", 1)[1]
        dst = os.path.join(blobs_dir, digest)
        if not os.path.exists(dst):
            shutil.copyfile(os.path.join(base_blobs, digest), dst)

    new_layers, new_diff_ids = [], []
    for tar_path in args.tars or []:
        desc, diff_id = make_layer(blobs_dir, tar_path)
        new_layers.append(desc)
        new_diff_ids.append(diff_id)

    config = dict(base_config)
    config["created"] = EPOCH
    config["rootfs"] = {
        "type": "layers",
        "diff_ids": list(base_config.get("rootfs", {}).get("diff_ids", [])) + new_diff_ids,
    }

    cfg = dict(config.get("config", {}))
    if args.env:
        cfg["Env"] = list(cfg.get("Env", [])) + args.env
    if args.entrypoint:
        cfg["Entrypoint"] = args.entrypoint
        if not args.cmd:
            # An explicit entrypoint without a cmd clears any inherited default args.
            cfg.pop("Cmd", None)
    if args.cmd:
        cfg["Cmd"] = args.cmd
    if args.workdir:
        cfg["WorkingDir"] = args.workdir
    if args.user:
        cfg["User"] = args.user
    config["config"] = cfg

    # One non-empty history entry per added layer keeps history aligned with diff_ids.
    history = list(config.get("history", []))
    history += [{"created": EPOCH, "created_by": "oci_image"} for _ in new_diff_ids]
    config["history"] = history

    config_desc = write_blob(blobs_dir, canon(config), OCI_CONFIG)

    manifest = {
        "schemaVersion": 2,
        "mediaType": OCI_MANIFEST,
        "config": config_desc,
        "layers": base_manifest["layers"] + new_layers,
    }
    manifest_desc = write_blob(blobs_dir, canon(manifest), OCI_MANIFEST)
    # platform + ref name live on the index descriptor, not in the manifest blob.
    manifest_desc["platform"] = {
        "architecture": base_config.get("architecture", "amd64"),
        "os": base_config.get("os", "linux"),
    }
    manifest_desc["annotations"] = {"org.opencontainers.image.ref.name": args.name}

    index = {"schemaVersion": 2, "mediaType": OCI_INDEX, "manifests": [manifest_desc]}
    with open(os.path.join(args.output, "index.json"), "wb") as f:
        f.write(canon(index))
    with open(os.path.join(args.output, "oci-layout"), "wb") as f:
        f.write(canon({"imageLayoutVersion": "1.0.0"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble an OCI image layout")
    parser.add_argument("--base", required=True, help="Base OCI image layout directory")
    parser.add_argument("--output", required=True, help="Output OCI image layout directory")
    parser.add_argument("--name", required=True, help="Image ref name annotation")
    parser.add_argument("--tars", nargs="+", help="Layer tar files to append")
    parser.add_argument("--env", action="append", help="Environment variable, KEY=VALUE")
    parser.add_argument("--entrypoint", nargs="+", help="Entrypoint argv")
    parser.add_argument("--cmd", nargs="+", help="Cmd argv")
    parser.add_argument("--user", help="User")
    parser.add_argument("--workdir", help="Working directory")
    build(parser.parse_args())
