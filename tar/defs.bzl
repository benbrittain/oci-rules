load("//tar:toolchain.bzl", "TarToolchainInfo")

def _tar_file_impl(ctx: AnalysisContext) -> list[Provider]:
    tar_output_name = (
        ctx.attrs.out if ctx.attrs.out else "{}.tar".format(ctx.label.name)
    )
    tar_file = ctx.actions.declare_output(tar_output_name)
    srcs = ctx.attrs.srcs

    # newline-separated list of source files
    srcs_file_path = ctx.actions.write("srcs.txt", cmd_args(srcs))

    # this is not GNU tar. don't look these flags up in the manual.
    cmd = cmd_args(
        ctx.attrs._tar_toolchain[TarToolchainInfo].tar[RunInfo],
        "--compress",
        "true" if ctx.attrs.compress else "false",
        "--file_path",
        srcs_file_path,
        "--filename",
        tar_file.as_output(),
        hidden = srcs,
    )

    ctx.actions.run(cmd, category = "tar")

    return [DefaultInfo(default_output = tar_file)]

tar_file = rule(
    impl = _tar_file_impl,
    attrs = {
        "compress": attrs.bool(default = False),
        "srcs": attrs.list(attrs.source()),
        "out": attrs.option(attrs.string(), default = None),
        "_tar_toolchain": attrs.toolchain_dep(
            default = "toolchains//:tar",
            providers = [TarToolchainInfo],
        ),
    },
)
