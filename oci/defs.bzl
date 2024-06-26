load("//oci:toolchain.bzl", "OciToolchainInfo")

def _oci_pull_impl(ctx: AnalysisContext) -> list[Provider]:
    image = ctx.attrs.image
    output = ctx.actions.declare_output("{}.tar".format(ctx.attrs.name))
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

def _oci_image_impl(ctx: AnalysisContext) -> list[Provider]:
    base = ctx.attrs.base[DefaultInfo].default_outputs

    # map all of these tars to their outputs using a list comprehension
    tars = ctx.attrs.tars
    tar_outputs = [tar[DefaultInfo].default_outputs for tar in tars]
    entrypoint = ctx.attrs.entrypoint

    output = ctx.actions.declare_output("{}.tar".format(ctx.attrs.name))
    cmd = cmd_args(
        ctx.attrs._image[RunInfo],
        "--crane",
        ctx.attrs._oci_toolchain[OciToolchainInfo].crane[RunInfo],
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
        "_image": attrs.default_only(attrs.exec_dep(default = "//oci/helpers:image")),
        "_oci_toolchain": attrs.toolchain_dep(
            default = "toolchains//:oci",
            providers = [OciToolchainInfo],
        ),
    },
)
