# oci-rules

Buck2 rules for the [Open Containers Initiative](https://opencontainers.org) image format.

## Installation

Add this repo as an external cell in your projects `.buckconfig`

```ini
[cells]
  # there will be other cells already
  oci = oci

[external_cells]
  # there may be other external cells already
  oci = git

[external_cell_oci]
  git_origin = https://github.com/benbrittain/oci-rules.git
  commit_hash = <set this to latest main branch commit hash>
```

### Configuring the toolchain

The OCI rules depend on a container manipulation tool called [crane](https://github.com/google/go-containerregistry/blob/main/cmd/crane/doc/crane.md). You must define the `oci_toolchain` rule in your `//toolchains` cell.

Example:
```starlark
load("@oci//oci:toolchain.bzl", "oci_toolchain", "download_crane_binary")
load("@oci//tar:toolchain.bzl", "tar_toolchain")

# Optional helper macro for fetching the crane binary based on platform arch
download_crane_binary(
    name = "crane",
    version = "0.21.7",
)

# Register the mandatory toolchain
oci_toolchain(                                     
    name = "oci",                                  
    crane = ":crane",                              
    visibility = ["PUBLIC"],                       
)

# Required by `tar_file`, which builds image layers.
tar_toolchain(
    name = "tar",
    visibility = ["PUBLIC"],
)
```


## Building image layers

`tar_file` produces a deterministic layer tar suitable for `oci_image`'s `tars`
attribute. Use `srcs` to drop sources at the archive root under their basename,
or `files` to place each source at an explicit path; `mode` overrides the file
mode on the `files` entries (handy for binaries whose on-disk bit is unreliable).

```starlark
load("@oci//tar:defs.bzl", "tar_file")

tar_file(
    name = "layer",
    files = {"/usr/local/bin/my-app": ":my-app"},
    mode = "0755",
)
```

Parent directories are synthesised automatically, symlinks are dereferenced so
the layer carries real bytes, and all metadata is normalised (mtime, uid/gid
zeroed; file modes forced to 0644, or 0755 when the source is executable,
unless `mode` overrides them) so the output is byte-reproducible.

## Documentation
TODO: Render documentation from starlark here

## Example
```bash
$ buckle build //tests:image --show-simple-output | xargs podman load -i
$ podman run -it --rm localhost:61978/image.tar:latest
```


