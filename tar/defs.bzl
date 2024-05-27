load("@prelude//python:toolchain.bzl", "PythonToolchainInfo")
load("@root//tar:toolchain.bzl", "TarToolchainInfo")

def _tar_file_impl(ctx: AnalysisContext) -> list[Provider]:
    tar_output_name = (
        ctx.attrs.out if ctx.attrs.out else "{}.tar".format(ctx.label.name)
    )
    tar_file = ctx.actions.declare_output(tar_output_name)
    srcs = ctx.attrs.srcs

    srcs_file_cmd = cmd_args()
    for src in srcs:
        srcs_file_cmd.add(src)

    srcs_file_path = ctx.actions.write("srcs.txt", srcs_file_cmd)

    tar_toolchain = ctx.attrs._tar_toolchain[TarToolchainInfo]

    cmd = cmd_args(
        ctx.attrs._python_toolchain[PythonToolchainInfo].interpreter,
        tar_toolchain.tar_file[DefaultInfo].default_outputs,
    )
    cmd.add("--compress")
    cmd.add("true" if ctx.attrs.compress else "false")
    cmd.add("--file_path")
    cmd.add(srcs_file_path)
    cmd.add("--filename")
    cmd.add(tar_file.as_output())
    cmd.hidden(srcs)

    ctx.actions.run(cmd, category = "tar")

    return [DefaultInfo(default_output = tar_file)]

tar_file = rule(
    impl = _tar_file_impl,
    attrs = {
        "compress": attrs.bool(default = False),
        "srcs": attrs.list(attrs.source()),
        "out": attrs.option(attrs.string(), default = None),
        "_python_toolchain": attrs.toolchain_dep(
            default = "toolchains//:python",
            providers = [PythonToolchainInfo],
        ),
        "_tar_toolchain": attrs.toolchain_dep(
            default = "toolchains//:tar",
            providers = [TarToolchainInfo],
        ),
    },
)
