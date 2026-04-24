load("//oci:toolchain.bzl", "OciToolchainInfo")

def _oci_image_impl(ctx: AnalysisContext) -> list[Provider]:
    base = ctx.attrs.base[DefaultInfo].default_outputs

    # map all of these tars to their outputs using a list comprehension
    tars = ctx.attrs.tars
    tar_outputs = [tar[DefaultInfo].default_outputs for tar in tars]

    image_name = ctx.attrs.name

    output = ctx.actions.declare_output(image_name)

    command = cmd_args(
        ctx.attrs._image[RunInfo],
        "--crane",
        ctx.attrs._oci_toolchain[OciToolchainInfo].crane[RunInfo],
        "--output",
        output.as_output(),
        "--base",
        base,
        cmd_args("--tars", tar_outputs) if tar_outputs else cmd_args(),
    )

    entrypoint = ctx.attrs.entrypoint
    workdir = ctx.attrs.workdir
    user = ctx.attrs.user
    cmd = ctx.attrs.cmd

    if entrypoint != None:
      command.add(["--entrypoint", ",".join(entrypoint)])
    if workdir != None:
      command.add(["--workdir", workdir])
    if user != None:
      command.add(["--user", workdir])
    if cmd != None:
      command.add(["--cmd", ",".join(cmd)])
    for k, v in ctx.attrs.env.items():
      command.add(["--env", "{}={}".format(k, v)])
    command.add([ "--name", image_name])

    ctx.actions.run(command, category = "oci")

    return [ DefaultInfo(default_output = output) ]

oci_image = rule(
    impl = _oci_image_impl,
    attrs = {
        "base": attrs.dep(providers = [DefaultInfo]),
        "workdir": attrs.option(attrs.string(), default = None),
        "user": attrs.option(attrs.string(), default = None),
        "tars": attrs.list(attrs.dep(), default = []),
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
