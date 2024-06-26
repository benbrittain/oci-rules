# Examples

All examples in here are their own buck2 project, isolated via .buckroot

## Rust
```bash
cd rust/
buck2 build //:rust-image --out - | podman load
podman run localhost:61978/rust-image.tar:latest
```
