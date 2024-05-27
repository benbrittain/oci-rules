load("//oci:toolchain.bzl", "OciToolchainInfo")

def _oci_image_impl(ctx: AnalysisContext) -> list[Provider]:
    base = ctx.attrs.base[DefaultInfo].default_outputs

    # map all of these tars to their outputs using a list comprehension
    tars = ctx.attrs.tars
    tar_outputs = [tar[DefaultInfo].default_outputs for tar in tars]

    #image_name = "{}-{}.tar".format(ctx.label.package.replace('/', '-'), ctx.attrs.name)
    image_name = "{}.tar".format(ctx.attrs.name)

    output = ctx.actions.declare_output(image_name)

    command = cmd_args(
        ctx.attrs._image[RunInfo],
        "--crane",
        ctx.attrs._oci_toolchain[OciToolchainInfo].crane[RunInfo],
        "--output",
        output.as_output(),
        "--base",
        base,
        "--tars",
        tar_outputs,
    )

    entrypoint = ctx.attrs.entrypoint
    if entrypoint:
      command.add(["--entrypoint", ",".join(entrypoint)])

    cmd = ctx.attrs.cmd
    if cmd:
      command.add(["--cmd", " ".join(cmd)])

    for k, v in ctx.attrs.env.items():
      command.add(["--env", f"{k}={v}"])

    command.add([ "--name", image_name])

    ctx.actions.run(command, category = "oci", always_print_stderr = True)

    return [DefaultInfo(default_output = output)]

oci_image = rule(
    impl = _oci_image_impl,
    attrs = {
        "base": attrs.dep(),
        "tars": attrs.list(attrs.dep()),
        "env": attrs.dict(key=attrs.string(), value=attrs.string(), default = {}),
        "cmd": attrs.option(attrs.list(attrs.string()), default = None),
        "entrypoint": attrs.option(attrs.list(attrs.string()), default = None),
        "_image": attrs.default_only(attrs.exec_dep(default = "//oci/helpers:image")),
        "_oci_toolchain": attrs.toolchain_dep(
            default = "toolchains//:oci",
            providers = [OciToolchainInfo],
        ),
    },
)
