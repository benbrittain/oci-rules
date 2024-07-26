load("//oci:toolchain.bzl", "OciToolchainInfo")

def _oci_pull_impl(ctx: AnalysisContext) -> list[Provider]:
    image = ctx.attrs.image
    output = ctx.actions.declare_output(ctx.attrs.name)
    platform = ctx.attrs.platforms[0]

    cmd = cmd_args(
        ctx.attrs._pull[RunInfo],
        "--crane",
        ctx.attrs._oci_toolchain[OciToolchainInfo].crane[RunInfo],
        "--platform",
        platform,
        "--output",
        output.as_output(),
        "--image",
        image,
        "--digest",
        ctx.attrs.digest,
    )

    ctx.actions.run(cmd, category = "oci")

    return [DefaultInfo(default_output = output)]

oci_pull = rule(
    impl = _oci_pull_impl,
    attrs = {
        "digest": attrs.string(),
        "image": attrs.string(),
        "platforms": attrs.list(attrs.string()),
        "_pull": attrs.default_only(attrs.exec_dep(default = "//oci/helpers:pull")),
        "_oci_toolchain": attrs.toolchain_dep(
            default = "toolchains//:oci",
            providers = [OciToolchainInfo],
        ),
    },
)
