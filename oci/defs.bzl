load("@prelude//python:toolchain.bzl", "PythonToolchainInfo")
load("//oci:toolchain.bzl", "OciToolchainInfo")

def _oci_pull_impl(ctx: AnalysisContext) -> list[Provider]:
    image = ctx.attrs.image
    output = ctx.actions.declare_output("{}.tar".format(ctx.attrs.name))
    platform = ctx.attrs.platforms[0]

    python = ctx.attrs._python_toolchain[PythonToolchainInfo].interpreter
    pull_py = ctx.attrs._oci_toolchain[OciToolchainInfo].pull_py[DefaultInfo].default_outputs
    crane = ctx.attrs._oci_toolchain[OciToolchainInfo].crane[RunInfo]

    cmd = cmd_args(
        python,
        pull_py,
        "--crane",
        crane,
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
        "_python_toolchain": attrs.toolchain_dep(
            default = "toolchains//:python",
            providers = [PythonToolchainInfo],
        ),
        "_oci_toolchain": attrs.toolchain_dep(
            default = "toolchains//:oci",
            providers = [OciToolchainInfo],
        ),
    },
)

def _oci_image_impl(ctx: AnalysisContext) -> list[Provider]:
    base = ctx.attrs.base[DefaultInfo].default_outputs

    # map all of these tars to their outputs using a list comprehension
    tars = ctx.attrs.tars
    tar_outputs = [tar[DefaultInfo].default_outputs for tar in tars]
    entrypoint = ctx.attrs.entrypoint

    output = ctx.actions.declare_output("{}.tar".format(ctx.attrs.name))
    python = ctx.attrs._python_toolchain[PythonToolchainInfo].interpreter
    image_py = ctx.attrs._oci_toolchain[OciToolchainInfo].image_py[DefaultInfo].default_outputs
    crane = ctx.attrs._oci_toolchain[OciToolchainInfo].crane[RunInfo]

    cmd = cmd_args(
        python,
        image_py,
        "--crane",
        crane,
        "--output",
        output.as_output(),
        "--base",
        base,
        "--tars",
        tar_outputs,
        "--entrypoint",
        cmd_args(entrypoint, delimiter = ","),
        "--name",
        ctx.attrs.name,
    )

    ctx.actions.run(cmd, category = "oci")

    return [DefaultInfo(default_output = output)]

oci_image = rule(
    impl = _oci_image_impl,
    attrs = {
        "base": attrs.dep(),
        "tars": attrs.list(attrs.dep()),
        # TODO(dmiller): I'm not sure if this data type is correct
        "entrypoint": attrs.option(attrs.list(attrs.string())),
        "_python_toolchain": attrs.toolchain_dep(
            default = "toolchains//:python",
            providers = [PythonToolchainInfo],
        ),
        "_oci_toolchain": attrs.toolchain_dep(
            default = "toolchains//:oci",
            providers = [OciToolchainInfo],
        ),
    },
)
