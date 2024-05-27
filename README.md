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
  commit_hash = 27e4a388104ccaada58fd211c635561ac21ddd3a
```

### Configuring the toolchain

The OCI rules depend on a container manipulation tool called [crane](https://github.com/google/go-containerregistry/blob/main/cmd/crane/doc/crane.md). You must define the `oci_toolchain` rule in your `//toolchains` cell.

Example:
```starlark
load("@oci//oci:toolchain.bzl", "oci_toolchain", "download_crane_binary")

# Optional helper macro for fetching the crane binary based on platform arch
download_crane_binary(                      
    name = "crane",                         
    version = "0.19.1",                     
)

# Register the mandatory toolchain
oci_toolchain(                                     
    name = "oci",                                  
    crane = ":crane",                              
    visibility = ["PUBLIC"],                       
)                                                  
```
