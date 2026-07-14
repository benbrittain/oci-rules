load("//oci:toolchain.bzl", "OciToolchainInfo")

def _oci_pull_impl(ctx: AnalysisContext) -> list[Provider]:
    output = ctx.actions.declare_output(ctx.attrs.name, dir = True)
    crane = ctx.attrs._oci_toolchain[OciToolchainInfo].crane[RunInfo]

    cmd = cmd_args(
        crane,
        "pull",
        "--format=oci",
        "--platform",
        ctx.attrs.platform,
        "{}@{}".format(ctx.attrs.image, ctx.attrs.digest),
        output.as_output(),
    )

    ctx.actions.run(cmd, category = "oci")

    return [DefaultInfo(default_output = output)]

oci_pull = rule(
    impl = _oci_pull_impl,
    attrs = {
        "digest": attrs.string(),
        "image": attrs.string(),
        "platform": attrs.string(),
        "_oci_toolchain": attrs.toolchain_dep(
            default = "toolchains//:oci",
            providers = [OciToolchainInfo],
        ),
    },
)
