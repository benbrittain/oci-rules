# oci-rules

Buck2 rules for the [Open Containers Initiative](https://opencontainers.org) image format.

## Installation

Add this repo as an external cell in your projects `.buckconfig`

```
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
