def _oci_image_impl(ctx: AnalysisContext) -> list[Provider]:
    base = ctx.attrs.base[DefaultInfo].default_outputs
    tars = [tar[DefaultInfo].default_outputs for tar in ctx.attrs.tars]

    image_name = ctx.attrs.name
    output = ctx.actions.declare_output(image_name, dir = True)

    command = cmd_args(
        ctx.attrs._image[RunInfo],
        "--output",
        output.as_output(),
        "--base",
        base,
        "--name",
        image_name,
    )

    if ctx.attrs.tars:
        command.add(["--tars", tars])
    if ctx.attrs.entrypoint:
        command.add(["--entrypoint"] + ctx.attrs.entrypoint)
    if ctx.attrs.cmd:
        command.add(["--cmd"] + ctx.attrs.cmd)
    if ctx.attrs.workdir:
        command.add(["--workdir", ctx.attrs.workdir])
    if ctx.attrs.user:
        command.add(["--user", ctx.attrs.user])
    for k, v in ctx.attrs.env.items():
        command.add(["--env", "{}={}".format(k, v)])

    ctx.actions.run(command, category = "oci")

    return [DefaultInfo(default_output = output)]

oci_image = rule(
    impl = _oci_image_impl,
    attrs = {
        "base": attrs.dep(),
        "workdir": attrs.option(attrs.string(), default = None),
        "user": attrs.option(attrs.string(), default = None),
        "tars": attrs.list(attrs.dep()),
        "env": attrs.dict(key = attrs.string(), value = attrs.string(), default = {}),
        "cmd": attrs.option(attrs.list(attrs.string()), default = None),
        "entrypoint": attrs.option(attrs.list(attrs.string()), default = None),
        "_image": attrs.default_only(attrs.exec_dep(default = "//oci/helpers:image")),
    },
)
